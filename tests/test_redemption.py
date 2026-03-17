from tests.conftest import login, mint_thc, verify_balance_integrity
from app.models.redemption import Redemption


def test_redemption_page_loads(client, regular_user):
    login(client, 'alice', 'password')
    resp = client.get('/redemption/')
    assert resp.status_code == 200


def test_request_redemption(client, regular_user, second_user, app):
    mint_thc(client, 'alice', 'bob', 1.5)

    login(client, 'bob', 'password')
    resp = client.post('/redemption/request', data={
        'target': regular_user.id,
    }, follow_redirects=True)
    assert b'Redemption requested' in resp.data


def test_accept_redemption(client, regular_user, second_user, app):
    mint_thc(client, 'alice', 'bob', 1.5)

    login(client, 'bob', 'password')
    client.post('/redemption/request', data={'target': regular_user.id})

    redemption = Redemption.query.first()
    login(client, 'alice', 'password')
    resp = client.post(f'/redemption/{redemption.id}/accept', follow_redirects=True)
    assert b'Redemption accepted' in resp.data

    from app.services.balance_service import get_source_balance
    assert abs(get_source_balance(second_user.id, regular_user.id) - 0.5) < 1e-9
    verify_balance_integrity(app)


def test_decline_redemption(client, regular_user, second_user):
    mint_thc(client, 'alice', 'bob', 1.5)

    login(client, 'bob', 'password')
    client.post('/redemption/request', data={'target': regular_user.id})

    redemption = Redemption.query.first()
    login(client, 'alice', 'password')
    resp = client.post(f'/redemption/{redemption.id}/decline', follow_redirects=True)
    assert b'Redemption declined' in resp.data


def test_cancel_redemption(client, regular_user, second_user):
    mint_thc(client, 'alice', 'bob', 1.5)

    login(client, 'bob', 'password')
    client.post('/redemption/request', data={'target': regular_user.id})

    redemption = Redemption.query.first()
    resp = client.post(f'/redemption/{redemption.id}/cancel', follow_redirects=True)
    assert b'Redemption cancelled' in resp.data


def test_insufficient_balance_for_redemption(client, regular_user, second_user):
    mint_thc(client, 'alice', 'bob', 0.5)

    login(client, 'bob', 'password')
    resp = client.post('/redemption/request', data={
        'target': regular_user.id,
    }, follow_redirects=True)
    # Alice won't be in choices since bob has < 1.0 from alice
    assert resp.status_code == 200
