from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models.user import User
from app.models.balance import Balance
from app.forms.wallet_forms import SendForm, MINT_SOURCE, MAX_MINT_AMOUNT
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
    matrix = balance_service.get_balance_matrix(current_user.id)
    return render_template('wallet/index.html', balances=balances, total=total, matrix=matrix)


@wallet_bp.route('/send', methods=['GET', 'POST'])
@login_required
def send():
    form = SendForm()
    users = User.query.filter(User.id != current_user.id, User.is_active == True).order_by(User.display_name).all()
    form.recipient.choices = [(u.id, u.display_name) for u in users]

    balances = Balance.query.filter(
        Balance.holder_user_id == current_user.id,
        Balance.amount > 0
    ).order_by(Balance.amount.desc()).all()

    form.source.choices = [
        (b.source_user_id, f'{b.source.display_name} ({b.amount:.2f} THC available)')
        for b in balances
    ] + [(MINT_SOURCE, 'Mint new THC (creates new supply)')]

    # Data for the live "after this transaction" summary.
    summary_data = {
        'sources': {
            str(b.source_user_id): {'name': b.source.display_name, 'amount': round(b.amount, 2)}
            for b in balances
        },
        'recipients': {
            str(u.id): {
                'name': u.display_name,
                'holds_from_you': round(
                    balance_service.get_source_balance(u.id, current_user.id), 2
                ),
            }
            for u in users
        },
        'total': round(balance_service.get_total_balance(current_user.id), 2),
        'mintSource': MINT_SOURCE,
        'maxMint': MAX_MINT_AMOUNT,
    }

    if form.validate_on_submit():
        amount = round(form.amount.data, 2)
        source_id = form.source.data
        recipient = db.session.get(User, form.recipient.data)

        try:
            if source_id == MINT_SOURCE:
                if amount > MAX_MINT_AMOUNT:
                    raise ValueError(f'You can mint at most {MAX_MINT_AMOUNT:.2f} THC at a time.')
                transaction_service.record_mint_send(current_user.id, recipient.id, amount)
                db.session.commit()
                flash(f'Minted and sent {amount:.2f} THC to {recipient.display_name}.', 'success')
            else:
                available = balance_service.get_source_balance(current_user.id, source_id)
                if amount > available:
                    source_user = db.session.get(User, source_id)
                    raise ValueError(
                        f'Insufficient balance from {source_user.display_name}. '
                        f'You have {available:.2f} THC from them.'
                    )
                transaction_service.record_send(current_user.id, recipient.id, amount, source_id=source_id)
                db.session.commit()
                flash(f'Sent {amount:.2f} THC to {recipient.display_name}.', 'success')
            return redirect(url_for('wallet.index'))
        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'error')

    return render_template('wallet/send.html', form=form, summary_data=summary_data)
