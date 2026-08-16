from datetime import datetime, timezone

from app.extensions import db


class AdminAction(db.Model):
    """Audit trail of every privileged action.

    Detail strings must never quote user-written content: an admin removing an
    offensive bounty or display name would otherwise republish it here.
    """
    __tablename__ = 'admin_actions'

    id = db.Column(db.Integer, primary_key=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(64), nullable=False)
    target_type = db.Column(db.String(32), nullable=True)   # user, bounty, claim, transaction
    target_id = db.Column(db.Integer, nullable=True)
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    detail = db.Column(db.String(256), default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    admin_user = db.relationship('User', foreign_keys=[admin_user_id])
    target_user = db.relationship('User', foreign_keys=[target_user_id])

    def __repr__(self):
        return f'<AdminAction {self.id} {self.action}>'
