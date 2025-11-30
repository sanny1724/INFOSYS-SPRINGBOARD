import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os
from dotenv import load_dotenv

load_dotenv()

def send_alert_email(image_path: str, subject: str = "URGENT: Poacher Detected - EcoEye AI", body: str = "A potential poacher was detected by the EcoEye AI system. Please check the attached evidence."):
    sender_email = os.getenv("MAIL_USERNAME")
    sender_password = os.getenv("MAIL_PASSWORD")
    recipient_email = os.getenv("MAIL_RECIPIENT")

    if not sender_email or not sender_password or not recipient_email:
        print("Skipping email: Missing credentials in .env file")
        return False

    print(f"Sending email to {recipient_email}...")
    
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email

        text = MIMEText(body)
        msg.attach(text)

        with open(image_path, 'rb') as f:
            img_data = f.read()
            image = MIMEImage(img_data, name=os.path.basename(image_path))
            msg.attach(image)

        # Connect to Gmail SMTP (standard port 587)
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        print("Email sent successfully!")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
