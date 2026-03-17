from datetime import datetime, timezone

from app.extensions import db


class Redemption(db.Model):
    __tablename__ = 'redemptions'

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=1.0)
    status = db.Column(db.String(32), nullable=False, default='pending')  # pending, accepted, declined, cancelled
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime, nullable=True)

    requester = db.relationship('User', foreign_keys=[requester_id], backref='redemptions_requested')
    target = db.relationship('User', foreign_keys=[target_id], backref='redemptions_targeted')

    def __repr__(self):
        return f'<Redemption {self.id} {self.requester_id}->{self.target_id}>'
