import sqlite3
from passlib.hash import sha256_crypt

class Authenticator():
	# Validates the login details - return true if they are correct
	def verifyLogin(self, email, passwordAttempt : str):
		with sqlite3.connect("database/database.db") as con:
			result = self.userExists(email, con)
			# This user does not exist
			if not result:
				return False

			# If the username is there, then we verify the password for it
			if sha256_crypt.verify(passwordAttempt, result["password"]):
				return result["id"]    # The ID is needed for other things - pass it back
			else:
				return False

	def createNewUser(self, email, password):
		with sqlite3.connect("database/database.db") as con:
			if self.userExists(email, con):
				return False

			# If the user does not exist then we are good to go for creating the new user
			cur = con.cursor()
			cur.execute("INSERT INTO users (email, password) VALUES (?, ?)", [email, sha256_crypt.hash(password)])
			con.commit()
			cur.close()

			# Now return the ID of the inserted user so we can log them in
			return self.userExists(email, con)["id"]

	# Checks if the user exists. If not, returns false. Otherwise returns user ID and password
	def userExists(self, email, dbConnection):
		# First we can get out the user details from the database
		cur = dbConnection.cursor()
		cur.row_factory = sqlite3.Row # Makes result returned as dictionary
		cur.execute("SELECT id, password FROM users WHERE email = ?", [email])
		result = cur.fetchone()
		cur.close()

		# (if not result) will be true if there are no records with the passed 'email
		if not result:
			return False
		return result