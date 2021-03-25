from os import environ
from flask import Flask, render_template
from forms import LoginForm

app = Flask(__name__)
# A key is needed for some operations. In particular, for wt forms to protect against CSRF
app.secret_key = environ["FLASK_KEY"]

@app.route('/')
def hello_world():
	return render_template("main_layout_container.html")

@app.route("/login", methods=["GET", "POST"])
def login():
	# The instance will be automatically filled with data if there is data
	form = LoginForm()
	# Validate the form and check that it was submitted with a POST request
	if form.validate_on_submit():
		print(form.email.data)
		print(form.password.data)
	
	return render_template("login.html", form=form)

if __name__ == "__main__":
	app.run(debug=True)