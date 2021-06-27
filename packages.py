import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
from time import time, strftime, strptime, gmtime

# These create the browser and set the required options needed for it to function with parcelsapp
from selenium.webdriver import Chrome
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
# These are for waiting for the package data to appear
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

# This will be a decorator. It gets applied to class functions and modifies them so that a new database
# connection is created before the function is called. The connection is then closed. This saves having
# to write a new with-connect-as block every time I just want to get a cursor. Plus, decorators are cool!
def createDBConnection(func):
	def wrapper(self, *args, **kwargs):
		# Make new connection and store it in the instance so it can be accessed by the passed class func
		with sqlite3.connect(self.dbPath) as con:
			self.con = con
			return func(self, *args, **kwargs)
	return wrapper

class PackageHandler():
	# The constructor creates the schedulers
	def __init__(self, dbPath, chromeDriverName, emailHandler):
		self.emailHandler = emailHandler
		self.dbPath = dbPath
		self.con = None

		self.scheduler = BackgroundScheduler()
		self.scheduler.add_job(self.addOldPackagesToQueue, "interval", seconds=15)
		self.scheduler.add_job(self.scrapeNextInQueue, "interval", seconds=60)
		self.scheduler.add_job(self.checkForDeadPackages, "interval", seconds=300)
		self.scheduler.start()

		# Dont wait for full page load
		caps = DesiredCapabilities().CHROME
		caps["pageLoadStrategy"] = "none"
		# This option needs to be set otherwise the automated browser will be detected by the website
		opts = Options()
		opts.add_argument("--disable-blink-features=AutomationControlled")
		opts.add_argument("--headless") # Runs faster - no rendering
		# Startup the browser
		self.browser = Chrome(chromeDriverName, desired_capabilities=caps, chrome_options=opts)
		self.browser.get("https://google.com")
		#self.browser = None

	# Acts like a destructor
	def __del__(self):
		self.scheduler.shutdown()
		self.browser.close()
		#pass

	# Gets the top package on the queue - next in line. Proceeds to scrape the data for that package and add it to the db. Package is then removed from the queue and updated
	# Cant use the decorator here becase the sqlite connection will be on another thread
	def scrapeNextInQueue(self):
		# Get the package that is next in line for being scraped
		# Order by priority so we get new packages first
		con = sqlite3.connect(self.dbPath)
		cur = con.cursor()
		cur.row_factory = sqlite3.Row # Dictionary format
		cur.execute("SELECT queue.package_id AS id, packages.trackingNumber AS trackingNumber FROM queue INNER JOIN packages ON queue.package_id = packages.id ORDER BY queue.priority DESC, packages.id LIMIT 1")
		package = cur.fetchone()

		if not package:
			return

		# Browse to the page that tracks our package
		self.browser.get("https://parcelsapp.com/en/tracking/" + package["trackingNumber"])
		# Wait until the data has been fetched - a <ul> element will appear on the page
		unorderedList = WebDriverWait(self.browser, 30000, ignored_exceptions=(StaleElementReferenceException,)).until(EC.presence_of_element_located(("css selector", ".list-unstyled.events")))
		unorderedListItems = unorderedList.find_elements_by_tag_name("li")

		# Get the number of package rout data points for this package
		cur.execute("SELECT COUNT(*) AS count FROM package_data WHERE package_id = ?", [package["id"]])
		packageDataCount = cur.fetchone()["count"]
		cur.execute("DELETE FROM package_data WHERE package_id = ?", [package["id"]]) # Remove all old data

		for listItem in unorderedListItems:
			# This div holds 2 child elements containing the date and time of the package stage
			dateTimeDiv = listItem.find_element_by_css_selector("div.event-time")

			# We join the date and time together in 1 string, then pass it to this time parsing function
			# If the package number is incorrect or something, then the scraping will return something
			# along the lines of "no package data for <<country>>". If this happens it doesn't return a time,
			# only a date. If there is only a date then this block will catch it.
			try:
				parsedTime = strptime(dateTimeDiv.find_element_by_tag_name("strong").text + " " + dateTimeDiv.find_element_by_tag_name("span").text, "%d %b %Y %H:%M")
			except ValueError:
				parsedTime = strptime(dateTimeDiv.find_element_by_tag_name("strong").text, "%d %b %Y")

			# The data is what the package stage is actually about, things like Delivered, In Transit To Local Depot, Arrive at destination country etc.
			data = listItem.find_element_by_css_selector("div.event-content").find_element_by_tag_name("strong").text

			# Once we have all of the info we can insert it into the db
			cur.execute("INSERT INTO package_data (package_id, date, time, data) VALUES (?, ?, ?, ?)", [package["id"], strftime("%a %d %b %Y", parsedTime), strftime("%I:%M %p", parsedTime), data])

		# This package doesn't need to be updated for another 6 hours
		# Also set the last_new_data field to the current time if the amount of new data is bigger than the amount of old data
		cur.execute("DELETE FROM queue WHERE package_id = ?", [package["id"]])
		cur.execute("UPDATE packages SET last_updated = ?, last_new_data = CASE WHEN ? > 0 THEN ? ELSE (SELECT last_new_data FROM packages WHERE id = ?) END WHERE id = ?", [time(), len(unorderedListItems) - packageDataCount, time(), package["id"], package["id"]])
		cur.close()
		con.commit()
		con.close()

	# Checks if any packages haven't been updated for more than 6 hours. If so, adds them to the queue
	# Cant use the decorator here because the sqlite connection will be on a nother thread
	def addOldPackagesToQueue(self):		
		# Create a cursor with results in dictionary format, and get all packages that haven't been
		# updated for 6 hours, and are not already in the queue.
		con = sqlite3.connect(self.dbPath)
		cur = con.cursor()
		cur.row_factory = sqlite3.Row # Dictionary format
		cur.execute("SELECT id FROM packages WHERE (? - last_updated) >= 21600 AND id NOT IN (SELECT package_id FROM queue)", [time()])
		result = cur.fetchall()

		# Loop through each result and add the ID to the queue
		for row in result:
			cur.execute("INSERT INTO queue (package_id) VALUES (?)", [row["id"]])
			con.commit()
		cur.close()
		con.close()

	# Will find any packages that have not had new data for a long time.
	# Some are deleted, and some prompt a reminder email to the user that owns them.
	def checkForDeadPackages(self):
		con = sqlite3.connect(self.dbPath)
		cur = con.cursor()
		cur.row_factory = sqlite3.Row # Dictionary format

		# This joins users to pacakges, returns the email, title and id for each package that has not had new data for around a month
		cur.execute("SELECT COALESCE(packages.title, packages.trackingNumber) AS title, packages.last_new_data AS last_new_data, packages.id AS id, users.email AS user_email FROM packages INNER JOIN users ON users.id = packages.user_id WHERE (? - packages.last_new_data) >= 2419200 AND packages.email_sent = 0", [time()])
		result = cur.fetchall()

		# Loop through results - we need to either send a reminder email or delete the package
		for row in result:
			# If the difference is greater than a month then this package should be deleted
			if time() - row["last_new_data"] > 2678400:
				cur.execute("DELETE FROM packages WHERE id = ?", [row["id"]])
			# Otherwise it is getting close to deletion, so we send an email
			else:
				self.emailHandler.sendPackageReminderEmail(row["user_email"], row["title"], row["id"])
				cur.execute("UPDATE packages SET email_sent = 1 WHERE id = ?", [row["id"]])
			con.commit()

		cur.close()
		con.close()

	@createDBConnection
	def createNewPackage(self, trackingNumber, userID):
		# First we check if the user is already tracking this package
		cur = self.con.cursor()
		cur.row_factory = sqlite3.Row # Dictionary format
		cur.execute("SELECT id FROM packages WHERE user_id = ? AND trackingNumber = ?", [userID, trackingNumber])
		result = cur.fetchone()
		cur.close()
		if result:
			return False

		# If they aren't tracking the package, then we insert it into the db
		cur = self.con.cursor() # New cursor to avoid conflicts with different operation types
		cur.execute("INSERT INTO packages (trackingNumber, user_id, last_new_data) VALUES (?, ?, ?)", [trackingNumber, userID, time()])
		self.con.commit()
		cur.execute("INSERT INTO queue (package_id, priority) VALUES ((SELECT MAX(id) FROM packages), 1)")
		self.con.commit()
		cur.close()
		return True

	@createDBConnection
	def getListOfPackages(self, userID):
		# This is pretty self explanatory. We get a cursor, select all packages, close the cursor and return
		cur = self.con.cursor()
		cur.row_factory = sqlite3.Row # Dictionary format
		
		# The result set needs to have the title, but if the title is null we use the tracking number
		cur.execute("SELECT id, COALESCE(title, trackingNumber) AS title, last_new_data, ? AS current_time FROM packages WHERE user_id = ?", [time(), userID])
		result = cur.fetchall()
		cur.close()
		return result

	@createDBConnection
	def getPackageData(self, packageID, userID):
		# Make sure user has access
		if self.isPackageAssociatedWithUser(packageID, userID) == False:
			return False

		cur = self.con.cursor() # Dictionary format cursor
		cur.row_factory = sqlite3.Row

		# Return all stages in the packages journey with date, time and the description of the event
		# The package title is added to the top of the result. Order by reverse order so data is in date order
		cur.execute("SELECT id, date, time, data FROM package_data WHERE package_id = ? UNION SELECT 0, COALESCE(title, trackingNumber) AS title, trackingNumber, ROUND(last_updated) FROM packages WHERE id = ?", [packageID, packageID])
		result = cur.fetchall()
		cur.close()

		# We need to parse the seconds then reassign them to the row. However, this cannot be done to the
		# Row object directly, so we need to convert it to a dictionary first.
		result = [dict(row) for row in result]
		result[0]["data"] = strftime("%a %d %b %Y", gmtime(result[0]["data"]))
		return result
	
	# This checks if the specified user id has access to the specified package
	def isPackageAssociatedWithUser(self, packageID, userID):
		cur = self.con.cursor()
		# Check that the package is associated with this user. If not, return false.
		cur.execute("SELECT id FROM packages WHERE user_id = ? AND id = ?", [userID, packageID])
		result = cur.fetchone()
		cur.close()

		if not result:
			return False
		return True

	# This function will update the specified package's title after verifying that the user has access to it
	@createDBConnection
	def updatePackageTitle(self, packageID, userID, title):
		# Make sure they own this package
		if self.isPackageAssociatedWithUser(packageID, userID) == False:
			return "0"

		# Assign none to the title if the string is empty - we want to insert NULL into the db not an empty string
		newTitle = title.strip() if len(title.strip()) > 0 else None
		cur = self.con.cursor()
		cur.execute("UPDATE packages SET title = ? WHERE id = ?", [newTitle, packageID]) #Update and close connection
		self.con.commit()
		
		# If the title was an empty string, then the title for this package should now default back to the
		# tracking number. We need to perform an additional query to get the tracking number.
		if newTitle == None:
			cur.execute("SELECT trackingNumber FROM packages WHERE id = ?", [packageID])
			newTitle = cur.fetchone()[0]
		cur.close()

		# We have succeeded - return the new title
		return newTitle

	@createDBConnection
	def deletePackage(self, packageID, userID):
		# Make sure they own this package
		if self.isPackageAssociatedWithUser(packageID, userID) == False:
			return "0"
		
		# If they are authorised to delete this package then delete it.
		cur = self.con.cursor()
		cur.execute("DELETE FROM queue WHERE package_id = ?", [packageID])
		cur.execute("DELETE FROM package_data WHERE package_id = ?", [packageID])
		cur.execute("DELETE FROM packages WHERE id = ?", [packageID])
		self.con.commit()
		cur.close()
		return "1"

	@createDBConnection
	def renewPackage(self, packageID, userID):
		if self.isPackageAssociatedWithUser(packageID, userID) == False:
			return False

		# If they have access to it, reset the last_new_data to the current time, and reset the email_sent flag
		# This will make the system wait another few weeks before warning the user, and will allow it to resend the email.
		cur = self.con.cursor()
		cur.execute("UPDATE packages SET last_new_data = ?, email_sent = 0 WHERE id = ?", [time(), packageID])
		self.con.commit()
		cur.close()
		return True