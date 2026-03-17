from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models.bounty import Bounty, BountyClaim
from app.forms.bounty_forms import CreateBountyForm, SubmitClaimForm
from app.services import bounty_service

bounty_bp = Blueprint('bounty', __name__, url_prefix='/bounty')


@bounty_bp.route('/')
@login_required
def board():
    bounties = Bounty.query.order_by(
        db.case((Bounty.status == 'open', 0), else_=1),
        Bounty.created_at.desc()
    ).all()
    return render_template('bounty/board.html', bounties=bounties)


@bounty_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = CreateBountyForm()
    if form.validate_on_submit():
        try:
            bounty = bounty_service.create_bounty(
                poster_id=current_user.id,
                title=form.title.data,
                description=form.description.data,
                reward_amount=round(form.reward_amount.data, 2)
            )
            db.session.commit()
            flash('Bounty posted!', 'success')
            return redirect(url_for('bounty.detail', bounty_id=bounty.id))
        except ValueError as e:
            flash(str(e), 'error')
    return render_template('bounty/create.html', form=form)


@bounty_bp.route('/<int:bounty_id>')
@login_required
def detail(bounty_id):
    bounty = db.session.get(Bounty, bounty_id)
    if not bounty:
        flash('Bounty not found.', 'error')
        return redirect(url_for('bounty.board'))
    claim_form = SubmitClaimForm()
    return render_template('bounty/detail.html', bounty=bounty, claim_form=claim_form)


@bounty_bp.route('/<int:bounty_id>/claim', methods=['POST'])
@login_required
def submit_claim(bounty_id):
    form = SubmitClaimForm()
    if form.validate_on_submit():
        try:
            bounty_service.submit_claim(
                bounty_id=bounty_id,
                claimant_id=current_user.id,
                message=form.message.data
            )
            db.session.commit()
            flash('Claim submitted!', 'success')
        except ValueError as e:
            flash(str(e), 'error')
    return redirect(url_for('bounty.detail', bounty_id=bounty_id))


@bounty_bp.route('/claim/<int:claim_id>/approve', methods=['POST'])
@login_required
def approve_claim(claim_id):
    try:
        claim = bounty_service.approve_claim(claim_id, current_user.id)
        db.session.commit()
        flash('Claim approved! THC minted.', 'success')
        return redirect(url_for('bounty.detail', bounty_id=claim.bounty_id))
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('bounty.board'))


@bounty_bp.route('/claim/<int:claim_id>/reject', methods=['POST'])
@login_required
def reject_claim(claim_id):
    try:
        claim = bounty_service.reject_claim(claim_id, current_user.id)
        db.session.commit()
        flash('Claim rejected.', 'info')
        return redirect(url_for('bounty.detail', bounty_id=claim.bounty_id))
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('bounty.board'))


@bounty_bp.route('/<int:bounty_id>/cancel', methods=['POST'])
@login_required
def cancel(bounty_id):
    try:
        bounty_service.cancel_bounty(bounty_id, current_user.id)
        db.session.commit()
        flash('Bounty cancelled.', 'info')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(url_for('bounty.board'))
