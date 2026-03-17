from datetime import datetime, timezone

from app.extensions import db


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(32), nullable=False)  # send, burn, bounty_payout
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    memo = db.Column(db.String(256), default='')
    is_invalidated = db.Column(db.Boolean, default=False, nullable=False)
    invalidated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    invalidated_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    from_user = db.relationship('User', foreign_keys=[from_user_id], backref='transactions_from')
    to_user = db.relationship('User', foreign_keys=[to_user_id], backref='transactions_to')
    invalidated_by_user = db.relationship('User', foreign_keys=[invalidated_by])

    def __repr__(self):
        return f'<Transaction {self.id} {self.type} {self.amount}>'
