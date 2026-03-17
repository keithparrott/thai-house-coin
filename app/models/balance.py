from app.extensions import db


class Balance(db.Model):
    __tablename__ = 'balances'

    holder_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    source_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    amount = db.Column(db.Float, nullable=False, default=0.0)

    holder = db.relationship('User', foreign_keys=[holder_user_id], backref='balances_held')
    source = db.relationship('User', foreign_keys=[source_user_id], backref='balances_sourced')

    def __repr__(self):
        return f'<Balance holder={self.holder_user_id} source={self.source_user_id} amount={self.amount}>'
