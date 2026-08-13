from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Optional


class EditProfileForm(FlaskForm):
    display_name = StringField('Display Name', validators=[DataRequired(), Length(min=1, max=128)])
    email = StringField('Email', validators=[
        Optional(), Email(message='Enter a valid email address.'), Length(max=256)
    ])
    submit = SubmitField('Save Changes')
