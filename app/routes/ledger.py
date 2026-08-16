from flask import Blueprint, render_template, request
from flask_login import login_required

from app.models.transaction import Transaction
from app.models.user import User
from app.models.admin_action import AdminAction
from app.services import audit_service

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


@ledger_bp.route('/admin-actions')
@login_required
def admin_actions():
    """Public record of privileged actions. Readable by everyone by design —
    an audit trail only admins can see is not much of a check on admins."""
    page = request.args.get('page', 1, type=int)
    pagination = AdminAction.query.order_by(AdminAction.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    return render_template('admin_actions.html',
                           actions=pagination.items,
                           pagination=pagination,
                           label_for=audit_service.label_for)
