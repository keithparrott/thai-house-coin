from app.extensions import db
from app.models.user import User
from app.models.balance import Balance
from app.models.transaction import Transaction
from app.models.redemption import Redemption
from app.models.bounty import Bounty, BountyClaim, BountyContribution
from app.services import balance_service


def display_name_taken(display_name, exclude_user_id=None):
    """Case-insensitive check so 'Keith' and 'keith' are treated as the same name."""
    query = User.query.filter(
        db.func.lower(User.display_name) == display_name.strip().lower()
    )
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    return query.first() is not None


def email_taken(email, exclude_user_id=None):
    query = User.query.filter(db.func.lower(User.email) == email.strip().lower())
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    return query.first() is not None


def update_profile(user, display_name, email):
    display_name = (display_name or '').strip()
    email = (email or '').strip() or None

    if not display_name:
        raise ValueError('Display name is required.')
    if display_name_taken(display_name, exclude_user_id=user.id):
        raise ValueError('That display name is already in use.')
    if email and email_taken(email, exclude_user_id=user.id):
        raise ValueError('That email address is already in use.')

    user.display_name = display_name
    user.email = email
    db.session.flush()
    return user


def get_profile_stats(user_id):
    """Aggregate the public economy figures shown on a user's profile."""
    liabilities = db.session.query(
        db.func.coalesce(db.func.sum(Balance.amount), 0.0)
    ).filter(
        Balance.source_user_id == user_id,
        Balance.holder_user_id != user_id,
        Balance.amount > 0
    ).scalar()

    minted = db.session.query(
        db.func.coalesce(db.func.sum(Transaction.amount), 0.0)
    ).filter(
        Transaction.type == 'bounty_payout',
        Transaction.from_user_id == user_id,
        Transaction.is_invalidated == False  # noqa: E712
    ).scalar()

    return {
        'holdings': balance_service.get_total_balance(user_id),
        'liabilities': float(liabilities),
        'thc_minted': float(minted),
        'lunches_eaten': Redemption.query.filter_by(
            requester_id=user_id, status='accepted').count(),
        'lunches_given': Redemption.query.filter_by(
            target_id=user_id, status='accepted').count(),
        'lunches_owed': balance_service.get_lunches_owed(user_id),
        'lunches_redeemable': balance_service.get_lunches_redeemable(user_id),
        'bounties_posted': Bounty.query.filter_by(poster_id=user_id).count(),
        'bounties_open': Bounty.query.filter(
            Bounty.poster_id == user_id,
            Bounty.status.in_(['open', 'pending'])
        ).count(),
        'bounties_completed': BountyClaim.query.filter_by(
            claimant_id=user_id, status='approved').count(),
        'contributions_made': BountyContribution.query.filter_by(
            contributor_id=user_id).count(),
    }
