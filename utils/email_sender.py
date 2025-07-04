import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def send_booking_email(to_email, community, amenity, date, time):
    from_email = os.getenv("FROM_EMAIL")
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    if not all([from_email, smtp_host, smtp_port, smtp_user, smtp_pass]):
        raise ValueError("Missing one or more required email environment variables.")

    try:
        smtp_port = int(smtp_port)
    except ValueError:
        raise ValueError("SMTP_PORT must be an integer.")

    subject = f"Booking Confirmation: {amenity} at {community}"
    html_content = f"""
    <html>
    <body>
        <h2>Booking Confirmation</h2>
        <p><strong>Community:</strong> {community}</p>
        <p><strong>Amenity:</strong> {amenity}</p>
        <p><strong>Date:</strong> {date}</p>
        <p><strong>Time:</strong> {time}</p>
        <p>Thank you for using the Amenity Booking Service!</p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    part = MIMEText(html_content, "html")
    msg.attach(part)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, to_email, msg.as_string())
            print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print("❌ Failed to send email:", e)
        raise
