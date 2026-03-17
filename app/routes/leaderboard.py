from flask import Blueprint, render_template
from flask_login import login_required

from app.extensions import db
from app.models.user import User
from app.models.balance import Balance

leaderboard_bp = Blueprint('leaderboard', __name__, url_prefix='/leaderboard')


@leaderboard_bp.route('/')
@login_required
def index():
    # Aggregate total balance per user
    results = db.session.query(
        Balance.holder_user_id,
        db.func.sum(Balance.amount).label('total')
    ).filter(Balance.amount > 0).group_by(Balance.holder_user_id).all()

    user_totals = {r.holder_user_id: float(r.total) for r in results}

    users = User.query.filter_by(is_active=True).all()
    leaderboard = []
    for user in users:
        leaderboard.append({
            'user': user,
            'total': user_totals.get(user.id, 0.0)
        })
    leaderboard.sort(key=lambda x: x['total'], reverse=True)

    return render_template('leaderboard.html', leaderboard=leaderboard)
