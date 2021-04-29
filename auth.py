import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
from passlib.hash import sha256_crypt
from uuid import uuid4
from time import time

# This will be a decorator. It gets applied to class functions and modifies them so that a new database
# connection is created before the function is called. THe connection is then closed. This saves having
# to write a new with-connect-as block every time I just want to get a cursor. Plus, decorators are cool!
def createDBConnection(func):
	def wrapper(self, *args, **kwargs):
		# If we have an existing connection then we dont want to close it or open a new one
		if self.con != None:
			return func(self, *args, **kwargs)

		# Make new connection and store it in the instance so it can be accessed by the passed class func
		self.con = sqlite3.connect(self.dbPath)
		result = func(self, *args, **kwargs)
		self.con.close()
		self.con = None # Close and reset to none so we know that we no longer have an existing connection
		return result
	return wrapper

class Authenticator():
	def __init__(self, dbPath, emailHandler):
		self.dbPath = dbPath
		self.con = None
		self.emailHandler = emailHandler

		# This will schedule a job that purges any accounts that have not been verified within half an hour
		self.scheduler = BackgroundScheduler()
		self.scheduler.add_job(self.removeExpiredPendingUsers, "interval", seconds=120)
		self.scheduler.start()

	# Free scheduler resources when all references to the authenticator have been deleted
	def __del__(self):
		self.scheduler.shutdown()

	# Validates the login details - return true if they are correct
	@createDBConnection
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
	def createNewUser(self, verificationToken):
		cur = self.con.cursor()
		cur.row_factory = sqlite3.Row

		# First we want to check if this verification token still exists in the db
		cur.execute("SELECT email FROM pending_users WHERE verification_token = ?", [verificationToken])
		result = cur.fetchone()
		if not result: # Token broken, return false. The flask endpoint logic will handle it (in main.py)
			cur.close()
			return False

		# This function will be called when the user verifies their email address. Duplicate users will
		# have already been handled, so all we need to do is move the pending user record to the
		# confirmed users table.
		cur.execute("INSERT INTO users (email, password) SELECT email, password FROM pending_users WHERE verification_token = ?", [verificationToken])
		cur.execute("DELETE FROM pending_users WHERE verification_token = ?", [verificationToken])
		self.con.commit()
		cur.close()

		# Now return the ID of the inserted user so we can log them in
		return self.userExists(result["email"])["id"]

	# Checks if the user exists. If not, returns false. Otherwise returns user ID and password
	def userExists(self, email):
		# First we can get out the user details from the database
		cur = self.con.cursor()
		cur.row_factory = sqlite3.Row # Makes result returned as dictionary
		cur.execute("SELECT id, password FROM users WHERE email = ?", [email])
		result = cur.fetchone()
		cur.close()

		# (if not result) will be true if there are no records with the passed email
		if not result:
			return False
		return result

	@createDBConnection
	def createNewPendingUser(self, email, password):
		if self.userExists(email):
			return False

		# If the user doesn't already exist, then we can generate a new confirmation token and insert
		# it with the registration details into the database.
		cur = self.con.cursor()
		# If there is already a pending user with this email, then the person has gone back,
		# changed their password and resubmitted their registration form. It will be the same person
		# because obviously email address wont be assigned to more than one person. This means we can delete
		# their previous request as it is no longer needed since they changed their details.
		cur.execute("DELETE FROM pending_users WHERE email = ?", [email])
		cur.execute("INSERT INTO pending_users (email, password, verification_token, time_created) VALUES (?, ?, ?, ?)", [email, sha256_crypt.hash(password), uuid4().hex, time()])
		self.con.commit()

		# Return the ID of the newly created pending user
		# cur.execute("SELECT id FROM pending_users WHERE email = ?", [email])
		# result = cur.fetchone()
		cur.close()
		self.sendEmailVerificationEmail(email)
		return True

	# Retrieves verification token associated with pending user email and passes it to email handler
	@createDBConnection
	def sendEmailVerificationEmail(self, email):
		cur = self.con.cursor()
		cur.row_factory = sqlite3.Row
		cur.execute("SELECT verification_token FROM pending_users WHERE email = ?", [email])
		result = cur.fetchone()
		cur.close()

		# Someones messing around with the URL - not providing a valid email address
		if not result:
			return False

		# SEND THE THING
		self.emailHandler.sendVerificationEmail(email, result["verification_token"])
		return True

	# Purges any accounts that have not been verified within half an hour
	@createDBConnection
	def removeExpiredPendingUsers(self):
		print("Purging old tokens")
		print(time())

		cur = self.con.cursor()
		cur.execute("DELETE FROM pending_users WHERE ? - time_created > 1800", [time()])
		self.con.commit()
		cur.close()