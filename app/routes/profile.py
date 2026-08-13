from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models.user import User
from app.models.transaction import Transaction
from app.forms.profile_forms import EditProfileForm
from app.services import balance_service, user_service

profile_bp = Blueprint('profile', __name__, url_prefix='/user')


@profile_bp.route('/<int:user_id>')
@login_required
def view(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('leaderboard.index'))

    stats = user_service.get_profile_stats(user.id)
    is_self = user.id == current_user.id

    # Where the viewer stands with this person, in both directions.
    relationship = None
    if not is_self:
        relationship = {
            'you_owe_them': balance_service.get_source_balance(user.id, current_user.id),
            'they_owe_you': balance_service.get_source_balance(current_user.id, user.id),
        }

    recent_txns = Transaction.query.filter(
        db.or_(
            Transaction.from_user_id == user.id,
            Transaction.to_user_id == user.id
        )
    ).order_by(Transaction.created_at.desc()).limit(10).all()

    return render_template('profile/view.html',
                           user=user,
                           stats=stats,
                           is_self=is_self,
                           relationship=relationship,
                           recent_txns=recent_txns)


@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    form = EditProfileForm(obj=current_user)
    if form.validate_on_submit():
        try:
            user_service.update_profile(
                current_user,
                display_name=form.display_name.data,
                email=form.email.data
            )
            db.session.commit()
            flash('Profile updated.', 'success')
            return redirect(url_for('profile.view', user_id=current_user.id))
        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'error')
    return render_template('profile/edit.html', form=form)
