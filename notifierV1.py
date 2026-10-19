import os
import smtplib
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Safeguard dotenv import so container environments without local .env don't crash
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _get_credential(key: str, default: str = "") -> str:
    """
    Safely retrieves credentials across:
    1. Streamlit Cloud Secrets (st.secrets) - checked first and cast strictly to clean strings
    2. System/local environment variables (.env / GitHub Actions)
    """
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            val = str(st.secrets[key]).strip()
            if val:
                return val
    except Exception:
        pass

    env_val = os.getenv(key, default)
    return str(env_val).strip() if env_val else ""


def send_stock_email(subject: str, html_body: str, recipient: str = None) -> bool:
    """Dispatches an HTML email alert via Gmail SMTP SSL."""
    gmail_user = _get_credential("EMAIL_SENDER") or _get_credential("GMAIL_USER")
    gmail_password = _get_credential("EMAIL_PASSWORD") or _get_credential("GMAIL_APP_PASSWORD")
    recipient_email = (
        recipient
        or _get_credential("EMAIL_RECEIVER")
        or _get_credential("RECIPIENT_EMAIL")
        or gmail_user
    )

    if not gmail_user or not gmail_password:
        print("⚠️ Email notification skipped: Missing EMAIL_SENDER/GMAIL_USER or EMAIL_PASSWORD/GMAIL_APP_PASSWORD.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"TrendNorth Alerts <{gmail_user}>"
    msg["To"] = recipient_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, recipient_email, msg.as_string())
        print(f"📧 Alert email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to dispatch email alert: {e}")
        traceback.print_exc()
        return False


def send_feedback_email(sender_name: str, sender_email: str, sentiment: str, message: str) -> bool:
    """Formats and routes user feedback from the Streamlit UI directly to your inbox."""
    subject = f"💬 TrendNorth Feedback: [{sentiment.upper()}] from {sender_name}"

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #222; line-height: 1.5;">
        <div style="background-color: #0b1f3a; padding: 16px; border-radius: 8px 8px 0 0; color: #ffffff;">
            <h2 style="margin: 0; font-size: 1.25rem;">💬 New Feedback Received: TrendNorth</h2>
        </div>
        <div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 0 0 8px 8px; background-color: #ffffff;">
            <p style="margin: 4px 0;"><strong>From:</strong> {sender_name} (&lt;<a href="mailto:{sender_email}">{sender_email}</a>&gt;)</p>
            <p style="margin: 4px 0;"><strong>Topic:</strong> <span style="background-color: #f0f4f8; padding: 3px 8px; border-radius: 4px; font-weight: bold; color: #0b1f3a;">{sentiment}</span></p>
            <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 16px 0;">
            <p style="margin-bottom: 6px; font-weight: bold; color: #475569;">Comments / Message:</p>
            <div style="white-space: pre-wrap; font-size: 14px; background: #f8fafc; padding: 12px; border-left: 4px solid #0284c7; border-radius: 0 4px 4px 0;">{message}</div>
            <br>
            <p style="font-size: 12px; color: #94a3b8; margin: 0;">Dispatched via <a href="https://trendnorth.streamlit.app" style="color: #0284c7;">trendnorth.streamlit.app</a> feedback widget.</p>
        </div>
    </body>
    </html>
    """
    return send_stock_email(subject=subject, html_body=html_content)


if __name__ == "__main__":
    test_html = """
    <h2>📈 TrendNorth Test Alert</h2>
    <p>SMTP notification verified successfully from your project environment.</p>
    """
    send_stock_email("TrendNorth Notification Test", test_html)