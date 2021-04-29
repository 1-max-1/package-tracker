from os import environ
import smtplib
from ssl import create_default_context

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailHandler:
	# WHen the class is initiated it will create a connection to google's smtp server
	def __init__(self):
		self.sslContext = create_default_context()
		self.emailServer = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=self.sslContext)
		self.emailServer.login("flask19181@gmail.com", environ["EMAIL_PASSWORD"])

	def __del__(self):
		self.emailServer.close()

	# Sends an html email to the passed address asking them to click a link which wil verify their account
	def sendVerificationEmail(self, recipient, token):
		# Setup the message
		message = MIMEMultipart("alternative")
		message["Subject"] = "Account verification"
		message["From"] = "flask19181@gmail.com"
		message["To"] = recipient

		# Add the content and send it
		message.attach(MIMEText(f"""
<html>
<body>
<p>
Thanks for signing up! There's just one more step - click the link below to verify your account.
<br/><br/><a href="http://127.0.0.1:5000/confirmUserEmail/{token}">http://127.0.0.1:5000/confirmUserEmail/{token}</a><br/><br/>
If it doesn't work try copying the address and entering it in a browsers search bar.
This link will expire in 30 minutes.
</p>
</body>
</html>""", "html"))

		self.emailServer.sendmail("flask19181@gmail.com", recipient, message.as_string())