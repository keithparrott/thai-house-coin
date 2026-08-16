from tests.conftest import login, mint_thc, verify_balance_integrity


def _post_bounty(client, username, title='Bad Bounty', description='inappropriate text', reward=1.0):
    from app.models.bounty import Bounty
    login(client, username, 'password')
    client.post('/bounty/create', data={
        'title': title, 'description': description, 'reward_amount': reward,
    })
    return Bounty.query.order_by(Bounty.id.desc()).first()


def test_admin_panel_requires_admin(client, regular_user):
    login(client, 'alice', 'password')
    resp = client.get('/admin/', follow_redirects=True)
    assert b'Admin access required' in resp.data


def test_admin_panel_loads(client, admin_user):
    login(client, 'admin', 'password')
    resp = client.get('/admin/')
    assert resp.status_code == 200
    assert b'Users' in resp.data


def test_create_user(client, admin_user):
    login(client, 'admin', 'password')
    resp = client.post('/admin/create-user', data={
        'username': 'newuser',
        'display_name': 'New User',
        'password': 'temppass',
        'is_admin': False,
    }, follow_redirects=True)
    assert b'newuser' in resp.data
    assert b'created' in resp.data


def test_create_duplicate_user(client, admin_user, regular_user):
    login(client, 'admin', 'password')
    resp = client.post('/admin/create-user', data={
        'username': 'alice',
        'display_name': 'Alice 2',
        'password': 'temppass',
    }, follow_redirects=True)
    assert b'already exists' in resp.data


def test_reset_password(client, admin_user, regular_user):
    login(client, 'admin', 'password')
    resp = client.post(f'/admin/reset-password/{regular_user.id}', data={
        'new_password': 'newtemp123'
    }, follow_redirects=True)
    assert b'Password reset' in resp.data


def test_toggle_active(client, admin_user, regular_user):
    login(client, 'admin', 'password')
    resp = client.post(f'/admin/toggle-active/{regular_user.id}', follow_redirects=True)
    assert b'deactivated' in resp.data

    resp = client.post(f'/admin/toggle-active/{regular_user.id}', follow_redirects=True)
    assert b'activated' in resp.data


def test_cannot_deactivate_self(client, admin_user):
    login(client, 'admin', 'password')
    resp = client.post(f'/admin/toggle-active/{admin_user.id}', follow_redirects=True)
    assert b'cannot deactivate yourself' in resp.data


# --- Admin content moderation ---

def test_admin_removes_bounty_and_erases_text(client, admin_user, regular_user):
    from app.extensions import db
    from app.models.bounty import Bounty

    bounty = _post_bounty(client, 'alice')

    login(client, 'admin', 'password')
    resp = client.post(f'/admin/bounty/{bounty.id}/remove', follow_redirects=True)
    assert b'Bounty removed' in resp.data

    bounty = db.session.get(Bounty, bounty.id)
    assert bounty.status == 'cancelled'
    assert bounty.title == '[Removed by an admin]'
    assert bounty.description == ''

    # The offending text must be gone from the public board, not merely
    # marked cancelled.
    resp = client.get('/bounty/')
    assert b'inappropriate text' not in resp.data
    assert b'Bad Bounty' not in resp.data


def test_admin_remove_strips_text_of_completed_bounty_without_changing_status(
        client, admin_user, regular_user, second_user, app):
    """A completed bounty already paid out, so its status must stay accurate."""
    from app.extensions import db
    from app.models.bounty import Bounty

    bounty = mint_thc(client, 'alice', 'bob', 1.0)

    login(client, 'admin', 'password')
    client.post(f'/admin/bounty/{bounty.id}/remove', follow_redirects=True)

    bounty = db.session.get(Bounty, bounty.id)
    assert bounty.status == 'completed', 'a settled payout must not be reopened'
    assert bounty.title == '[Removed by an admin]'
    verify_balance_integrity(app)


def test_admin_removes_claim_message(client, admin_user, regular_user, second_user):
    from app.extensions import db
    from app.models.bounty import BountyClaim

    bounty = _post_bounty(client, 'alice', title='Fine bounty', description='ok')

    login(client, 'bob', 'password')
    client.post(f'/bounty/{bounty.id}/claim', data={'message': 'nasty claim text'})
    claim = BountyClaim.query.filter_by(bounty_id=bounty.id).first()

    login(client, 'admin', 'password')
    resp = client.post(f'/admin/claim/{claim.id}/remove', follow_redirects=True)
    assert b'Claim removed' in resp.data

    claim = db.session.get(BountyClaim, claim.id)
    assert claim.message == '[Removed by an admin]'
    assert claim.status == 'rejected'

    resp = client.get(f'/bounty/{bounty.id}')
    assert b'nasty claim text' not in resp.data


def test_removing_only_pending_claim_reopens_bounty(client, admin_user, regular_user, second_user):
    from app.extensions import db
    from app.models.bounty import Bounty, BountyClaim

    bounty = _post_bounty(client, 'alice', title='Reopen me', description='ok')

    login(client, 'bob', 'password')
    client.post(f'/bounty/{bounty.id}/claim', data={'message': 'spam'})
    claim = BountyClaim.query.filter_by(bounty_id=bounty.id).first()
    assert db.session.get(Bounty, bounty.id).status == 'pending'

    login(client, 'admin', 'password')
    client.post(f'/admin/claim/{claim.id}/remove')
    assert db.session.get(Bounty, bounty.id).status == 'open'


def test_non_admin_cannot_remove_bounty(client, regular_user, second_user):
    from app.extensions import db
    from app.models.bounty import Bounty

    bounty = _post_bounty(client, 'alice')

    login(client, 'bob', 'password')
    resp = client.post(f'/admin/bounty/{bounty.id}/remove', follow_redirects=True)
    assert b'Admin access required' in resp.data

    bounty = db.session.get(Bounty, bounty.id)
    assert bounty.title == 'Bad Bounty', 'content must survive a non-admin takedown attempt'


def test_non_admin_cannot_remove_claim(client, regular_user, second_user):
    from app.extensions import db
    from app.models.bounty import BountyClaim

    bounty = _post_bounty(client, 'alice', title='ok', description='ok')
    login(client, 'bob', 'password')
    client.post(f'/bounty/{bounty.id}/claim', data={'message': 'my claim'})
    claim = BountyClaim.query.filter_by(bounty_id=bounty.id).first()

    resp = client.post(f'/admin/claim/{claim.id}/remove', follow_redirects=True)
    assert b'Admin access required' in resp.data
    assert db.session.get(BountyClaim, claim.id).message == 'my claim'


# --- Admin display name editing ---

def test_admin_edits_display_name(client, admin_user, regular_user):
    from app.models.user import User

    login(client, 'admin', 'password')
    resp = client.post(f'/admin/edit-user/{regular_user.id}', data={
        'display_name': 'Renamed By Admin',
    }, follow_redirects=True)
    assert b'Display name updated' in resp.data

    user = User.query.filter_by(username='alice').first()
    assert user is not None, 'username must be untouched'
    assert user.display_name == 'Renamed By Admin'


def test_admin_edit_rejects_duplicate_display_name(client, admin_user, regular_user, second_user):
    from app.models.user import User

    login(client, 'admin', 'password')
    resp = client.post(f'/admin/edit-user/{regular_user.id}', data={
        'display_name': 'bob',
    }, follow_redirects=True)
    assert b'display name is already in use' in resp.data
    assert User.query.filter_by(username='alice').first().display_name == 'Alice'


def test_non_admin_cannot_edit_other_user(client, regular_user, second_user):
    from app.models.user import User

    login(client, 'bob', 'password')
    resp = client.post(f'/admin/edit-user/{regular_user.id}', data={
        'display_name': 'Hacked',
    }, follow_redirects=True)
    assert b'Admin access required' in resp.data
    assert User.query.filter_by(username='alice').first().display_name == 'Alice'
