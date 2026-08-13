from flask_wtf import FlaskForm
from wtforms import SelectField, FloatField, SubmitField
from wtforms.validators import DataRequired, NumberRange

# Sentinel for "mint new THC" in the source selector. Real user ids are >= 1,
# and -1 stays truthy so DataRequired still behaves.
MINT_SOURCE = -1

# Matches the per-bounty reward ceiling, so no single action can create
# more new supply than a bounty can.
MAX_MINT_AMOUNT = 5.0


class SendForm(FlaskForm):
    recipient = SelectField('Recipient', coerce=int, validators=[DataRequired()])
    source = SelectField('Source', coerce=int, validators=[DataRequired()])
    amount = FloatField('Amount (THC)', validators=[
        DataRequired(), NumberRange(min=0.01, message='Minimum send amount is 0.01 THC.')
    ])
    submit = SubmitField('Send THC')
