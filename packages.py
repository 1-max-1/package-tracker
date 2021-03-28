import sqlite3

class PackageHandler():
	def createNewPackage(self, trackingNumber, userID):
		with sqlite3.connect("database/database.db") as con:
			# First we check if the user is already tracking this package
			cur = con.cursor()
			cur.row_factory = sqlite3.Row # Dictionary format
			cur.execute("SELECT id FROM packages WHERE userID = ? AND trackingNumber = ?", [userID, trackingNumber])
			result = cur.fetchone()
			cur.close()
			if result:
				return False

			# If they aren't tracking the package, then we insert it into the db
			cur = con.cursor()
			cur.execute("INSERT INTO packages (trackingNumber, userID) VALUES (?, ?)", [trackingNumber, userID])
			con.commit()
			cur.close()
			return True

	def getListOfPackages(self, userID):
		with sqlite3.connect("database/database.db") as con:
			# This is pretty self explanatory. We get a cursor, select all packages, close the cursor and return
			cur = con.cursor()
			cur.row_factory = sqlite3.Row # Dictionary format
			
			cur.execute("SELECT * FROM packages WHERE userID = ?", [userID])
			result = cur.fetchall()
			cur.close()
			return result