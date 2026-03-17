from flask_wtf import FlaskForm
from wtforms import SelectField, FloatField, SubmitField
from wtforms.validators import DataRequired, NumberRange


class SendForm(FlaskForm):
    recipient = SelectField('Recipient', coerce=int, validators=[DataRequired()])
    amount = FloatField('Amount (THC)', validators=[
        DataRequired(), NumberRange(min=0.01, message='Minimum send amount is 0.01 THC.')
    ])
    submit = SubmitField('Send THC')
