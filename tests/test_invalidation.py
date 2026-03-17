from tests.conftest import login, mint_thc, verify_balance_integrity
from app.models.transaction import Transaction


def test_invalidate_transaction(client, admin_user, regular_user, second_user, app):
    mint_thc(client, 'alice', 'bob', 2.0)

    txn = Transaction.query.first()
    login(client, 'admin', 'password')
    resp = client.post(f'/admin/invalidate/{txn.id}', follow_redirects=True)
    assert b'invalidated' in resp.data.lower()

    from app.services.balance_service import get_total_balance
    with app.app_context():
        assert abs(get_total_balance(second_user.id)) < 1e-9

    verify_balance_integrity(app)


def test_invalidate_requires_admin(client, regular_user, second_user):
    mint_thc(client, 'alice', 'bob', 1.0)

    txn = Transaction.query.first()
    login(client, 'bob', 'password')
    resp = client.post(f'/admin/invalidate/{txn.id}', follow_redirects=True)
    assert b'Admin access required' in resp.data


def test_invalidate_cascading(client, admin_user, regular_user, second_user, third_user, app):
    """Invalidating a bounty payout should cascade to downstream sends."""
    mint_thc(client, 'alice', 'bob', 3.0)

    login(client, 'bob', 'password')
    client.post('/wallet/send', data={
        'recipient': third_user.id,
        'amount': 1.0,
    })

    txn = Transaction.query.filter_by(type='bounty_payout').first()
    login(client, 'admin', 'password')
    client.post(f'/admin/invalidate/{txn.id}')

    from app.services.balance_service import get_total_balance
    with app.app_context():
        charlie_balance = get_total_balance(third_user.id)
        assert abs(charlie_balance - 1.0) < 1e-9

    verify_balance_integrity(app)
