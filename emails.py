from os import environ
import smtplib
from ssl import create_default_context

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailHandler:
	# When the class is initiated it will create a connection to google's smtp server
	def __init__(self):
		# Constants - makes it easier to modify them if they are up here
		self.emailAddress = "flask19181@gmail.com"
		self.targetURL = "http://127.0.0.1:5000/"

		# Connect to email server
		self.sslContext = create_default_context()
		self.emailServer = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=self.sslContext)
		self.emailServer.login(self.emailAddress, environ["EMAIL_PASSWORD"])

	def __del__(self):
		self.emailServer.close()

	# Sends an html email to the passed address asking them to click a link which wil verify their account
	def sendVerificationEmail(self, recipient, token):
		self.sendMail(recipient, "Account verification", f"""
<html>
<body>
<p>
Thanks for signing up! There's just one more step - click the link below to verify your account.
<br/><br/><a href="{self.targetURL}confirmUserEmail/{token}">{self.targetURL}confirmUserEmail/{token}</a><br/><br/>
If it doesn't work try copying the address and entering it in a browsers search bar.
This link will expire in 30 minutes.
</p>
</body>
</html>""")

	def sendPasswordResetEmail(self, recipient, token):
		self.sendMail(recipient, "Password reset request", f"""
<html>
<body>
<p>
There was a request to reset your password. Click the link below to change it.
<br/><br/><a href="{self.targetURL}resetPassword/{token}">{self.targetURL}resetPassword/{token}</a><br/><br/>
If it doesn't work try copying the address and entering it in a browsers search bar.
This link will expire in 30 minutes.

If this wasn't you, don't worry. Your account and password is safe. You can safely ignore this email.
</p>
</body>
</html>""")

	def sendPackageReminderEmail(self, recipient, packageTitle, packageID):
		self.sendMail(recipient, "Outdated Package", f"""
<html>
<body>
<p>
Your package <i>{packageTitle}</i> has not had any new data for almost a month.
Because of this, it will soon be deleted.
If you wish to keep your package, please click the link below.
<br/><a href="{self.targetURL}renewPackage/{packageID}">{self.targetURL}renewPackage/{packageID}</a><br/>
If it doesn't work try copying the address and entering it in a browsers search bar.
</p>
</body>
</html>
""")

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