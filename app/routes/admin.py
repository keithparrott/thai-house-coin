from functools import wraps
from datetime import datetime, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models.user import User
from app.models.transaction import Transaction
from app.forms.admin_forms import CreateUserForm, ResetPasswordForm, AdminEditUserForm
from app.services import bounty_service
from app.services.balance_service import rebuild_all_balances
from app.services import user_service

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
        elif user_service.display_name_taken(form.display_name.data):
            flash('That display name is already in use.', 'error')
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


@admin_bp.route('/edit-user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.panel'))

    form = AdminEditUserForm(obj=user)
    if form.validate_on_submit():
        try:
            user_service.update_profile(user, form.display_name.data, user.email)
            db.session.commit()
            flash(f'Display name updated for "{user.username}".', 'success')
            return redirect(url_for('admin.panel'))
        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'error')
    return render_template('admin/edit_user.html', form=form, target_user=user)


@admin_bp.route('/bounty/<int:bounty_id>/remove', methods=['POST'])
@admin_required
def remove_bounty(bounty_id):
    try:
        bounty_service.admin_remove_bounty(bounty_id)
        db.session.commit()
        flash('Bounty removed.', 'success')
    except ValueError as e:
        db.session.rollback()
        flash(str(e), 'error')
    return redirect(url_for('bounty.detail', bounty_id=bounty_id))


@admin_bp.route('/claim/<int:claim_id>/remove', methods=['POST'])
@admin_required
def remove_claim(claim_id):
    try:
        claim = bounty_service.admin_remove_claim(claim_id)
        bounty_id = claim.bounty_id
        db.session.commit()
        flash('Claim removed.', 'success')
        return redirect(url_for('bounty.detail', bounty_id=bounty_id))
    except ValueError as e:
        db.session.rollback()
        flash(str(e), 'error')
        return redirect(url_for('bounty.board'))


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
