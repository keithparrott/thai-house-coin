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
    contributions = db.relationship('BountyContribution', backref='bounty', lazy='dynamic',
                                    order_by='BountyContribution.created_at.asc()')

    @property
    def total_reward(self):
        contributed = self.contributions.with_entities(
            db.func.coalesce(db.func.sum(BountyContribution.amount), 0.0)
        ).scalar()
        return self.reward_amount + float(contributed)

    @property
    def contributor_count(self):
        return self.contributions.count()

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


class BountyContribution(db.Model):
    __tablename__ = 'bounty_contributions'
    __table_args__ = (db.UniqueConstraint('bounty_id', 'contributor_id', name='uq_bounty_contributor'),)

    id = db.Column(db.Integer, primary_key=True)
    bounty_id = db.Column(db.Integer, db.ForeignKey('bounties.id'), nullable=False)
    contributor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    contributor = db.relationship('User', backref='bounty_contributions')

    def __repr__(self):
        return f'<BountyContribution {self.id} bounty={self.bounty_id} contributor={self.contributor_id}>'
