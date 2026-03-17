from datetime import datetime, timezone

from app.extensions import db
from app.models.redemption import Redemption
from app.services import balance_service, transaction_service


def request_redemption(requester_id, target_id):
    source_bal = balance_service.get_source_balance(requester_id, target_id)
    if source_bal < 1.0:
        raise ValueError('You need at least 1.0 THC from this person to redeem.')

    # Check no existing pending redemption for same pair
    existing = Redemption.query.filter_by(
        requester_id=requester_id, target_id=target_id, status='pending'
    ).first()
    if existing:
        raise ValueError('You already have a pending redemption from this person.')

    redemption = Redemption(
        requester_id=requester_id,
        target_id=target_id,
        amount=1.0
    )
    db.session.add(redemption)
    db.session.flush()
    return redemption


def accept_redemption(redemption_id, target_id):
    redemption = db.session.get(Redemption, redemption_id)
    if not redemption or redemption.target_id != target_id:
        raise ValueError('Not your redemption to accept.')
    if redemption.status != 'pending':
        raise ValueError('Redemption is not pending.')

    # Verify balance still sufficient
    source_bal = balance_service.get_source_balance(redemption.requester_id, redemption.target_id)
    if source_bal < 1.0:
        raise ValueError('Requester no longer has enough THC from you.')

    # Burn 1.0 THC
    transaction_service.record_burn(
        target_id=redemption.target_id,
        requester_id=redemption.requester_id,
        amount=1.0,
        memo='Redemption accepted'
    )

    redemption.status = 'accepted'
    redemption.resolved_at = datetime.now(timezone.utc)
    db.session.flush()
    return redemption


def decline_redemption(redemption_id, target_id):
    redemption = db.session.get(Redemption, redemption_id)
    if not redemption or redemption.target_id != target_id:
        raise ValueError('Not your redemption to decline.')
    if redemption.status != 'pending':
        raise ValueError('Redemption is not pending.')

    redemption.status = 'declined'
    redemption.resolved_at = datetime.now(timezone.utc)
    db.session.flush()
    return redemption


def cancel_redemption(redemption_id, requester_id):
    redemption = db.session.get(Redemption, redemption_id)
    if not redemption or redemption.requester_id != requester_id:
        raise ValueError('Not your redemption to cancel.')
    if redemption.status != 'pending':
        raise ValueError('Redemption is not pending.')

    redemption.status = 'cancelled'
    redemption.resolved_at = datetime.now(timezone.utc)
    db.session.flush()
    return redemption
