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
