import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import datetime

# Load variables from .env file
load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

def send_stock_email(subject: str, html_body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"TSX Screener Alert <{GMAIL_USER}>"
    msg["To"] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())
        print(f"📧 Email alert sent successfully to {RECIPIENT_EMAIL}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

# Standalone Test
if __name__ == "__main__":
    test_html = """
    <h2>📈 TSX Screener Test Alert</h2>
    <p>This is a test notification from your VS Code stock screener setup.</p>
    """
    send_stock_email("TSX Test Alert", test_html)
# Send feedback email from user
def send_feedback_email(sender_email: str, feedback_text: str):
    """Sends user feedback to the admin inbox using existing SMTP configuration."""
    subject = f"💬 TSX Screener Feedback from {sender_email}"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.5;">
        <h2 style="color: #0b3954;">New User Feedback Received</h2>
        <p><strong>From:</strong> <a href="mailto:{sender_email}">{sender_email}</a></p>
        <p><strong>Submitted:</strong> {datetime.now().strftime('%Y-%m-%d %I:%M %p')}</p>
        <hr style="border: 0; border-top: 1px solid #ddd; margin: 15px 0;">
        <p><strong>Feedback:</strong></p>
        <blockquote style="background: #f9f9f9; border-left: 4px solid #0b3954; padding: 10px 15px; margin: 0; white-space: pre-wrap;">
{feedback_text}
        </blockquote>
    </body>
    </html>
    """
    send_stock_email(subject=subject, html_body=html_body)