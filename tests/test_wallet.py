from tests.conftest import login, mint_thc, verify_balance_integrity


def test_wallet_shows_balance(client, regular_user, second_user, app):
    mint_thc(client, 'alice', 'bob', 2.0)
    login(client, 'bob', 'password')
    resp = client.get('/wallet/')
    assert b'2.00' in resp.data
    verify_balance_integrity(app)


def test_send_thc(client, regular_user, second_user, third_user, app):
    mint_thc(client, 'alice', 'bob', 2.0)

    login(client, 'bob', 'password')
    resp = client.post('/wallet/send', data={
        'recipient': third_user.id,
        'amount': 0.5,
    }, follow_redirects=True)
    assert b'Sent 0.50 THC' in resp.data
    verify_balance_integrity(app)


def test_send_insufficient_balance(client, regular_user, second_user, app):
    mint_thc(client, 'alice', 'bob', 1.0)

    login(client, 'bob', 'password')
    resp = client.post('/wallet/send', data={
        'recipient': regular_user.id,
        'amount': 5.0,
    }, follow_redirects=True)
    assert b'Insufficient balance' in resp.data


def test_source_tagging_on_send(client, regular_user, second_user, third_user, app):
    """When Bob sends THC to Charlie, Charlie's source is Bob (not Alice)."""
    mint_thc(client, 'alice', 'bob', 2.0)

    login(client, 'bob', 'password')
    client.post('/wallet/send', data={
        'recipient': third_user.id,
        'amount': 1.0,
    })

    from app.models.balance import Balance
    bal = Balance.query.filter_by(holder_user_id=third_user.id, source_user_id=second_user.id).first()
    assert bal is not None
    assert abs(bal.amount - 1.0) < 1e-9

    bal_alice = Balance.query.filter_by(holder_user_id=third_user.id, source_user_id=regular_user.id).first()
    assert bal_alice is None or abs(bal_alice.amount) < 1e-9

    verify_balance_integrity(app)
