import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

def debug_email():
    print("--- DEBUG EMAIL START ---")
    
    sender = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")
    recipient = os.getenv("MAIL_RECIPIENT")
    
    print(f"Sender: {sender}")
    print(f"Password: {'*' * len(password) if password else 'None'}")
    print(f"Recipient: {recipient}")
    
    if not sender or not password or not recipient:
        print("MISSING CREDENTIALS")
        return

    try:
        print("Connecting to smtp.gmail.com:587...")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.set_debuglevel(1) # Enable SMTP debug output
        
        print("Starting TLS...")
        server.starttls()
        
        print("Logging in...")
        server.login(sender, password)
        print("Login successful!")
        
        msg = MIMEText("This is a debug email from Wildeye AI.")
        msg['Subject'] = "Wildeye Debug Email"
        msg['From'] = sender
        msg['To'] = recipient
        
        print(f"Sending to {recipient}...")
        server.send_message(msg)
        print("Message sent!")
        
        server.quit()
        print("--- DEBUG EMAIL SUCCESS ---")
        
    except Exception as e:
        print(f"--- DEBUG EMAIL FAILED ---")
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_email()
