from datetime import datetime, timezone

from app.extensions import db


class Bounty(db.Model):
    __tablename__ = 'bounties'

    id = db.Column(db.Integer, primary_key=True)
    poster_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, default='')
    reward_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(32), nullable=False, default='open')  # open, pending, completed, cancelled
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)

    poster = db.relationship('User', backref='bounties_posted')
    claims = db.relationship('BountyClaim', backref='bounty', lazy='dynamic',
                             order_by='BountyClaim.submitted_at.desc()')

    def __repr__(self):
        return f'<Bounty {self.id} "{self.title}">'


class BountyClaim(db.Model):
    __tablename__ = 'bounty_claims'

    id = db.Column(db.Integer, primary_key=True)
    bounty_id = db.Column(db.Integer, db.ForeignKey('bounties.id'), nullable=False)
    claimant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, default='')
    status = db.Column(db.String(32), nullable=False, default='pending')  # pending, approved, rejected
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    claimant = db.relationship('User', backref='bounty_claims')

    def __repr__(self):
        return f'<BountyClaim {self.id} bounty={self.bounty_id}>'
