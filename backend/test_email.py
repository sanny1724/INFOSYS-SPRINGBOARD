from mailer import send_alert_email
import os
from dotenv import load_dotenv

load_dotenv()

print("--- Email Configuration Check ---")
username = os.getenv("MAIL_USERNAME")
password = os.getenv("MAIL_PASSWORD")
recipient = os.getenv("MAIL_RECIPIENT")

print(f"MAIL_USERNAME: {'Set' if username else 'MISSING'}")
print(f"MAIL_PASSWORD: {'Set' if password else 'MISSING'}")
print(f"MAIL_RECIPIENT: {'Set' if recipient else 'MISSING'}")

if not username or not password or not recipient:
    print("\nERROR: Missing credentials in .env file.")
    print("Please ensure you have set MAIL_USERNAME, MAIL_PASSWORD, and MAIL_RECIPIENT.")
else:
    print("\nAttempting to send test email...")
    # Create a dummy image for testing
    # Use an existing image if available, otherwise create a dummy
    image_path = "temp_alert_frame.jpg" if os.path.exists("temp_alert_frame.jpg") else "test_image.jpg"
    if image_path == "test_image.jpg":
        with open("test_image.jpg", "wb") as f:
            f.write(b"dummy image content")

    success = send_alert_email(image_path, recipient, subject="EcoEye Test Email", body="This is a test email to verify your configuration.")
    
    if success:
        print("\nSUCCESS: Test email sent! Check your inbox.")
    else:
        print("\nFAILURE: Could not send email. Check your App Password and internet connection.")
    
    # Clean up
    if os.path.exists("test_image.jpg"):
        os.remove("test_image.jpg")
