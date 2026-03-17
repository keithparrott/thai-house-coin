from app.extensions import db
from app.models.transaction import Transaction
from app.services import balance_service


def record_bounty_payout(poster_id, claimant_id, amount, memo=''):
    txn = Transaction(
        type='bounty_payout',
        from_user_id=poster_id,
        to_user_id=claimant_id,
        amount=amount,
        memo=memo
    )
    db.session.add(txn)
    balance_service.credit_balance(claimant_id, poster_id, amount)
    db.session.flush()
    return txn


def record_send(sender_id, recipient_id, amount, memo=''):
    success = balance_service.debit_fifo(sender_id, amount)
    if not success:
        raise ValueError('Insufficient balance')

    txn = Transaction(
        type='send',
        from_user_id=sender_id,
        to_user_id=recipient_id,
        amount=amount,
        memo=memo
    )
    db.session.add(txn)
    balance_service.credit_balance(recipient_id, sender_id, amount)
    db.session.flush()
    return txn


def record_burn(target_id, requester_id, amount, memo=''):
    """Burn THC: debit from requester's balance sourced from target."""
    balance_service.debit_balance(requester_id, target_id, amount)

    txn = Transaction(
        type='burn',
        from_user_id=target_id,
        to_user_id=requester_id,
        amount=amount,
        memo=memo
    )
    db.session.add(txn)
    db.session.flush()
    return txn
