from flask import Flask, render_template
app = Flask(__name__)

@app.route('/')
def hello_world():
    return render_template("main_layout_container.html")

@app.route("/login", methods=["GET", "POST"])
def login():
	pass
	# Need to check if the form is post or get then log the user in

if __name__ == "__main__":
	app.run(debug=True)