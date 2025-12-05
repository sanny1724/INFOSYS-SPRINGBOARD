import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os
from dotenv import load_dotenv

load_dotenv()

def send_alert_email(image_path: str, recipient_email: str, subject: str = "URGENT: Poacher Detected - EcoEye AI", body: str = None, location_link: str = None):
    # Try both naming conventions
    sender_email = os.getenv("EMAIL_SENDER") or os.getenv("MAIL_USERNAME")
    sender_password = os.getenv("EMAIL_PASSWORD") or os.getenv("MAIL_PASSWORD")

    print(f"DEBUG: Sender: {sender_email[:3]}***@{sender_email.split('@')[-1]}")
    print(f"DEBUG: Recipient: {recipient_email}")
    
    if not sender_email or not sender_password:
        print("Error: Email credentials not found in environment variables.")
        return False

    print(f"DEBUG: Connecting to SMTP server...")
    
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email

        if body is None:
            body = "⚠️ A potential poacher has been detected by the EcoEye AI system.\n\nPlease review the attached image immediately."

        if location_link:
            body += f"\n\n📍 Incident Location: {location_link}"
            body += "\n(Click to view on Google Maps)"

        text = MIMEText(body)
        msg.attach(text)

        if os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                img_data = f.read()
                # Default to jpeg if guessing fails, or just let MIMEImage handle it but provide subtype if needed
                # Better: determine subtype from extension
                import imghdr
                subtype = imghdr.what(None, img_data) or 'jpeg'
                image = MIMEImage(img_data, name=os.path.basename(image_path), _subtype=subtype)
                msg.attach(image)
        else:
            print(f"Warning: Image file not found at {image_path}")

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
