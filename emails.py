from os import environ
from ssl import create_default_context

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from jinja2 import Environment, FileSystemLoader

class EmailHandler:
	# When the class is initiated it will create a connection to google's smtp server
	def __init__(self):
		# Constants - makes it easier to modify them if they are up here
		self.emailAddress = environ["EMAIL_ADDRESS"]
		self.hostname = "http://127.0.0.1:5000"

		# Connect to email server
		self.sslContext = create_default_context()
		self.emailServer = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=self.sslContext)
		self.emailServer.login(self.emailAddress, environ["EMAIL_PASSWORD"])

		# Use jinja environment to pass variables to email templates
		self.jinjaEnv = Environment(loader=FileSystemLoader("templates/emails"))

	def __del__(self):
		self.emailServer.close()

	# Sends an html email to the passed address asking them to click a link which wil verify their account
	def sendVerificationEmail(self, recipient, token):
		html = self.jinjaEnv.get_template("verifyEmail.html").render(hostname=self.hostname, token=token)
		self.sendMail(recipient, "Account verification", html)

	def sendPasswordResetEmail(self, recipient, token):
		html = self.jinjaEnv.get_template("resetPassword.html").render(hostname=self.hostname, token=token)
		self.sendMail(recipient, "Password reset request", html)

	def sendPackageReminderEmail(self, recipient, packageTitle, packageID):
		html = self.jinjaEnv.get_template("packageReminder.html").render(hostname=self.hostname, packageID=packageID, packageTitle=packageTitle)
		self.sendMail(recipient, "Outdated package", html)

	# This will send the actual mail to someone
	def sendMail(self, recipient, subject, body):
		# Setup the message
		message = MIMEMultipart("alternative")
		message["Subject"] = subject
		message["From"] = self.emailAddress
		message["To"] = recipient
		# Add the content and send it
		message.attach(MIMEText(body, "html"))
		self.emailServer.sendmail(self.emailAddress, recipient, message.as_string())