import os
import smtplib
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

def send_stock_email(subject: str, html_body: str, recipient: str = None) -> bool:
    """Dispatches an HTML email alert via Gmail SMTP over STARTTLS (port 587)."""
    gmail_user = os.getenv("GMAIL_USER") or os.getenv("EMAIL_SENDER")
    raw_password = os.getenv("GMAIL_APP_PASSWORD") or os.getenv("EMAIL_PASSWORD")
    
    gmail_password = raw_password.replace(" ", "").strip() if raw_password else ""
    recipient_email = recipient or os.getenv("RECIPIENT_EMAIL") or os.getenv("ALERT_RECIPIENT") or gmail_user

    if not gmail_user or not gmail_password:
        print("⚠️ Email notification skipped: Missing credentials in environment.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"TrendNorth Analytics <{gmail_user}>"
    msg["To"] = recipient_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, recipient_email, msg.as_string())
        print(f"📧 Alert email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to dispatch email alert: {e}")
        traceback.print_exc()
        return False

def send_feedback_email(sender_name: str, sender_email: str, sentiment: str, message: str) -> bool:
    """Formats and routes user feedback directly to your inbox."""
    subject = f"💬 TrendNorth Feedback: [{sentiment.upper()}] from {sender_name}"

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #222; line-height: 1.5;">
        <div style="background-color: #0b1f3a; padding: 16px; border-radius: 8px 8px 0 0; color: #ffffff;">
            <h2 style="margin: 0; font-size: 1.25rem;">💬 New Feedback Received: TrendNorth Analytics</h2>
        </div>
        <div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 0 0 8px 8px; background-color: #ffffff;">
            <p style="margin: 4px 0;"><strong>From:</strong> {sender_name} (&lt;<a href="mailto:{sender_email}">{sender_email}</a>&gt;)</p>
            <p style="margin: 4px 0;"><strong>Topic:</strong> <span style="background-color: #f0f4f8; padding: 3px 8px; border-radius: 4px; font-weight: bold; color: #0b1f3a;">{sentiment}</span></p>
            <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 16px 0;">
            <p style="margin-bottom: 6px; font-weight: bold; color: #475569;">Comments / Message:</p>
            <div style="white-space: pre-wrap; font-size: 14px; background: #f8fafc; padding: 12px; border-left: 4px solid #0284c7; border-radius: 0 4px 4px 0;">{message}</div>
            <br>
            <p style="font-size: 12px; color: #94a3b8; margin: 0;">Dispatched via TrendNorth Analytics feedback system.</p>
        </div>
    </body>
    </html>
    """
    return send_stock_email(subject=subject, html_body=html_content)

if __name__ == "__main__":
    test_html = """
    <h2>📈 TrendNorth Analytics Test Alert</h2>
    <p>SMTP notification verified successfully from your project environment.</p>
    """
    send_stock_email("TrendNorth Notification Test", test_html)