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
from app.services import user_service, audit_service

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
            db.session.flush()
            audit_service.record(
                current_user.id, 'create_user', target_type='user',
                target_id=user.id, target_user_id=user.id,
                detail='as an admin' if user.is_admin else ''
            )
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
        audit_service.record(current_user.id, 'reset_password', target_type='user',
                             target_id=user.id, target_user_id=user.id)
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
            # Deliberately not logging the previous name: an admin clearing an
            # offensive one would otherwise republish it in the public log.
            audit_service.record(current_user.id, 'rename_user', target_type='user',
                                 target_id=user.id, target_user_id=user.id)
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
        bounty = bounty_service.admin_remove_bounty(bounty_id)
        audit_service.record(current_user.id, 'remove_bounty', target_type='bounty',
                             target_id=bounty.id, target_user_id=bounty.poster_id)
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
        audit_service.record(current_user.id, 'remove_claim', target_type='claim',
                             target_id=claim.id, target_user_id=claim.claimant_id)
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
        audit_service.record(
            current_user.id,
            'activate_user' if user.is_active else 'deactivate_user',
            target_type='user', target_id=user.id, target_user_id=user.id
        )
        db.session.commit()
        status = 'activated' if user.is_active else 'deactivated'
        flash(f'User "{user.username}" {status}.', 'success')
    return redirect(url_for('admin.panel'))


@admin_bp.route('/toggle-role/<int:user_id>', methods=['POST'])
@admin_required
def toggle_role(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.panel'))

    if user.id == current_user.id:
        flash('You cannot change your own role.', 'error')
        return redirect(url_for('admin.panel'))

    if user.is_admin:
        # Defensive: the self-check above already makes zero admins
        # unreachable, but state the invariant explicitly.
        remaining = User.query.filter(User.role == 'admin', User.id != user.id).count()
        if remaining == 0:
            flash('There must be at least one admin.', 'error')
            return redirect(url_for('admin.panel'))
        user.role = 'user'
        action, verb = 'revoke_admin', 'is no longer an admin'
    else:
        user.role = 'admin'
        action, verb = 'grant_admin', 'is now an admin'

    audit_service.record(current_user.id, action, target_type='user',
                         target_id=user.id, target_user_id=user.id)
    db.session.commit()
    flash(f'"{user.username}" {verb}.', 'success')
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
        audit_service.record(current_user.id, 'invalidate_transaction',
                             target_type='transaction', target_id=txn.id,
                             detail=f'{txn.type} of {txn.amount:.2f} THC')
        db.session.commit()
        flash(f'Transaction #{txn.id} invalidated. All balances recalculated.', 'success')
        return redirect(url_for('ledger.index'))

    return render_template('admin/invalidate.html', txn=txn)
