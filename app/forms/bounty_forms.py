from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange


class CreateBountyForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=1, max=256)])
    description = TextAreaField('Description')
    reward_amount = FloatField('Reward (THC)', validators=[
        DataRequired(), NumberRange(min=0.01, max=5.0, message='Reward must be between 0.01 and 5.0 THC.')
    ])
    submit = SubmitField('Post Bounty')


class SubmitClaimForm(FlaskForm):
    message = TextAreaField('Proof / Message', validators=[DataRequired(), Length(min=1, max=1000)])
    submit = SubmitField('Submit Claim')
