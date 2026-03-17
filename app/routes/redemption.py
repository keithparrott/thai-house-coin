from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models.user import User
from app.models.balance import Balance
from app.models.redemption import Redemption
from app.forms.redemption_forms import RedeemForm
from app.services import redemption_service

redemption_bp = Blueprint('redemption', __name__, url_prefix='/redemption')


@redemption_bp.route('/')
@login_required
def index():
    # Sources with >= 1.0 THC (redeemable)
    redeemable = Balance.query.filter(
        Balance.holder_user_id == current_user.id,
        Balance.amount >= 1.0
    ).all()

    form = RedeemForm()
    form.target.choices = [(b.source_user_id, f'{b.source.display_name} ({b.amount:.2f} THC)') for b in redeemable]

    outgoing = Redemption.query.filter_by(requester_id=current_user.id).order_by(
        Redemption.created_at.desc()
    ).all()
    incoming = Redemption.query.filter_by(target_id=current_user.id).order_by(
        Redemption.created_at.desc()
    ).all()

    return render_template('redemption/index.html',
                           form=form,
                           outgoing=outgoing,
                           incoming=incoming,
                           redeemable=redeemable)


@redemption_bp.route('/request', methods=['POST'])
@login_required
def request_redemption():
    # Re-populate choices for validation
    redeemable = Balance.query.filter(
        Balance.holder_user_id == current_user.id,
        Balance.amount >= 1.0
    ).all()
    form = RedeemForm()
    form.target.choices = [(b.source_user_id, b.source.display_name) for b in redeemable]

    if form.validate_on_submit():
        try:
            redemption_service.request_redemption(current_user.id, form.target.data)
            db.session.commit()
            flash('Redemption requested!', 'success')
        except ValueError as e:
            flash(str(e), 'error')
    return redirect(url_for('redemption.index'))


@redemption_bp.route('/<int:redemption_id>/accept', methods=['POST'])
@login_required
def accept(redemption_id):
    try:
        redemption_service.accept_redemption(redemption_id, current_user.id)
        db.session.commit()
        flash('Redemption accepted! 1.0 THC burned. Time for Thai food!', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(url_for('redemption.index'))


@redemption_bp.route('/<int:redemption_id>/decline', methods=['POST'])
@login_required
def decline(redemption_id):
    try:
        redemption_service.decline_redemption(redemption_id, current_user.id)
        db.session.commit()
        flash('Redemption declined.', 'info')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(url_for('redemption.index'))


@redemption_bp.route('/<int:redemption_id>/cancel', methods=['POST'])
@login_required
def cancel(redemption_id):
    try:
        redemption_service.cancel_redemption(redemption_id, current_user.id)
        db.session.commit()
        flash('Redemption cancelled.', 'info')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(url_for('redemption.index'))
