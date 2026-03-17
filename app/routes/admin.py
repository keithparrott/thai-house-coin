from functools import wraps
from datetime import datetime, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models.user import User
from app.models.transaction import Transaction
from app.forms.admin_forms import CreateUserForm, ResetPasswordForm
from app.services.balance_service import rebuild_all_balances

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@admin_required
def panel():
    users = User.query.order_by(User.created_at.asc()).all()
    return render_template('admin/panel.html', users=users)


@admin_bp.route('/create-user', methods=['GET', 'POST'])
@admin_required
def create_user():
    form = CreateUserForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists.', 'error')
        else:
            user = User(
                username=form.username.data,
                display_name=form.display_name.data,
                role='admin' if form.is_admin.data else 'user',
                must_change_password=True
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash(f'User "{user.username}" created.', 'success')
            return redirect(url_for('admin.panel'))
    return render_template('admin/create_user.html', form=form)


@admin_bp.route('/reset-password/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def reset_password(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.panel'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.new_password.data)
        user.must_change_password = True
        db.session.commit()
        flash(f'Password reset for "{user.username}".', 'success')
        return redirect(url_for('admin.panel'))
    return render_template('admin/reset_password.html', form=form, target_user=user)


@admin_bp.route('/toggle-active/<int:user_id>', methods=['POST'])
@admin_required
def toggle_active(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'error')
    elif user.id == current_user.id:
        flash('You cannot deactivate yourself.', 'error')
    else:
        user.is_active = not user.is_active
        db.session.commit()
        status = 'activated' if user.is_active else 'deactivated'
        flash(f'User "{user.username}" {status}.', 'success')
    return redirect(url_for('admin.panel'))


@admin_bp.route('/invalidate/<int:txn_id>', methods=['GET', 'POST'])
@admin_required
def invalidate_transaction(txn_id):
    txn = db.session.get(Transaction, txn_id)
    if not txn:
        flash('Transaction not found.', 'error')
        return redirect(url_for('ledger.index'))

    if txn.is_invalidated:
        flash('Transaction is already invalidated.', 'error')
        return redirect(url_for('ledger.index'))

    if request.method == 'POST':
        txn.is_invalidated = True
        txn.invalidated_by = current_user.id
        txn.invalidated_at = datetime.now(timezone.utc)
        rebuild_all_balances()
        db.session.commit()
        flash(f'Transaction #{txn.id} invalidated. All balances recalculated.', 'success')
        return redirect(url_for('ledger.index'))

    return render_template('admin/invalidate.html', txn=txn)
