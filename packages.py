import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
from time import time

from requests import get as httpGetRequest
from bs4 import BeautifulSoup

# These create the browser and set the required options needed for it to function with parcelsapp
from selenium.webdriver import Chrome
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

# These are for waiting for the package data to appear
#from selenium.webdriver.common.by import By
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
		self.scheduler.add_job(self.addOldPackagesToQueue, "interval", seconds=45)
		self.scheduler.start()

		self.dbPath = dbPath

		# Dont wait for full page load
		caps = DesiredCapabilities().CHROME
		caps["pageLoadStrategy"] = "none"
		# This option needs to be set otherwise the automated browser will be detected by the website
		opts = Options()
		opts.add_argument("--disable-blink-features=AutomationControlled")
		self.browser = Chrome(chromeDriverName, desired_capabilities=caps, chrome_options=opts)
		self.scrapePackageData("987271263865000564") # 91094210311903559338

	# Acts like a destructor
	def __del__(self):
		self.scheduler.shutdown()
		self.browser.close()

	def scrapePackageData(self, trackingNumber):
		# page = httpGetRequest("https://parcelsapp.com/en/tracking/" + trackingNumber)
		# soup = BeautifulSoup(page.content, "html.parser")
		# print(soup.prettify())

		self.browser.get("https://parcelsapp.com/en/tracking/" + str(trackingNumber))
		print(WebDriverWait(self.browser, 30000).until(EC.presence_of_element_located(("css selector", ".list-unstyled"))))
		print("Received data")

	# Checks if any packages haven't been updated for more than 6 hours. If so, adds them to the queue
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
		cur.execute("SELECT id FROM packages WHERE userID = ? AND trackingNumber = ?", [userID, trackingNumber])
		result = cur.fetchone()
		cur.close()
		if result:
			return False

		# If they aren't tracking the package, then we insert it into the db
		cur = self.con.cursor()
		cur.execute("INSERT INTO packages (trackingNumber, userID) VALUES (?, ?)", [trackingNumber, userID])
		self.con.commit()
		cur.close()
		return True

	@createDBConnection
	def getListOfPackages(self, userID):
		# This is pretty self explanatory. We get a cursor, select all packages, close the cursor and return
		cur = self.con.cursor()
		cur.row_factory = sqlite3.Row # Dictionary format
		
		cur.execute("SELECT * FROM packages WHERE userID = ?", [userID])
		result = cur.fetchall()
		cur.close()
		return result