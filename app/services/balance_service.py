from app.extensions import db
from app.models.balance import Balance
from app.models.transaction import Transaction


def get_total_balance(user_id):
    result = db.session.query(db.func.coalesce(db.func.sum(Balance.amount), 0.0)).filter(
        Balance.holder_user_id == user_id,
        Balance.amount > 0
    ).scalar()
    return float(result)


def get_source_balance(holder_id, source_id):
    bal = Balance.query.filter_by(holder_user_id=holder_id, source_user_id=source_id).first()
    return bal.amount if bal else 0.0


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
