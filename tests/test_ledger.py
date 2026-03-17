from tests.conftest import login, mint_thc


def test_ledger_loads(client, regular_user):
    login(client, 'alice', 'password')
    resp = client.get('/ledger/')
    assert resp.status_code == 200
    assert b'Public Ledger' in resp.data


def test_ledger_shows_transactions(client, regular_user, second_user):
    mint_thc(client, 'alice', 'bob', 1.0)
    login(client, 'alice', 'password')
    resp = client.get('/ledger/')
    assert b'bounty_payout' in resp.data


def test_ledger_filter_by_type(client, regular_user, second_user):
    mint_thc(client, 'alice', 'bob', 1.0)

    login(client, 'alice', 'password')
    resp = client.get('/ledger/?type=send')
    assert b'No transactions found' in resp.data

    resp = client.get('/ledger/?type=bounty_payout')
    assert b'bounty_payout' in resp.data
