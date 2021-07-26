# package-tracker
current delays:
Outdated packages are checked for every 15 seconds. These are added to the queue
Every 60 seconds, the topmost package in the queue is scraped with selenium
Every 300 seconds, the system checks for packages that are dead, and alerts the user that they will soon be deleted

You will need to create your own environment variable file (.env)