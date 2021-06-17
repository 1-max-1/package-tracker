from re import search
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

# Represents (from a object point of view) the form that the user sees when they login.
# Makes it easy to access the field data
class LoginForm(FlaskForm):
	email = StringField("Email", validators=[DataRequired(), Email(), Length(min=3, max=254)], render_kw={"style": "margin: auto; width: 100%;"})
	password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)], render_kw={"style": "margin: auto; width: 100%;"})

# Same thing but for registration
class RegisterForm(FlaskForm):
	email = StringField("Email", validators=[DataRequired(), Email(), Length(min=3, max=254)], render_kw={"style": "margin: auto; width: 100%;"})
	password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)], render_kw={"style": "margin: auto; width: 100%;"})
	passwordConfirmation = PasswordField("Confirm password", validators=[DataRequired(), Length(min=8, max=128), EqualTo("password", "Passwords do not match")], render_kw={"style": "margin: auto; width: 100%;"})

	# Called automatically by WTForms when validating the 'password' field
	def validate_password(self, field):
		if search(".*[A-Z].*", field.data) is None:
			raise ValidationError("Password must contain at least one uppercase character")
		if search(".*[0-9].*", field.data) is None:
			raise ValidationError("Password must contain at least one number")

class AddPackageForm(FlaskForm):
	trackingCode = StringField("Tracking number", validators=[DataRequired()])
	classes = {"trackingCode": "d-inline-block"}

class ForgotPasswordForm(FlaskForm):
	email = StringField("Email", validators=[DataRequired(), Email(), Length(min=3, max=254)], render_kw={"style": "margin: auto; width: 100%;"})

class ResetPasswordForm(FlaskForm):
	password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)], render_kw={"style": "margin: auto; width: 100%;"})
	passwordConfirmation = PasswordField("Confirm password", validators=[DataRequired(), Length(min=8, max=128), EqualTo("password", "Passwords do not match")], render_kw={"style": "margin: auto; width: 100%;"})