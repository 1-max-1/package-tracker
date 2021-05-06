import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
from time import time, strftime, strptime

# These create the browser and set the required options needed for it to function with parcelsapp
from selenium.webdriver import Chrome
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
# These are for waiting for the package data to appear
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

class PackageHandler():
	# The constructor creates the schedulers
	def __init__(self, dbPath, chromeDriverName):
		self.scheduler = BackgroundScheduler()
		# self.scheduler.add_job(self.addOldPackagesToQueue, "interval", seconds=45)
		# self.scheduler.add_job(self.scrapeNextInQueue, "interval", seconds=20)
		# self.scheduler.start()

		self.dbPath = dbPath
		self.con = None

		# # Dont wait for full page load
		# caps = DesiredCapabilities().CHROME
		# caps["pageLoadStrategy"] = "none"
		# # This option needs to be set otherwise the automated browser will be detected by the website
		# opts = Options()
		# opts.add_argument("--disable-blink-features=AutomationControlled")
		# # Startup the browser
		# self.browser = Chrome(chromeDriverName, desired_capabilities=caps, chrome_options=opts)
		# self.browser.get("https://google.com")
		self.browser = None

	# Acts like a destructor
	def __del__(self):
		# self.scheduler.shutdown()
		# self.browser.close()
		pass

	# Gets the top package on the queue - next in line. Proceeds to scrape the data for that package and add it to the db. Package is then removed from the queue and updated
	@createDBConnection
	def scrapeNextInQueue(self):
		# Get the package that is next in line for being scraped
		cur = self.con.cursor()
		cur.row_factory = sqlite3.Row # Dictionary format
		cur.execute("SELECT queue.package_id AS id, packages.trackingNumber AS trackingNumber FROM queue INNER JOIN packages ON queue.package_id = packages.id LIMIT 1")
		package = cur.fetchone()

		if not package:
			return

		# Browse to the page that tracks our package
		self.browser.get("https://parcelsapp.com/en/tracking/" + package["trackingNumber"])
		# Wait until the data has been fetched - a <ul> element will appear on the page
		unorderedList = WebDriverWait(self.browser, 30000).until(EC.presence_of_element_located(("css selector", ".list-unstyled.events")))
		cur.execute("DELETE FROM package_data WHERE package_id = ?", [package["id"]]) # Remove all old data

		for listItem in unorderedList.find_elements_by_tag_name("li"):
			# This div holds 2 child elements containing the date and time of the package stage
			dateTimeDiv = listItem.find_element_by_css_selector("div.event-time")
			# We join the date and time together in 1 string, then pass it to this time parsing function
			parsedTime = strptime(dateTimeDiv.find_element_by_tag_name("strong").text + " " + dateTimeDiv.find_element_by_tag_name("span").text, "%d %b %Y %H:%M")
			# The data is what the package stage is actually about, things like Delivered, In Transit To Local Depot, Arrive at destination country etc.
			data = listItem.find_element_by_css_selector("div.event-content").find_element_by_tag_name("strong").text

			# Once we have all of the info we can insert it into the db
			cur.execute("INSERT INTO package_data (package_id, date, time, data) VALUES (?, ?, ?, ?)", [package["id"], strftime("%a %d %b %Y", parsedTime), strftime("%I:%M %p", parsedTime), data])

		# This package doesn't need to be updated for another 6 hours
		cur.execute("DELETE FROM queue WHERE package_id = ?", [package["id"]])
		cur.execute("UPDATE packages SET last_updated = ? WHERE id = ?", [time(), package["id"]])
		cur.close()
		self.con.commit()

	# Checks if any packages haven't been updated for more than 6 hou`rs. If so, adds them to the queue
	@createDBConnection
	def addOldPackagesToQueue(self):		
		# Create a cursor with results in dictionary format, and get all packages that haven't been
		# updated for 6 hours, and are not already in the queue.
		cur = self.con.cursor()
		cur.row_factory = sqlite3.Row # Dictionary format
		cur.execute("SELECT id FROM packages WHERE (? - last_updated) >= 21600 AND id NOT IN (SELECT package_id FROM queue)", [time()])
		result = cur.fetchall()

		# Loop through each result and add the ID to the queue
		for row in result:
			cur.execute("INSERT INTO queue (package_id) VALUES (?)", [row["id"]])
			self.con.commit()
		cur.close()

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
		cur.execute("INSERT INTO packages (trackingNumber, user_id) VALUES (?, ?)", [trackingNumber, userID])
		self.con.commit()
		cur.close()
		return True

	@createDBConnection
	def getListOfPackages(self, userID):
		# This is pretty self explanatory. We get a cursor, select all packages, close the cursor and return
		cur = self.con.cursor()
		cur.row_factory = sqlite3.Row # Dictionary format
		
		# The result set needs to have the title, but if the title is null we use the tracking number
		cur.execute("SELECT id, COALESCE(title, trackingNumber) AS title FROM packages WHERE user_id = ?", [userID])
		result = cur.fetchall()
		cur.close()
		return result

	@createDBConnection
	def getPackageData(self, packageID, userID):
		cur = self.con.cursor() # Dictionary format cursor
		cur.row_factory = sqlite3.Row

		# Check that the package is associated with this user. If not, return false.
		cur.execute("SELECT packages.id FROM packages INNER JOIN users ON users.id = packages.user_id WHERE users.id = ? AND packages.id = ?", [userID, packageID])
		if not cur.fetchone():
			return False

		# Return all stages in the packages journey with date, time and the description of the event
		# The package title is added to the top of the result. Order by reverse order so data is in date order
		cur.execute("SELECT id, date, time, data FROM package_data WHERE package_id = ? UNION SELECT 0, COALESCE(title, trackingNumber) AS title, NULL, NULL FROM packages WHERE id = ?", [packageID, packageID])
		result = cur.fetchall()
		cur.close()
		return result

	# This function will update the specified package's title after verifying that the user has access to it
	@createDBConnection
	def updatePackageTitle(self, packageID, userID, title):
		# Get the package that matches the passed id and make sure it has the passed user ID
		cur = self.con.cursor()
		cur.execute("SELECT id FROM packages WHERE id = ? AND user_id = ?", [packageID, userID])
		result = cur.fetchone()

		# If there is no result then it means there are no packages with that ID or the package
		# does not belong to the current user. Need to stop them from editing someone else's package.
		if not result:
			cur.close()
			return "0"

		# Assign none to the title if the string is empty - we want to insert NULL into the db not an empty string
		newTitle = title.strip() if len(title.strip()) > 0 else None
		cur.execute("UPDATE packages SET title = ?", [newTitle]) #Update and close connection
		self.con.commit()
		cur.close()

		# We have succeeded - return the new title
		return newTitle