from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length


class CreateUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=64)])
    display_name = StringField('Display Name', validators=[DataRequired(), Length(min=1, max=128)])
    password = PasswordField('Temporary Password', validators=[DataRequired(), Length(min=6)])
    is_admin = BooleanField('Admin?')
    submit = SubmitField('Create User')


class ResetPasswordForm(FlaskForm):
    new_password = PasswordField('New Temporary Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Reset Password')
