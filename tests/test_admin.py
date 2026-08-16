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


# --- Admin role management ---

def test_grant_and_revoke_admin(client, admin_user, regular_user):
    from app.extensions import db
    from app.models.user import User

    login(client, 'admin', 'password')
    resp = client.post(f'/admin/toggle-role/{regular_user.id}', follow_redirects=True)
    assert b'is now an admin' in resp.data
    assert db.session.get(User, regular_user.id).is_admin is True

    resp = client.post(f'/admin/toggle-role/{regular_user.id}', follow_redirects=True)
    assert b'is no longer an admin' in resp.data
    assert db.session.get(User, regular_user.id).is_admin is False


def test_promoted_user_gains_admin_access(client, admin_user, regular_user):
    login(client, 'admin', 'password')
    client.post(f'/admin/toggle-role/{regular_user.id}')

    login(client, 'alice', 'password')
    resp = client.get('/admin/')
    assert resp.status_code == 200
    assert b'Admin access required' not in resp.data


def test_revoked_user_loses_admin_access(client, admin_user, regular_user):
    login(client, 'admin', 'password')
    client.post(f'/admin/toggle-role/{regular_user.id}')
    client.post(f'/admin/toggle-role/{regular_user.id}')

    login(client, 'alice', 'password')
    resp = client.get('/admin/', follow_redirects=True)
    assert b'Admin access required' in resp.data


def test_cannot_change_own_role(client, admin_user):
    from app.extensions import db
    from app.models.user import User

    login(client, 'admin', 'password')
    resp = client.post(f'/admin/toggle-role/{admin_user.id}', follow_redirects=True)
    assert b'cannot change your own role' in resp.data
    assert db.session.get(User, admin_user.id).is_admin is True


def test_last_admin_cannot_be_removed(client, admin_user, regular_user):
    """Promote a second admin, who then tries to demote the original."""
    from app.extensions import db
    from app.models.user import User

    login(client, 'admin', 'password')
    client.post(f'/admin/toggle-role/{regular_user.id}')

    # Alice (now admin) demotes the original admin — allowed, she remains.
    login(client, 'alice', 'password')
    resp = client.post(f'/admin/toggle-role/{admin_user.id}', follow_redirects=True)
    assert b'is no longer an admin' in resp.data
    assert db.session.get(User, admin_user.id).is_admin is False

    # She cannot demote herself, so the system can never reach zero admins.
    resp = client.post(f'/admin/toggle-role/{regular_user.id}', follow_redirects=True)
    assert b'cannot change your own role' in resp.data
    assert User.query.filter_by(role='admin').count() == 1


def test_non_admin_cannot_change_roles(client, regular_user, second_user):
    from app.extensions import db
    from app.models.user import User

    login(client, 'bob', 'password')
    resp = client.post(f'/admin/toggle-role/{regular_user.id}', follow_redirects=True)
    assert b'Admin access required' in resp.data
    assert db.session.get(User, regular_user.id).is_admin is False


# --- Audit trail ---

def test_actions_are_logged(client, admin_user, regular_user):
    from app.models.admin_action import AdminAction

    login(client, 'admin', 'password')
    client.post(f'/admin/toggle-active/{regular_user.id}')
    client.post(f'/admin/toggle-role/{regular_user.id}')
    client.post(f'/admin/reset-password/{regular_user.id}', data={'new_password': 'newtemp123'})

    actions = [a.action for a in AdminAction.query.order_by(AdminAction.id).all()]
    assert actions == ['deactivate_user', 'grant_admin', 'reset_password']

    entry = AdminAction.query.first()
    assert entry.admin_user_id == admin_user.id
    assert entry.target_user_id == regular_user.id


def test_takedowns_are_logged(client, admin_user, regular_user):
    from app.models.admin_action import AdminAction

    bounty = _post_bounty(client, 'alice')
    login(client, 'admin', 'password')
    client.post(f'/admin/bounty/{bounty.id}/remove')

    entry = AdminAction.query.filter_by(action='remove_bounty').first()
    assert entry is not None
    assert entry.target_id == bounty.id
    assert entry.target_user_id == regular_user.id


def test_log_never_republishes_removed_content(client, admin_user, regular_user):
    """Renaming and takedown must not echo the offending text into the log."""
    from app.models.admin_action import AdminAction

    bounty = _post_bounty(client, 'alice', title='OFFENSIVE TITLE', description='bad words')

    login(client, 'admin', 'password')
    client.post(f'/admin/bounty/{bounty.id}/remove')
    client.post(f'/admin/edit-user/{regular_user.id}', data={'display_name': 'Neutral Name'})

    details = ' '.join(a.detail or '' for a in AdminAction.query.all())
    assert 'OFFENSIVE TITLE' not in details
    assert 'bad words' not in details
    assert 'Alice' not in details, 'the previous display name must not be echoed'

    resp = client.get('/ledger/admin-actions')
    assert b'OFFENSIVE TITLE' not in resp.data
    assert b'bad words' not in resp.data


def test_audit_log_is_visible_to_regular_users(client, admin_user, regular_user):
    login(client, 'admin', 'password')
    client.post(f'/admin/toggle-active/{regular_user.id}')
    client.post(f'/admin/toggle-active/{regular_user.id}')

    login(client, 'alice', 'password')
    resp = client.get('/ledger/admin-actions')
    assert resp.status_code == 200
    assert b'Admin Action Log' in resp.data
    assert b'reactivated an account' in resp.data


def test_audit_log_requires_login(client):
    resp = client.get('/ledger/admin-actions', follow_redirects=True)
    assert b'Please log in' in resp.data


def test_invalidation_is_logged(client, admin_user, regular_user, second_user, app):
    from app.models.admin_action import AdminAction
    from app.models.transaction import Transaction

    mint_thc(client, 'alice', 'bob', 1.0)
    txn = Transaction.query.first()

    login(client, 'admin', 'password')
    client.post(f'/admin/invalidate/{txn.id}')

    entry = AdminAction.query.filter_by(action='invalidate_transaction').first()
    assert entry is not None
    assert entry.target_id == txn.id
    verify_balance_integrity(app)
