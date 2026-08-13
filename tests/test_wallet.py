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
        'source': regular_user.id,
        'amount': 0.5,
    }, follow_redirects=True)
    assert b'Sent 0.50 THC' in resp.data
    verify_balance_integrity(app)


def test_send_insufficient_balance(client, regular_user, second_user, app):
    mint_thc(client, 'alice', 'bob', 1.0)

    login(client, 'bob', 'password')
    resp = client.post('/wallet/send', data={
        'recipient': regular_user.id,
        'source': regular_user.id,
        'amount': 5.0,
    }, follow_redirects=True)
    assert b'Insufficient balance' in resp.data


def test_source_tagging_on_send(client, regular_user, second_user, third_user, app):
    """When Bob sends THC to Charlie, Charlie's source is Bob (not Alice)."""
    mint_thc(client, 'alice', 'bob', 2.0)

    login(client, 'bob', 'password')
    client.post('/wallet/send', data={
        'recipient': third_user.id,
        'source': regular_user.id,
        'amount': 1.0,
    })

    from app.models.balance import Balance
    bal = Balance.query.filter_by(holder_user_id=third_user.id, source_user_id=second_user.id).first()
    assert bal is not None
    assert abs(bal.amount - 1.0) < 1e-9

    bal_alice = Balance.query.filter_by(holder_user_id=third_user.id, source_user_id=regular_user.id).first()
    assert bal_alice is None or abs(bal_alice.amount) < 1e-9

    verify_balance_integrity(app)


def test_send_debits_the_chosen_source_not_fifo(client, regular_user, second_user,
                                                third_user, admin_user, app):
    """Charlie holds THC from both Alice and Bob. Choosing Bob must debit Bob,
    even though FIFO (ascending source id) would have drained Alice first."""
    mint_thc(client, 'alice', 'charlie', 1.0)
    mint_thc(client, 'bob', 'charlie', 1.0)

    from app.services import balance_service
    assert regular_user.id < second_user.id, 'fixture ordering assumption for FIFO'

    login(client, 'charlie', 'password')
    resp = client.post('/wallet/send', data={
        'recipient': admin_user.id,
        'source': second_user.id,   # explicitly draw from Bob
        'amount': 0.6,
    }, follow_redirects=True)
    assert b'Sent 0.60 THC' in resp.data

    assert abs(balance_service.get_source_balance(third_user.id, regular_user.id) - 1.0) < 1e-9
    assert abs(balance_service.get_source_balance(third_user.id, second_user.id) - 0.4) < 1e-9

    verify_balance_integrity(app)


def test_cannot_overdraw_a_single_source(client, regular_user, second_user,
                                         third_user, admin_user, app):
    """Total balance is enough, but the chosen source alone is not."""
    mint_thc(client, 'alice', 'charlie', 1.0)
    mint_thc(client, 'bob', 'charlie', 1.0)

    login(client, 'charlie', 'password')
    resp = client.post('/wallet/send', data={
        'recipient': admin_user.id,
        'source': second_user.id,
        'amount': 1.5,   # under the 2.0 total, over the 1.0 from Bob
    }, follow_redirects=True)
    assert b'Insufficient balance from Bob' in resp.data

    from app.services import balance_service
    assert abs(balance_service.get_total_balance(third_user.id) - 2.0) < 1e-9
    verify_balance_integrity(app)


def test_mint_send_creates_new_supply(client, regular_user, second_user, app):
    from app.services import balance_service
    from app.forms.wallet_forms import MINT_SOURCE

    login(client, 'alice', 'password')
    resp = client.post('/wallet/send', data={
        'recipient': second_user.id,
        'source': MINT_SOURCE,
        'amount': 1.25,
    }, follow_redirects=True)
    assert b'Minted and sent 1.25 THC' in resp.data

    # Bob is credited, tagged to Alice; Alice is not debited (she had nothing).
    assert abs(balance_service.get_source_balance(second_user.id, regular_user.id) - 1.25) < 1e-9
    assert abs(balance_service.get_total_balance(regular_user.id)) < 1e-9

    verify_balance_integrity(app)


def test_mint_send_does_not_drain_existing_balances(client, regular_user, second_user,
                                                    third_user, app):
    """Minting must leave the sender's own holdings untouched."""
    from app.services import balance_service
    from app.forms.wallet_forms import MINT_SOURCE

    mint_thc(client, 'alice', 'bob', 2.0)

    login(client, 'bob', 'password')
    client.post('/wallet/send', data={
        'recipient': third_user.id,
        'source': MINT_SOURCE,
        'amount': 0.5,
    }, follow_redirects=True)

    assert abs(balance_service.get_source_balance(second_user.id, regular_user.id) - 2.0) < 1e-9
    assert abs(balance_service.get_source_balance(third_user.id, second_user.id) - 0.5) < 1e-9
    verify_balance_integrity(app)


def test_mint_send_respects_cap(client, regular_user, second_user, app):
    from app.forms.wallet_forms import MINT_SOURCE

    login(client, 'alice', 'password')
    resp = client.post('/wallet/send', data={
        'recipient': second_user.id,
        'source': MINT_SOURCE,
        'amount': 9.0,
    }, follow_redirects=True)
    assert b'at most 5.00 THC' in resp.data

    from app.services import balance_service
    assert abs(balance_service.get_total_balance(second_user.id)) < 1e-9


def test_rebuild_replays_chosen_source_and_mints(client, regular_user, second_user,
                                                 third_user, admin_user, app):
    """The balance cache must be reconstructible from the ledger alone."""
    from app.services import balance_service
    from app.forms.wallet_forms import MINT_SOURCE
    from app.extensions import db

    mint_thc(client, 'alice', 'charlie', 1.0)
    mint_thc(client, 'bob', 'charlie', 1.0)

    login(client, 'charlie', 'password')
    client.post('/wallet/send', data={
        'recipient': admin_user.id, 'source': second_user.id, 'amount': 0.6,
    })
    client.post('/wallet/send', data={
        'recipient': admin_user.id, 'source': MINT_SOURCE, 'amount': 0.4,
    })

    before = {
        (b.holder_user_id, b.source_user_id): round(b.amount, 6)
        for b in balance_service.Balance.query.all() if abs(b.amount) > 1e-9
    }

    balance_service.rebuild_all_balances()
    db.session.commit()

    after = {
        (b.holder_user_id, b.source_user_id): round(b.amount, 6)
        for b in balance_service.Balance.query.all() if abs(b.amount) > 1e-9
    }

    assert before == after, f'replay diverged\nbefore={before}\nafter={after}'
    verify_balance_integrity(app)
