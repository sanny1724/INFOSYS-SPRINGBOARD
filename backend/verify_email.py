import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def test_email():
    sender = os.getenv("EMAIL_SENDER") or os.getenv("MAIL_USERNAME")
    password = os.getenv("EMAIL_PASSWORD") or os.getenv("MAIL_PASSWORD")
    recipient = os.getenv("MAIL_RECIPIENT")

    print(f"Sender: {sender}")
    print(f"Recipient: {recipient}")

    if not sender or not password:
        print("Error: Missing credentials")
        return

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = "Wildeye Test Email"

    body = "This is a test email to verify SMTP configuration."
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        text = msg.as_string()
        server.sendmail(sender, recipient, text)
        server.quit()
        print("Email sent successfully from script!")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    test_email()
