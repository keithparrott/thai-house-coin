from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models.user import User
from app.models.balance import Balance
from app.forms.wallet_forms import SendForm
from app.services import balance_service, transaction_service

wallet_bp = Blueprint('wallet', __name__, url_prefix='/wallet')


@wallet_bp.route('/')
@login_required
def index():
    balances = Balance.query.filter(
        Balance.holder_user_id == current_user.id,
        Balance.amount > 0
    ).order_by(Balance.amount.desc()).all()
    total = sum(b.amount for b in balances)
    return render_template('wallet/index.html', balances=balances, total=total)


@wallet_bp.route('/send', methods=['GET', 'POST'])
@login_required
def send():
    form = SendForm()
    users = User.query.filter(User.id != current_user.id, User.is_active == True).order_by(User.display_name).all()
    form.recipient.choices = [(u.id, u.display_name) for u in users]

    if form.validate_on_submit():
        total = balance_service.get_total_balance(current_user.id)
        amount = round(form.amount.data, 2)
        if amount > total:
            flash(f'Insufficient balance. You have {total:.2f} THC.', 'error')
        else:
            try:
                transaction_service.record_send(current_user.id, form.recipient.data, amount)
                db.session.commit()
                recipient = db.session.get(User, form.recipient.data)
                flash(f'Sent {amount:.2f} THC to {recipient.display_name}.', 'success')
                return redirect(url_for('wallet.index'))
            except ValueError as e:
                flash(str(e), 'error')

    return render_template('wallet/send.html', form=form)
