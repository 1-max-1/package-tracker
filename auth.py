import sqlite3
from passlib.hash import sha256_crypt

# This will be a decorator. It gets applied to class functions and modifies them so that a new database
# connection is created before the function is called. THe connection is then closed. This saves having
# to write a new with-connect-as block every time I just want to get a cursor. Plus, decorators are cool!
def createDBConnection(func):
	def wrapper(self, *args, **kwargs):
		# Make new connection and store it in the instance so it can be accessed by the passed class func
		with sqlite3.connect(self.dbPath) as con:
			self.con = con
			return func(self, *args, **kwargs)
	return wrapper

class Authenticator():
	def __init__(self, dbPath):
		self.dbPath = dbPath
		self.con = None	

	# Validates the login details - return true if they are correct
	def verifyLogin(self, email, passwordAttempt: str):
		result = self.userExists(email)
		# This user does not exist
		if not result:
			return False

		# If the username is there, then we verify the password for it
		if sha256_crypt.verify(passwordAttempt, result["password"]):
			return result["id"]    # The ID is needed for other things - pass it back
		else:
			return False

	@createDBConnection
	def createNewUser(self, email, password):
		if self.userExists(email):
			return False

		# If the user does not exist then we are good to go for creating the new user
		cur = self.con.cursor()
		cur.execute("INSERT INTO users (email, password) VALUES (?, ?)", [email, sha256_crypt.hash(password)])
		self.con.commit()
		cur.close()

		# Now return the ID of the inserted user so we can log them in
		return self.userExists(email)["id"]

	# Checks if the user exists. If not, returns false. Otherwise returns user ID and password
	@createDBConnection
	def userExists(self, email):
		# First we can get out the user details from the database
		cur = self.con.cursor()
		cur.row_factory = sqlite3.Row # Makes result returned as dictionary
		cur.execute("SELECT id, password FROM users WHERE email = ?", [email])
		result = cur.fetchone()
		cur.close()

		# (if not result) will be true if there are no records with the passed 'email
		if not result:
			return False
		return result