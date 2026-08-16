from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.models.bounty import Bounty, BountyClaim, BountyContribution
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
    if not bounty or bounty.status not in ('open', 'pending'):
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
    bounty.status = 'pending'
    db.session.flush()
    return claim


def contribute_to_bounty(bounty_id, contributor_id, amount):
    bounty = db.session.get(Bounty, bounty_id)
    if not bounty:
        raise ValueError('Bounty not found.')
    if bounty.poster_id == contributor_id:
        raise ValueError('You cannot contribute to your own bounty.')
    if bounty.status not in ('open', 'pending'):
        raise ValueError('This bounty is no longer accepting contributions.')

    contribution = BountyContribution.query.filter_by(
        bounty_id=bounty_id, contributor_id=contributor_id
    ).first()
    if contribution:
        contribution.amount = round(contribution.amount + amount, 2)
    else:
        contribution = BountyContribution(
            bounty_id=bounty_id,
            contributor_id=contributor_id,
            amount=amount
        )
        db.session.add(contribution)

    db.session.flush()
    return contribution


def approve_claim(claim_id, poster_id):
    claim = db.session.get(BountyClaim, claim_id)
    if not claim:
        raise ValueError('Claim not found.')
    bounty = claim.bounty
    if bounty.poster_id != poster_id:
        raise ValueError('Only the poster can approve claims.')
    if bounty.status not in ('open', 'pending'):
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

    # Mint THC from the original poster's reward
    transaction_service.record_bounty_payout(
        poster_id=bounty.poster_id,
        claimant_id=claim.claimant_id,
        amount=bounty.reward_amount,
        memo=f'Bounty: {bounty.title}'
    )

    # Mint THC from each contributor, source-tagged to them individually
    # so it remains separately redeemable (see source-tagged balance model).
    for contribution in bounty.contributions.all():
        if contribution.amount > 0:
            transaction_service.record_bounty_payout(
                poster_id=contribution.contributor_id,
                claimant_id=claim.claimant_id,
                amount=contribution.amount,
                memo=f'Bounty contribution: {bounty.title}'
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

    # If no pending claims remain, revert bounty to open
    bounty = claim.bounty
    remaining = BountyClaim.query.filter_by(bounty_id=bounty.id, status='pending').count()
    if remaining == 0:
        bounty.status = 'open'

    db.session.flush()
    return claim


REMOVED_NOTICE = '[Removed by an admin]'


def admin_remove_bounty(bounty_id):
    """Moderation takedown. Redacts the text rather than deleting the row —
    cancelled bounties stay listed on the board, so a status change alone
    would leave the offending content on screen."""
    bounty = db.session.get(Bounty, bounty_id)
    if not bounty:
        raise ValueError('Bounty not found.')

    bounty.title = REMOVED_NOTICE
    bounty.description = ''

    # Close it only if it is still live. A completed bounty already paid out,
    # so its status must stay accurate — we only strip the text.
    if bounty.status in ('open', 'pending'):
        BountyClaim.query.filter_by(bounty_id=bounty_id, status='pending').update({'status': 'rejected'})
        bounty.status = 'cancelled'

    db.session.flush()
    return bounty


def admin_remove_claim(claim_id):
    """Moderation takedown for a claim message. Rejecting alone is not enough:
    claim text renders regardless of status."""
    claim = db.session.get(BountyClaim, claim_id)
    if not claim:
        raise ValueError('Claim not found.')

    claim.message = REMOVED_NOTICE
    if claim.status == 'pending':
        claim.status = 'rejected'
        bounty = claim.bounty
        remaining = BountyClaim.query.filter(
            BountyClaim.bounty_id == bounty.id,
            BountyClaim.id != claim.id,
            BountyClaim.status == 'pending'
        ).count()
        if remaining == 0 and bounty.status == 'pending':
            bounty.status = 'open'

    db.session.flush()
    return claim


def cancel_bounty(bounty_id, poster_id):
    bounty = db.session.get(Bounty, bounty_id)
    if not bounty or bounty.poster_id != poster_id:
        raise ValueError('Not your bounty.')
    if bounty.status not in ('open', 'pending'):
        raise ValueError('Can only cancel open bounties.')

    # Reject any pending claims on cancellation
    BountyClaim.query.filter_by(bounty_id=bounty_id, status='pending').update({'status': 'rejected'})

    bounty.status = 'cancelled'
    db.session.flush()
    return bounty
