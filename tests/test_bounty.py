from tests.conftest import login, mint_thc, verify_balance_integrity


def test_bounty_board_loads(client, regular_user):
    login(client, 'alice', 'password')
    resp = client.get('/bounty/')
    assert resp.status_code == 200
    assert b'Bounty Board' in resp.data


def test_create_bounty(client, regular_user):
    login(client, 'alice', 'password')
    resp = client.post('/bounty/create', data={
        'title': 'Test Bounty',
        'description': 'Do a thing',
        'reward_amount': 1.5,
    }, follow_redirects=True)
    assert b'Bounty posted' in resp.data
    assert b'Test Bounty' in resp.data


def test_max_bounties(client, regular_user):
    login(client, 'alice', 'password')
    for i in range(5):
        client.post('/bounty/create', data={
            'title': f'Bounty {i}',
            'description': 'x',
            'reward_amount': 0.5,
        })
    resp = client.post('/bounty/create', data={
        'title': 'Bounty 6',
        'description': 'x',
        'reward_amount': 0.5,
    }, follow_redirects=True)
    assert b'at most 5' in resp.data


def test_claim_and_approve(client, regular_user, second_user, app):
    mint_thc(client, 'alice', 'bob', 2.0)
    verify_balance_integrity(app)


def test_cannot_self_claim(client, regular_user):
    login(client, 'alice', 'password')
    client.post('/bounty/create', data={
        'title': 'My bounty',
        'description': 'x',
        'reward_amount': 0.5,
    })
    from app.models.bounty import Bounty
    bounty = Bounty.query.first()
    resp = client.post(f'/bounty/{bounty.id}/claim', data={
        'message': 'self claim'
    }, follow_redirects=True)
    assert b'cannot claim your own' in resp.data


def test_reject_claim(client, regular_user, second_user):
    login(client, 'alice', 'password')
    client.post('/bounty/create', data={
        'title': 'Reject test',
        'description': 'x',
        'reward_amount': 0.5,
    })
    from app.models.bounty import Bounty, BountyClaim
    bounty = Bounty.query.first()

    login(client, 'bob', 'password')
    client.post(f'/bounty/{bounty.id}/claim', data={'message': 'attempt'})

    login(client, 'alice', 'password')
    claim = BountyClaim.query.filter_by(bounty_id=bounty.id, status='pending').first()
    resp = client.post(f'/bounty/claim/{claim.id}/reject', follow_redirects=True)
    assert b'Claim rejected' in resp.data


def test_cancel_bounty(client, regular_user):
    login(client, 'alice', 'password')
    client.post('/bounty/create', data={
        'title': 'Cancel me',
        'description': 'x',
        'reward_amount': 0.5,
    })
    from app.models.bounty import Bounty
    bounty = Bounty.query.first()
    resp = client.post(f'/bounty/{bounty.id}/cancel', follow_redirects=True)
    assert b'Bounty cancelled' in resp.data


def test_contribute_to_bounty(client, regular_user, second_user):
    login(client, 'alice', 'password')
    client.post('/bounty/create', data={
        'title': 'Team effort',
        'description': 'x',
        'reward_amount': 1.0,
    })
    from app.extensions import db
    from app.models.bounty import Bounty
    bounty = Bounty.query.first()

    login(client, 'bob', 'password')
    resp = client.post(f'/bounty/{bounty.id}/contribute', data={'amount': 0.5}, follow_redirects=True)
    assert b'upping the ante' in resp.data

    bounty = db.session.get(Bounty, bounty.id)
    assert abs(bounty.total_reward - 1.5) < 1e-9
    assert bounty.contributor_count == 1


def test_cannot_contribute_to_own_bounty(client, regular_user):
    login(client, 'alice', 'password')
    client.post('/bounty/create', data={
        'title': 'Solo bounty',
        'description': 'x',
        'reward_amount': 1.0,
    })
    from app.extensions import db
    from app.models.bounty import Bounty
    bounty = Bounty.query.first()

    resp = client.post(f'/bounty/{bounty.id}/contribute', data={'amount': 0.5}, follow_redirects=True)
    assert b'cannot contribute to your own bounty' in resp.data
    bounty = db.session.get(Bounty, bounty.id)
    assert bounty.contributor_count == 0


def test_multi_contributor_payout_source_tagged(client, regular_user, second_user, third_user, app):
    login(client, 'alice', 'password')
    client.post('/bounty/create', data={
        'title': 'Big task',
        'description': 'x',
        'reward_amount': 1.0,
    })
    from app.models.bounty import Bounty, BountyClaim
    bounty = Bounty.query.first()

    login(client, 'bob', 'password')
    client.post(f'/bounty/{bounty.id}/contribute', data={'amount': 0.5})

    login(client, 'charlie', 'password')
    client.post(f'/bounty/{bounty.id}/claim', data={'message': 'done'})

    login(client, 'alice', 'password')
    claim = BountyClaim.query.filter_by(bounty_id=bounty.id, status='pending').first()
    resp = client.post(f'/bounty/claim/{claim.id}/approve', follow_redirects=True)
    assert b'THC minted' in resp.data

    from app.models.user import User
    from app.services import balance_service
    alice = User.query.filter_by(username='alice').first()
    bob = User.query.filter_by(username='bob').first()
    charlie = User.query.filter_by(username='charlie').first()

    # Charlie's payout must remain split by source: 1.0 from Alice, 0.5 from Bob —
    # not lumped into a single 1.5 balance — so each portion redeems independently.
    assert abs(balance_service.get_source_balance(charlie.id, alice.id) - 1.0) < 1e-9
    assert abs(balance_service.get_source_balance(charlie.id, bob.id) - 0.5) < 1e-9

    verify_balance_integrity(app)


def test_cannot_contribute_after_completion(client, regular_user, second_user, third_user):
    login(client, 'alice', 'password')
    client.post('/bounty/create', data={
        'title': 'Fast task',
        'description': 'x',
        'reward_amount': 0.5,
    })
    from app.models.bounty import Bounty, BountyClaim
    bounty = Bounty.query.first()

    login(client, 'charlie', 'password')
    client.post(f'/bounty/{bounty.id}/claim', data={'message': 'done'})

    login(client, 'alice', 'password')
    claim = BountyClaim.query.filter_by(bounty_id=bounty.id, status='pending').first()
    client.post(f'/bounty/claim/{claim.id}/approve')

    login(client, 'bob', 'password')
    resp = client.post(f'/bounty/{bounty.id}/contribute', data={'amount': 0.5}, follow_redirects=True)
    assert b'no longer accepting contributions' in resp.data
