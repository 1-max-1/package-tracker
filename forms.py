from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email, EqualTo, Length

# Represents (from a object point of view) the form that the user sees when they login.
# Makes it easy to access the field data
class LoginForm(FlaskForm):
	email = StringField("Email", validators=[DataRequired(), Email(), Length(min=3, max=254)])
	password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])

# Same thing but for registration
class RegisterForm(FlaskForm):
	email = StringField("Email", validators=[DataRequired(), Email(), Length(min=3, max=254)])
	password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
	passwordConfirmation = PasswordField("Confirm password", validators=[DataRequired(), Length(min=8, max=128), EqualTo("password", "Passwords do not match")])

class AddPackageForm(FlaskForm):
	trackingCode = StringField("Tracking number", validators=[DataRequired()])

class ForgotPasswordForm(FlaskForm):
	email = StringField("Email", validators=[DataRequired(), Email(), Length(min=3, max=254)])

class ResetPasswordForm(FlaskForm):
	password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
	passwordConfirmation = PasswordField("Confirm password", validators=[DataRequired(), Length(min=8, max=128), EqualTo("password", "Passwords do not match")])