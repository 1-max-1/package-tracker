import sqlite3
from passlib.hash import sha256_crypt

class Authenticator():
	# Validates the login details - return true if they are correct
	def verifyLogin(self, email, passwordAttempt):
		with sqlite3.connect("database/database.db") as con:
			# First we can get out the user details from the database
			cur = con.cursor()
			cur.row_factory = sqlite3.Row # Makes result returned as dictionary
			cur.execute("SELECT id, password FROM users WHERE email = ?", [email])
			result = cur.fetchone()
			cur.close()

			# If not result will be true if there are no records with the passed username
			if not result:
				return False

			# If the username is there, then we verify the password for it
			if sha256_crypt.verify(passwordAttempt, result["password"]):
				return result["id"]    # The ID is needed for other things - pass it back
			else:
				return False