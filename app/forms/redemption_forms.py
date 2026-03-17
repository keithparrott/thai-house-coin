from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired


class RedeemForm(FlaskForm):
    target = SelectField('Redeem From', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Request Redemption')
