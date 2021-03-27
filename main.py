from os import environ
from flask import Flask, render_template, session, flash, redirect, url_for
from forms import LoginForm, RegisterForm
from auth import Authenticator

app = Flask(__name__)
# A key is needed for some operations. In particular, for wt forms to protect against CSRF
app.secret_key = environ["FLASK_KEY"]
authenticator = Authenticator()

@app.route('/')
def hello_world():
	#TODO: change this method to a home page renderer
	return render_template("main_layout_container.html")

# This function can be applied as a decorator to any other function. Basically, it modifies the passed
# function by first checking if the user is logged in. If so, it runs the passes function.
# See here: https://realpython.com/primer-on-python-decorators/
def login_required(func):
	def wrapper(*args, **kwargs):
		if "userID" in session and session["userID"] > 0:
			func(*args, **kwargs)
		else:
			flash("You need to log in to do that!", "danger")
			return redirect(url_for("login"))

	# wrapper is the new function that will be put in place of any function that uses this decorator
	return wrapper

@app.route("/login", methods=["GET", "POST"])
def login():
	# The form instance will be automatically filled with data if there is data
	form = LoginForm()
	# Validate the form and check that it was submitted with a POST request
	if form.validate_on_submit():

		# Returns valid user ID if successfull. Since user ID's start from 1, the if statment will
		# always evaluate to true if a user ID is returned
		userID = authenticator.verifyLogin(form.email.data, form.password.data)
		if userID:
			# If the login was successfull then we can store the user ID as we will need it later for
			# querying all of the packages for the user. We redirect them to the list of their packages
			session["userID"] = userID
			flash("Login successful!", "success")
			return redirect(url_for("packageList"))
		else:
			flash("Incorrect username or password. Please try again.", "danger")
	
	return render_template("login.html", form=form)

# When they log out we remove all session data
@app.route("/logout")
def logout():
	session["userID"] = 0
	session.clear()
	flash("You have been logged out!", "success")
	return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
	# The form instance will be automatically filled with data if there is data
	form = LoginForm()
	# Validate the form and check that it was submitted (POST request). We dont want to make a new
	# user for a get request (not submitted).
	if form.validate_on_submit():

		userID = authenticator.createNewUser(form.email.data, form.password.data)
		if userID:
			# If the registration was successfull then we can log them in. Store the user ID as we will
			# need it later for querying all of the packages for the user.
			session["userID"] = userID
			flash("Login successful!", "success")
			return redirect(url_for("packageList"))
		else:
			flash("That user already exists!", "danger")

	# If the request was not submitted (or the user already exists) then we can just render the form normally.
	return render_template("register.html", form=form)

@login_required
@app.route("/packageList")
def packageList():
	return render_template("main_layout_container.html")

if __name__ == "__main__":
	app.run(debug=True)