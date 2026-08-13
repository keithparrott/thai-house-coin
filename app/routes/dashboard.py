from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.models.transaction import Transaction
from app.models.redemption import Redemption
from app.models.bounty import Bounty
from app.extensions import db
from app.services import balance_service

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    lunches_eaten = Redemption.query.filter_by(
        requester_id=current_user.id, status='accepted'
    ).count()
    lunches_given = Redemption.query.filter_by(
        target_id=current_user.id, status='accepted'
    ).count()
    lunches_owed = balance_service.get_lunches_owed(current_user.id)
    lunches_redeemable = balance_service.get_lunches_redeemable(current_user.id)

    pending_bounties = Bounty.query.filter_by(
        poster_id=current_user.id, status='pending'
    ).order_by(Bounty.created_at.desc()).all()

    pending_redemptions = Redemption.query.filter_by(
        target_id=current_user.id, status='pending'
    ).order_by(Redemption.created_at.desc()).all()

    open_bounties = Bounty.query.filter(
        Bounty.status.in_(['open', 'pending'])
    ).order_by(Bounty.created_at.desc()).all()

    recent_txns = Transaction.query.filter(
        db.or_(
            Transaction.from_user_id == current_user.id,
            Transaction.to_user_id == current_user.id
        )
    ).order_by(Transaction.created_at.desc()).limit(10).all()

    return render_template('dashboard.html',
                           lunches_eaten=lunches_eaten,
                           lunches_given=lunches_given,
                           lunches_owed=lunches_owed,
                           lunches_redeemable=lunches_redeemable,
                           pending_bounties=pending_bounties,
                           pending_redemptions=pending_redemptions,
                           open_bounties=open_bounties,
                           recent_txns=recent_txns)
