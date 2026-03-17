from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.models.balance import Balance
from app.models.transaction import Transaction
from app.models.redemption import Redemption
from app.models.bounty import BountyClaim
from app.extensions import db

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    balances = Balance.query.filter(
        Balance.holder_user_id == current_user.id,
        Balance.amount > 0
    ).all()
    total_balance = sum(b.amount for b in balances)

    pending_redemptions_in = Redemption.query.filter_by(
        target_id=current_user.id, status='pending'
    ).count()
    pending_redemptions_out = Redemption.query.filter_by(
        requester_id=current_user.id, status='pending'
    ).count()

    pending_claims = BountyClaim.query.join(BountyClaim.bounty).filter(
        BountyClaim.status == 'pending',
        db.or_(
            BountyClaim.claimant_id == current_user.id,
            BountyClaim.bounty.has(poster_id=current_user.id)
        )
    ).count()

    recent_txns = Transaction.query.filter(
        db.or_(
            Transaction.from_user_id == current_user.id,
            Transaction.to_user_id == current_user.id
        )
    ).order_by(Transaction.created_at.desc()).limit(10).all()

    top_sources = sorted(balances, key=lambda b: b.amount, reverse=True)[:5]

    return render_template('dashboard.html',
                           total_balance=total_balance,
                           top_sources=top_sources,
                           pending_redemptions_in=pending_redemptions_in,
                           pending_redemptions_out=pending_redemptions_out,
                           pending_claims=pending_claims,
                           recent_txns=recent_txns)
