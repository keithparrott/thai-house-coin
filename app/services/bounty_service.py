from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.models.bounty import Bounty, BountyClaim
from app.services import transaction_service


def create_bounty(poster_id, title, description, reward_amount):
    open_count = Bounty.query.filter_by(poster_id=poster_id, status='open').count()
    if open_count >= 5:
        raise ValueError('You can have at most 5 open bounties.')

    bounty = Bounty(
        poster_id=poster_id,
        title=title,
        description=description,
        reward_amount=reward_amount
    )
    db.session.add(bounty)
    db.session.flush()
    return bounty


def submit_claim(bounty_id, claimant_id, message):
    bounty = db.session.get(Bounty, bounty_id)
    if not bounty or bounty.status != 'open':
        raise ValueError('Bounty is not open.')
    if bounty.poster_id == claimant_id:
        raise ValueError('You cannot claim your own bounty.')

    # Check 10-minute cooldown
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    recent = BountyClaim.query.filter(
        BountyClaim.bounty_id == bounty_id,
        BountyClaim.claimant_id == claimant_id,
        BountyClaim.submitted_at > cutoff
    ).first()
    if recent:
        raise ValueError('Please wait 10 minutes between claim submissions.')

    claim = BountyClaim(
        bounty_id=bounty_id,
        claimant_id=claimant_id,
        message=message
    )
    db.session.add(claim)
    db.session.flush()
    return claim


def approve_claim(claim_id, poster_id):
    claim = db.session.get(BountyClaim, claim_id)
    if not claim:
        raise ValueError('Claim not found.')
    bounty = claim.bounty
    if bounty.poster_id != poster_id:
        raise ValueError('Only the poster can approve claims.')
    if bounty.status != 'open':
        raise ValueError('Bounty is no longer open.')
    if claim.status != 'pending':
        raise ValueError('Claim is not pending.')

    claim.status = 'approved'
    bounty.status = 'completed'
    bounty.completed_at = datetime.now(timezone.utc)

    # Reject all other pending claims
    BountyClaim.query.filter(
        BountyClaim.bounty_id == bounty.id,
        BountyClaim.id != claim.id,
        BountyClaim.status == 'pending'
    ).update({'status': 'rejected'})

    # Mint THC
    transaction_service.record_bounty_payout(
        poster_id=bounty.poster_id,
        claimant_id=claim.claimant_id,
        amount=bounty.reward_amount,
        memo=f'Bounty: {bounty.title}'
    )

    db.session.flush()
    return claim


def reject_claim(claim_id, poster_id):
    claim = db.session.get(BountyClaim, claim_id)
    if not claim:
        raise ValueError('Claim not found.')
    if claim.bounty.poster_id != poster_id:
        raise ValueError('Only the poster can reject claims.')
    if claim.status != 'pending':
        raise ValueError('Claim is not pending.')

    claim.status = 'rejected'
    db.session.flush()
    return claim


def cancel_bounty(bounty_id, poster_id):
    bounty = db.session.get(Bounty, bounty_id)
    if not bounty or bounty.poster_id != poster_id:
        raise ValueError('Not your bounty.')
    if bounty.status != 'open':
        raise ValueError('Can only cancel open bounties.')

    pending = BountyClaim.query.filter_by(bounty_id=bounty_id, status='pending').count()
    if pending > 0:
        raise ValueError('Cannot cancel a bounty with pending claims.')

    bounty.status = 'cancelled'
    db.session.flush()
    return bounty
