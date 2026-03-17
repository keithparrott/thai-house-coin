import pytest
from app import create_app
from app.extensions import db as _db
from app.models.user import User


@pytest.fixture(scope='session')
def app():
    app = create_app('testing')
    return app


@pytest.fixture(autouse=True)
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(db):
    user = User(username='admin', display_name='Admin', role='admin', must_change_password=False)
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def regular_user(db):
    user = User(username='alice', display_name='Alice', role='user', must_change_password=False)
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def second_user(db):
    user = User(username='bob', display_name='Bob', role='user', must_change_password=False)
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def third_user(db):
    user = User(username='charlie', display_name='Charlie', role='user', must_change_password=False)
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    return user


def login(client, username='admin', password='password'):
    client.get('/logout')  # Ensure previous session is cleared
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)


def mint_thc(client, poster_username, claimant_username, amount):
    """Helper: create bounty, claim, and approve to mint THC. Returns the bounty."""
    from app.models.bounty import Bounty, BountyClaim

    login(client, poster_username, 'password')
    client.post('/bounty/create', data={
        'title': f'Mint bounty {amount}',
        'description': 'test mint',
        'reward_amount': amount,
    })
    bounty = Bounty.query.order_by(Bounty.id.desc()).first()

    login(client, claimant_username, 'password')
    client.post(f'/bounty/{bounty.id}/claim', data={'message': 'done'})

    login(client, poster_username, 'password')
    claim = BountyClaim.query.filter_by(bounty_id=bounty.id, status='pending').first()
    assert claim is not None, f'No pending claim found for bounty {bounty.id}'
    client.post(f'/bounty/claim/{claim.id}/approve')
    return bounty


def verify_balance_integrity(app):
    """Verify cached balances match replayed transactions."""
    from app.models.balance import Balance
    from app.models.transaction import Transaction

    with app.app_context():
        # Replay transactions to compute expected balances
        expected = {}  # (holder_id, source_id) -> amount

        transactions = Transaction.query.filter_by(is_invalidated=False).order_by(
            Transaction.created_at.asc(), Transaction.id.asc()
        ).all()

        def _credit(holder, source, amt):
            key = (holder, source)
            expected[key] = round(expected.get(key, 0.0) + amt, 10)

        def _debit_fifo(holder, amt):
            holder_bals = sorted(
                [(k, v) for k, v in expected.items() if k[0] == holder and v > 0],
                key=lambda x: x[0][1]
            )
            remaining = amt
            for key, val in holder_bals:
                if remaining <= 0:
                    break
                deduct = min(val, remaining)
                expected[key] = round(val - deduct, 10)
                remaining = round(remaining - deduct, 10)

        for txn in transactions:
            if txn.type == 'bounty_payout':
                _credit(txn.to_user_id, txn.from_user_id, txn.amount)
            elif txn.type == 'send':
                _debit_fifo(txn.from_user_id, txn.amount)
                _credit(txn.to_user_id, txn.from_user_id, txn.amount)
            elif txn.type == 'burn':
                key = (txn.to_user_id, txn.from_user_id)
                expected[key] = round(expected.get(key, 0.0) - txn.amount, 10)

        # Compare with cached balances
        cached = {}
        for bal in Balance.query.all():
            if abs(bal.amount) > 1e-9:
                cached[(bal.holder_user_id, bal.source_user_id)] = round(bal.amount, 10)

        # Remove zero entries from expected
        expected_clean = {k: v for k, v in expected.items() if abs(v) > 1e-9}

        assert cached == expected_clean, f"Balance mismatch!\nCached: {cached}\nExpected: {expected_clean}"
