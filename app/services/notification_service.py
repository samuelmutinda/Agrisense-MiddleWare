"""
Multi-channel notification service.

Supports:
- Email via SendGrid
- SMS via Twilio and Africa's Talking
- Voice calls via Twilio
- Push notifications via Firebase Cloud Messaging
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    VOICE = "voice"
    PUSH = "push"


class NotificationPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NotificationRequest(BaseModel):
    recipient_id: str
    channel: NotificationChannel
    title: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    recipient_fcm_token: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationResult(BaseModel):
    success: bool
    channel: NotificationChannel
    message_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime


# =============================================================================
# EMAIL VIA SENDGRID
# =============================================================================

async def send_email_sendgrid(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    from_email: Optional[str] = None,
) -> NotificationResult:
    """Send email via SendGrid API."""
    settings = get_settings()
    
    if not settings.sendgrid_configured:
        return NotificationResult(
            success=False,
            channel=NotificationChannel.EMAIL,
            error="SendGrid not configured",
            timestamp=datetime.utcnow(),
        )
    
    try:
        import httpx
        
        sender = from_email or settings.sendgrid_from_email
        
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": sender},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body_text}],
        }
        
        if body_html:
            payload["content"].append({"type": "text/html", "value": body_html})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.sendgrid_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        
        if response.status_code in (200, 202):
            message_id = response.headers.get("X-Message-Id", "")
            logger.info(f"Email sent to {to_email}: {message_id}")
            return NotificationResult(
                success=True,
                channel=NotificationChannel.EMAIL,
                message_id=message_id,
                timestamp=datetime.utcnow(),
            )
        else:
            error = f"SendGrid error: {response.status_code} - {response.text}"
            logger.error(error)
            return NotificationResult(
                success=False,
                channel=NotificationChannel.EMAIL,
                error=error,
                timestamp=datetime.utcnow(),
            )
    
    except Exception as e:
        error = f"Email send failed: {str(e)}"
        logger.error(error)
        return NotificationResult(
            success=False,
            channel=NotificationChannel.EMAIL,
            error=error,
            timestamp=datetime.utcnow(),
        )


# =============================================================================
# SMS VIA TWILIO
# =============================================================================

async def send_sms_twilio(
    to_phone: str,
    message: str,
) -> NotificationResult:
    """Send SMS via Twilio API."""
    settings = get_settings()
    
    if not settings.twilio_configured:
        return NotificationResult(
            success=False,
            channel=NotificationChannel.SMS,
            error="Twilio not configured",
            timestamp=datetime.utcnow(),
        )
    
    try:
        import httpx
        from base64 import b64encode
        
        auth = b64encode(
            f"{settings.twilio_account_sid}:{settings.twilio_auth_token}".encode()
        ).decode()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json",
                data={
                    "To": to_phone,
                    "From": settings.twilio_from_number,
                    "Body": message,
                },
                headers={"Authorization": f"Basic {auth}"},
                timeout=30.0,
            )
        
        if response.status_code in (200, 201):
            data = response.json()
            message_sid = data.get("sid", "")
            logger.info(f"SMS sent to {to_phone}: {message_sid}")
            return NotificationResult(
                success=True,
                channel=NotificationChannel.SMS,
                message_id=message_sid,
                timestamp=datetime.utcnow(),
            )
        else:
            error = f"Twilio error: {response.status_code} - {response.text}"
            logger.error(error)
            return NotificationResult(
                success=False,
                channel=NotificationChannel.SMS,
                error=error,
                timestamp=datetime.utcnow(),
            )
    
    except Exception as e:
        error = f"SMS send failed: {str(e)}"
        logger.error(error)
        return NotificationResult(
            success=False,
            channel=NotificationChannel.SMS,
            error=error,
            timestamp=datetime.utcnow(),
        )


# =============================================================================
# SMS VIA AFRICA'S TALKING
# =============================================================================

async def send_sms_africastalking(
    to_phone: str,
    message: str,
) -> NotificationResult:
    """Send SMS via Africa's Talking API."""
    settings = get_settings()
    
    if not settings.africastalking_configured:
        return NotificationResult(
            success=False,
            channel=NotificationChannel.SMS,
            error="Africa's Talking not configured",
            timestamp=datetime.utcnow(),
        )
    
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.africastalking.com/version1/messaging",
                data={
                    "username": settings.africastalking_username,
                    "to": to_phone,
                    "message": message,
                    "from": settings.africastalking_shortcode,
                },
                headers={
                    "apiKey": settings.africastalking_api_key,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
                timeout=30.0,
            )
        
        if response.status_code == 201:
            data = response.json()
            recipients = data.get("SMSMessageData", {}).get("Recipients", [])
            if recipients and recipients[0].get("status") == "Success":
                message_id = recipients[0].get("messageId", "")
                logger.info(f"SMS sent via AT to {to_phone}: {message_id}")
                return NotificationResult(
                    success=True,
                    channel=NotificationChannel.SMS,
                    message_id=message_id,
                    timestamp=datetime.utcnow(),
                )
        
        error = f"Africa's Talking error: {response.status_code} - {response.text}"
        logger.error(error)
        return NotificationResult(
            success=False,
            channel=NotificationChannel.SMS,
            error=error,
            timestamp=datetime.utcnow(),
        )
    
    except Exception as e:
        error = f"SMS send failed: {str(e)}"
        logger.error(error)
        return NotificationResult(
            success=False,
            channel=NotificationChannel.SMS,
            error=error,
            timestamp=datetime.utcnow(),
        )


# =============================================================================
# VOICE CALL VIA TWILIO
# =============================================================================

async def initiate_voice_call(
    to_phone: str,
    twiml_message: str,
) -> NotificationResult:
    """Initiate voice call via Twilio."""
    settings = get_settings()
    
    if not settings.twilio_configured:
        return NotificationResult(
            success=False,
            channel=NotificationChannel.VOICE,
            error="Twilio not configured",
            timestamp=datetime.utcnow(),
        )
    
    try:
        import httpx
        from base64 import b64encode
        
        auth = b64encode(
            f"{settings.twilio_account_sid}:{settings.twilio_auth_token}".encode()
        ).decode()
        
        # TwiML for text-to-speech
        twiml = f'<Response><Say voice="alice">{twiml_message}</Say></Response>'
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Calls.json",
                data={
                    "To": to_phone,
                    "From": settings.twilio_from_number,
                    "Twiml": twiml,
                },
                headers={"Authorization": f"Basic {auth}"},
                timeout=30.0,
            )
        
        if response.status_code in (200, 201):
            data = response.json()
            call_sid = data.get("sid", "")
            logger.info(f"Voice call initiated to {to_phone}: {call_sid}")
            return NotificationResult(
                success=True,
                channel=NotificationChannel.VOICE,
                message_id=call_sid,
                timestamp=datetime.utcnow(),
            )
        else:
            error = f"Twilio voice error: {response.status_code} - {response.text}"
            logger.error(error)
            return NotificationResult(
                success=False,
                channel=NotificationChannel.VOICE,
                error=error,
                timestamp=datetime.utcnow(),
            )
    
    except Exception as e:
        error = f"Voice call failed: {str(e)}"
        logger.error(error)
        return NotificationResult(
            success=False,
            channel=NotificationChannel.VOICE,
            error=error,
            timestamp=datetime.utcnow(),
        )


# =============================================================================
# PUSH NOTIFICATION VIA FCM
# =============================================================================

async def send_push_fcm(
    fcm_token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
) -> NotificationResult:
    """Send push notification via Firebase Cloud Messaging."""
    settings = get_settings()
    
    if not settings.fcm_server_key:
        return NotificationResult(
            success=False,
            channel=NotificationChannel.PUSH,
            error="FCM not configured",
            timestamp=datetime.utcnow(),
        )
    
    try:
        import httpx
        
        payload = {
            "to": fcm_token,
            "notification": {
                "title": title,
                "body": body,
            },
        }
        
        if data:
            payload["data"] = data
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://fcm.googleapis.com/fcm/send",
                json=payload,
                headers={
                    "Authorization": f"key={settings.fcm_server_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        
        if response.status_code == 200:
            resp_data = response.json()
            if resp_data.get("success", 0) > 0:
                message_id = resp_data.get("results", [{}])[0].get("message_id", "")
                logger.info(f"Push notification sent: {message_id}")
                return NotificationResult(
                    success=True,
                    channel=NotificationChannel.PUSH,
                    message_id=message_id,
                    timestamp=datetime.utcnow(),
                )
        
        error = f"FCM error: {response.status_code} - {response.text}"
        logger.error(error)
        return NotificationResult(
            success=False,
            channel=NotificationChannel.PUSH,
            error=error,
            timestamp=datetime.utcnow(),
        )
    
    except Exception as e:
        error = f"Push notification failed: {str(e)}"
        logger.error(error)
        return NotificationResult(
            success=False,
            channel=NotificationChannel.PUSH,
            error=error,
            timestamp=datetime.utcnow(),
        )


# =============================================================================
# UNIFIED SEND NOTIFICATION
# =============================================================================

async def send_notification(
    request: NotificationRequest,
    prefer_africastalking: bool = True,
) -> NotificationResult:
    """
    Send notification via the specified channel.
    
    Args:
        request: NotificationRequest with all details
        prefer_africastalking: For SMS, prefer Africa's Talking over Twilio
    
    Returns:
        NotificationResult with status
    """
    if request.channel == NotificationChannel.EMAIL:
        if not request.recipient_email:
            return NotificationResult(
                success=False,
                channel=request.channel,
                error="No email address provided",
                timestamp=datetime.utcnow(),
            )
        return await send_email_sendgrid(
            to_email=request.recipient_email,
            subject=request.title,
            body_text=request.body,
        )
    
    elif request.channel == NotificationChannel.SMS:
        if not request.recipient_phone:
            return NotificationResult(
                success=False,
                channel=request.channel,
                error="No phone number provided",
                timestamp=datetime.utcnow(),
            )
        
        settings = get_settings()
        message = f"{request.title}\n\n{request.body}"
        
        # Try Africa's Talking first for East Africa
        if prefer_africastalking and settings.africastalking_configured:
            result = await send_sms_africastalking(request.recipient_phone, message)
            if result.success:
                return result
        
        # Fall back to Twilio
        if settings.twilio_configured:
            return await send_sms_twilio(request.recipient_phone, message)
        
        return NotificationResult(
            success=False,
            channel=request.channel,
            error="No SMS provider configured",
            timestamp=datetime.utcnow(),
        )
    
    elif request.channel == NotificationChannel.VOICE:
        if not request.recipient_phone:
            return NotificationResult(
                success=False,
                channel=request.channel,
                error="No phone number provided",
                timestamp=datetime.utcnow(),
            )
        
        message = f"{request.title}. {request.body}"
        return await initiate_voice_call(request.recipient_phone, message)
    
    elif request.channel == NotificationChannel.PUSH:
        if not request.recipient_fcm_token:
            return NotificationResult(
                success=False,
                channel=request.channel,
                error="No FCM token provided",
                timestamp=datetime.utcnow(),
            )
        return await send_push_fcm(
            fcm_token=request.recipient_fcm_token,
            title=request.title,
            body=request.body,
            data=request.metadata,
        )
    
    return NotificationResult(
        success=False,
        channel=request.channel,
        error=f"Unknown channel: {request.channel}",
        timestamp=datetime.utcnow(),
    )


async def send_bulk_notifications(
    requests: List[NotificationRequest],
) -> List[NotificationResult]:
    """Send multiple notifications."""
    import asyncio
    return await asyncio.gather(*[send_notification(req) for req in requests])
