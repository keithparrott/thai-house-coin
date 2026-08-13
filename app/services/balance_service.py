import math

from app.extensions import db
from app.models.balance import Balance
from app.models.transaction import Transaction
from app.models.user import User


def get_total_balance(user_id):
    result = db.session.query(db.func.coalesce(db.func.sum(Balance.amount), 0.0)).filter(
        Balance.holder_user_id == user_id,
        Balance.amount > 0
    ).scalar()
    return float(result)


def get_source_balance(holder_id, source_id):
    bal = Balance.query.filter_by(holder_user_id=holder_id, source_user_id=source_id).first()
    return bal.amount if bal else 0.0


def get_balance_matrix(user_id):
    """Per-counterparty view of THC owed in both directions for `user_id`.

    Returns a list of {user, you_owe_them, they_owe_you} rows, one per user
    who currently holds THC sourced from `user_id` and/or is a source of
    THC that `user_id` currently holds. Sorted by combined amount desc.
    """
    they_owe_you = {
        b.source_user_id: b.amount for b in
        Balance.query.filter(Balance.holder_user_id == user_id, Balance.amount > 0).all()
    }
    you_owe_them = {
        b.holder_user_id: b.amount for b in
        Balance.query.filter(Balance.source_user_id == user_id, Balance.holder_user_id != user_id,
                              Balance.amount > 0).all()
    }

    counterparty_ids = set(they_owe_you) | set(you_owe_them)
    users = {u.id: u for u in User.query.filter(User.id.in_(counterparty_ids)).all()} if counterparty_ids else {}

    rows = []
    for cid in counterparty_ids:
        rows.append({
            'user': users[cid],
            'you_owe_them': you_owe_them.get(cid, 0.0),
            'they_owe_you': they_owe_you.get(cid, 0.0),
        })
    rows.sort(key=lambda r: r['you_owe_them'] + r['they_owe_you'], reverse=True)
    return rows


def get_lunches_owed(user_id):
    """Total lunches `user_id` owes: sum of whole lunches (floor) across every
    counterparty who holds >= 1.0 THC sourced from `user_id`."""
    balances = Balance.query.filter(
        Balance.source_user_id == user_id,
        Balance.holder_user_id != user_id,
        Balance.amount >= 1.0
    ).all()
    return sum(int(math.floor(b.amount)) for b in balances)


def get_lunches_redeemable(user_id):
    """Total lunches `user_id` can redeem: sum of whole lunches (floor) across
    every source `user_id` holds >= 1.0 THC from."""
    balances = Balance.query.filter(
        Balance.holder_user_id == user_id,
        Balance.amount >= 1.0
    ).all()
    return sum(int(math.floor(b.amount)) for b in balances)


def credit_balance(holder_id, source_id, amount):
    bal = Balance.query.filter_by(holder_user_id=holder_id, source_user_id=source_id).first()
    if bal:
        bal.amount = round(bal.amount + amount, 10)
    else:
        bal = Balance(holder_user_id=holder_id, source_user_id=source_id, amount=amount)
        db.session.add(bal)


def debit_balance(holder_id, source_id, amount):
    bal = Balance.query.filter_by(holder_user_id=holder_id, source_user_id=source_id).first()
    if bal:
        bal.amount = round(bal.amount - amount, 10)


def debit_fifo(holder_id, amount):
    """Debit `amount` from holder's balances using FIFO (source_user_id ASC)."""
    balances = Balance.query.filter(
        Balance.holder_user_id == holder_id,
        Balance.amount > 0
    ).order_by(Balance.source_user_id.asc()).all()

    remaining = amount
    for bal in balances:
        if remaining <= 0:
            break
        deduct = min(bal.amount, remaining)
        bal.amount = round(bal.amount - deduct, 10)
        remaining = round(remaining - deduct, 10)

    return remaining <= 1e-9  # success if fully deducted


def rebuild_all_balances():
    """Wipe balance cache and replay all non-invalidated transactions."""
    Balance.query.delete()

    transactions = Transaction.query.filter_by(is_invalidated=False).order_by(
        Transaction.created_at.asc(), Transaction.id.asc()
    ).all()

    # We need to track balances in memory for FIFO send replays
    # balances_map: {(holder_id, source_id): amount}
    balances_map = {}

    def _credit(holder, source, amt):
        key = (holder, source)
        balances_map[key] = round(balances_map.get(key, 0.0) + amt, 10)

    def _debit_fifo_map(holder, amt):
        holder_balances = sorted(
            [(k, v) for k, v in balances_map.items() if k[0] == holder and v > 0],
            key=lambda x: x[0][1]  # sort by source_user_id ASC
        )
        remaining = amt
        for key, val in holder_balances:
            if remaining <= 0:
                break
            deduct = min(val, remaining)
            balances_map[key] = round(val - deduct, 10)
            remaining = round(remaining - deduct, 10)

    for txn in transactions:
        if txn.type == 'bounty_payout':
            # Mint: credit claimant with source=poster
            _credit(txn.to_user_id, txn.from_user_id, txn.amount)
        elif txn.type == 'send':
            # Debit sender FIFO, credit recipient with source=sender
            _debit_fifo_map(txn.from_user_id, txn.amount)
            _credit(txn.to_user_id, txn.from_user_id, txn.amount)
        elif txn.type == 'burn':
            # Debit specific source from holder
            # from_user_id = target (source), to_user_id = requester (holder)
            key = (txn.to_user_id, txn.from_user_id)
            balances_map[key] = round(balances_map.get(key, 0.0) - txn.amount, 10)

    # Write back to DB
    for (holder_id, source_id), amount in balances_map.items():
        if abs(amount) > 1e-9:
            db.session.add(Balance(
                holder_user_id=holder_id,
                source_user_id=source_id,
                amount=round(amount, 10)
            ))

    db.session.flush()
