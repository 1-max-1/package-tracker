from os import environ
from functools import wraps
#from socket import gethostname, gethostbyname

from flask import Flask, render_template, session, flash, redirect, url_for, request
import forms

from auth import Authenticator
from packages import PackageHandler
from emails import EmailHandler

app = Flask(__name__)
# A key is needed for some operations. In particular, for WTForms to protect against CSRF
app.secret_key = environ["FLASK_KEY"]

emailHandler = EmailHandler()
authenticator = Authenticator("database/database.db", emailHandler)
packageHandler = PackageHandler("database/database.db", environ["CHROMEDRIVER_PATH"], emailHandler)

@app.route('/')
def homePage():
	return render_template("homePage.html")

# This function can be applied as a decorator to any other function. Basically, it modifies the passed
# function by first checking if the user is logged in. If so, it runs the passes function.
# See here: https://realpython.com/primer-on-python-decorators/
def login_required(func):
	@wraps(func) # This decorator copies over function attributes like __name__, docstring etc. required by flask for some reason
	def wrapper(*args, **kwargs):
		if "userID" in session and session["userID"] > 0:
			return func(*args, **kwargs)
		else:
			flash("You need to log in to do that!", "danger")
			return redirect(url_for("login"))

	# wrapper is the new function that will be put in place of any function that uses this decorator
	return wrapper

# Add an optional URL param - this will tell us that we need to redirect somewhere else after login
@app.route("/login", methods=["GET", "POST"])
@app.route("/login/<int:redirectToRenew>/<int:packageID>", methods=["GET", "POST"])
def login(redirectToRenew=0, packageID=0):
	# The form instance will be automatically filled with data if there is data
	form = forms.LoginForm()
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

			# If the user came here from the renew package page, we send them back there as they have now logged in
			print(redirectToRenew)
			print(packageID)
			if redirectToRenew == 1:
				return redirect(url_for("renewPackage", packageID=packageID))
			# If they just logged in then we send them to the main page of their list
			else:
				return redirect(url_for("packageList"))
		else:
			flash("Incorrect username or password. Please try again.", "danger")
			# Need to redirect them back to this page so that if they reload it,
			# the form wont be cached and wont resubmit. Then they wont have to click that popup every time
			return redirect(url_for("login", redirectToRenew=redirectToRenew, packageID=packageID))
	
	return render_template("login.html", form=form)

# When they log out we remove all session data
@app.route("/logout")
@login_required
def logout():
	session["userID"] = 0
	session.clear()
	flash("You have been logged out!", "primary")
	return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
	# The form instance will be automatically filled with data if there is data
	form = forms.RegisterForm()

	# Validate the form and check that it was submitted (POST request). We dont want to make a new
	# user for a get request (not submitted).
	if form.validate_on_submit():
		if authenticator.createNewPendingUser(form.email.data, form.password.data):
			# If the user does not already exist then it was a success and we can redirect them
			# to the next page, which will tell them that they need to verify their email address
			return render_template("verifyYourEmail.html", email=form.email.data)
		else:
			flash("That user already exists!", "danger")
			# Need to redirect them back to this page so that if they reload it,
			# the form wont be cached and wont resubmit. Then they wont have to click that popup every time
			return redirect(url_for("register"))

	# If the request was not submitted (or the user already exists) then we can just render the form normally.
	return render_template("register.html", form=form)

@app.route("/packageList", methods=["GET", "POST"])
@login_required
def packageList():
	form = forms.AddPackageForm()
	# If the form was submitted with a POST request then the user is adding a package
	if form.validate_on_submit():
		if packageHandler.createNewPackage(form.trackingCode.data, session["userID"]):
			flash("Package added successfully!", "success")
			form.trackingCode.data = ""
		else:
			flash("You have already added that package!", "warning")
		# Need to redirect them back to this page so that if they reload it,
		# the form wont be cached and wont resubmit. Then they wont have to click that popup every time
		return redirect(url_for("packageList"))

	# If the request is just a get request, then we can just render the list of packages
	packageListDict = packageHandler.getListOfPackages(session["userID"])
	return render_template("packageList.html", form=form, packageList=packageListDict)

@app.route("/packageDetails/<int:packageID>")
@login_required
def viewPackage(packageID):
	packageData = packageHandler.getPackageData(packageID, session["userID"])

	# Make sure that the supplied package id is in the list of packages that this user is tracking
	# thr getPackageData function does this automatically for us
	if not packageData:
		flash("You are not tracking that package. Add it!", "primary")
		return redirect(url_for("packageList"))

	# Pass the data to the template where it will be iterated over and rendered
	return render_template("packageData.html", packageData=packageData)

@app.route("/confirmUserEmail/<string:token>")
def confirmUserEmail(token):
	# Returns false if failed, otherwise returns the ID of the new user
	userID = authenticator.createNewUser(token)
	if not userID:
		flash("This link is either invalid or has expired. Please re-register.", "warning")
		return redirect(url_for("register"))
	# If it was a success then we can log them in
	else:
		# We can store the user ID as we will need it later for querying all of the packages for the user.
		# We then redirect them to the list of their packages
		session["userID"] = userID
		flash("Verification successful! You are now logged in.", "success")
		return redirect(url_for("packageList"))

# Will resend the email for a password reset or email verification.
# The resend type specifies whether it is for a pending user or password reset.
@app.route("/resendEmail/<int:resendType>/<string:email>")
def resendEmail(resendType, email):
	# Email verification
	if resendType == 1:
		if not authenticator.sendEmailVerificationEmail(email):
			flash("Something went wrong and we couldn't resend the email. You may need to re-register.", "danger")
		return render_template("verifyYourEmail.html", email=email)
	# Password reset
	elif resendType == 2:
		if not authenticator.sendPasswordResetEmail(email):
			flash("Something went wrong and we couldn't resend the email. You may need to redo the passwod reset.", "danger")
		return render_template("forgotPasswordStep2.html", email=email)

@app.route("/forgotPassword", methods=["GET", "POST"])
def forgotPassword():
	# As the form inherits from flask form, the constructor will use flasks request variable to
	# automatically fill the form with data. If it is just a get request then nothing will happen
	form = forms.ForgotPasswordForm()

	# If the form is a post request (and validated) then the user is sending it to reset their password
	if form.validate_on_submit():
		if authenticator.createPasswordResetRequest(form.email.data):
			# If it was successfull then we can show them what to do next
			return render_template("forgotPasswordStep2.html", email=form.email.data)
		else:
			# If it wasn't successull, then there is one reason: the passed email does not exist
			flash("There is no account with that email!", "danger")
			return redirect(url_for("forgotPassword")) # Redirect so we can go to the GET side of page

	# If it was just a get request or a failed post request then we just render the form with it's errors
	return render_template("forgotPassword.html", form=form)

@app.route("/resetPassword/<string:token>", methods=["GET", "POST"])
def resetPassword(token):
	# If the token is still valid then this will return user ID. Otherwise it will return false
	userID = authenticator.verifyPasswordResetToken(token)
	# We cant do anything if the token isnt valid - redirect back to forgot pasword page so they can redo it
	if not userID:
		flash("That link is either invalid or expired. You will need to redo the reset proccess.", "danger")
		return redirect(url_for("forgotPassword"))

	# Now that we have validated the token, we create a form. If the request is a POST then the inherited
	# constructor will automatically fill out the form with the correct data.
	form = forms.ResetPasswordForm()
	# We do the logic on a POST request because that means the user has filled out the form and submitted it
	if form.validate_on_submit():
		authenticator.updatePassword(userID, form.password.data)
		return redirect(url_for("login"))

	return render_template("enterNewPassword.html", form=form)

# This endpoint is for handling ajax requests from the UI.
# the ajax request is initiated when the user wants to change the title for one of their packages.
@app.route("/updatePackageTitle", methods=["POST"])
def updatePackageTitle():
	# If they dont have a user ID in their session then they are not logged in, which means they are
	# manipulating the URL. HAXXXXX block them from it.
	if "userID" not in session or "packageID" not in request.form:
		return "0"

	# Update the package with the data. We just pass on what the updatePackage function returned.
	# it will send back "0" if it failed or the new package title on a success.
	return packageHandler.updatePackageTitle(request.form["packageID"], session["userID"], request.form["newTitle"])

# This endpoint is for handling ajax requests from the UI.
# the ajax request is initiated when the user wants to delete one of their packages.
@app.route("/deletePackage", methods=["POST"])
def deletePackage():
	# If they dont have a user ID in their session then they are not logged in, which means they are
	# manipulating the URL. HAXXXXX block them from it.
	if "userID" not in session or "packageID" not in request.form:
		return "0"

	# Request for the package to be deleted. The function will first check if the user is authorised.
	# Returns either "0" or "1" for success and failiure. We can just pass on this value.
	return packageHandler.deletePackage(request.form["packageID"], session["userID"])

# This route handles requests from users wanting to renew their packages
@app.route("/renewPackage/<int:packageID>")
def renewPackage(packageID):
	# If they aren't logged in then we redirect them to the login page.
	# Specify the target so when they log in they get redirected back here
	if "userID" not in session:
		return redirect(url_for("login", redirectToRenew=1, packageID=packageID))

	if packageHandler.renewPackage(packageID, session["userID"]) == True:
		flash("Package renewed!", "success")
	else:
		flash("You cannot renew that package as you do not own it!", "danger")
	return redirect(url_for("packageList"))

if __name__ == "__main__":
	#TODO: Make sure to change this to non-debg on production
	#gethostbyname(gethostname())
	app.run(debug=True, use_reloader=False, host="0.0.0.0", port=5000)