"""Notification service for SMS and Email"""
from app.config import settings
from app.services.twilio_service import twilio_service
import logging

logger = logging.getLogger(__name__)

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

class NotificationService:
    def __init__(self):
        self.sendgrid_client = None
        if SENDGRID_AVAILABLE and hasattr(settings, 'SENDGRID_API_KEY'):
            try:
                self.sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
                logger.info("✅ SendGrid Email initialized")
            except:
                logger.info("📝 Using mock email")
    
    async def send_booking_confirmation_sms(
        self,
        phone_number: str,
        customer_name: str,
        business_name: str,
        date_time: str,
        confirmation_code: str
    ) -> dict:
        """Send booking confirmation via SMS"""
        message = f"Hi {customer_name}! Your reservation at {business_name} is confirmed for {date_time}. Confirmation code: {confirmation_code}"
        
        return twilio_service.send_sms(phone_number, message)
    
    async def send_booking_confirmation_email(
        self,
        email: str,
        customer_name: str,
        business_name: str,
        date_time: str,
        confirmation_code: str
    ) -> dict:
        """Send booking confirmation via Email"""
        if not self.sendgrid_client:
            logger.info(f"📧 Mock Email to {email}")
            return {"success": True, "mock": True}
        
        try:
            message = Mail(
                from_email='noreply@zenith-ai.app',
                to_emails=email,
                subject=f'Booking Confirmation - {business_name}',
                html_content=f"""
                <html>
                <body>
                    <h2>Booking Confirmed!</h2>
                    <p>Hi {customer_name},</p>
                    <p>Your reservation at <strong>{business_name}</strong> is confirmed.</p>
                    <p><strong>Date & Time:</strong> {date_time}</p>
                    <p><strong>Confirmation Code:</strong> {confirmation_code}</p>
                    <p>We look forward to seeing you!</p>
                </body>
                </html>
                """
            )
            
            response = self.sendgrid_client.send(message)
            return {"success": True, "status_code": response.status_code}
            
        except Exception as e:
            logger.error(f"Email error: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_cancellation_confirmation(
        self,
        phone_number: str,
        customer_name: str,
        business_name: str,
        confirmation_code: str
    ) -> dict:
        """Send cancellation confirmation"""
        message = f"Hi {customer_name}, your reservation at {business_name} (Code: {confirmation_code}) has been cancelled. Contact us if you have questions."
        
        return twilio_service.send_sms(phone_number, message)

notification_service = NotificationService()
