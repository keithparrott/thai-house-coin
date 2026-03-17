from flask import Blueprint, render_template, request
from flask_login import login_required

from app.models.transaction import Transaction
from app.models.user import User

ledger_bp = Blueprint('ledger', __name__, url_prefix='/ledger')


@ledger_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    txn_type = request.args.get('type', '', type=str)
    user_id = request.args.get('user', 0, type=int)

    query = Transaction.query

    if txn_type:
        query = query.filter(Transaction.type == txn_type)
    if user_id:
        query = query.filter(
            (Transaction.from_user_id == user_id) | (Transaction.to_user_id == user_id)
        )

    pagination = query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )

    users = User.query.filter_by(is_active=True).order_by(User.display_name).all()

    return render_template('ledger.html',
                           transactions=pagination.items,
                           pagination=pagination,
                           txn_type=txn_type,
                           user_id=user_id,
                           users=users)
