"""
Notification manager for the Lab Management System.
"""

import logging
from typing import Dict, Any
import smtplib
from webexteamssdk import WebexTeamsAPI
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logger = logging.getLogger(__name__)

class NotificationManager:
    """
    Manages notifications for the Lab Management System.
    Handles Webex notifications.
    """
    
    def __init__(self):
        """Initialize the notification manager."""
        logger.info("Notification Manager initialized")
    
    def send_device_notification(self, device_id: int, message: str, data: Dict[str, Any]):
        """
        Send a notification about a device event.
        
        Args:
            device_id: ID of the device
            message: Notification message
            data: Additional data for the notification
        """
        # This is a placeholder implementation
        logger.info(f"NOTIFICATION: Device {device_id}: {message}")
        
        # TODO: Implement actual notification sending via Webex
        # For now, just log the message
        return True

    def notify_user_by_email(self, subject, context, email_list):
        #subject = f'Subject: {subject} \n\n {context}'
        # configure SMTP server
        smtp_server = "outbound.cisco.com"
        port = 25
        sender_email = "no-reply@cisco.com"

        recipient_email = email_list
        message = MIMEMultipart()
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = ", ".join(email_list)
        message.attach(MIMEText(context, 'plain', 'utf-8'))
        try:
            with smtplib.SMTP(smtp_server, port) as server:
                server.starttls()
                server.sendmail(sender_email, recipient_email, message.as_string())

                logger.info("send mail successfully")
        except Exception as e:
            logger.warning(f"fail to send mail: {e}")

    def notify_user_by_email_with_plain_txt(self, subject:str, body:str, email_list:list):
        msg = MIMEMultipart()
        msg['From'] = 'no-reply@cisco.com'
        msg['To'] = ', '.join(email_list)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        smtp_server =  "outbound.cisco.com"
        port = 25
        recipient_email = email_list
        try:
            server = smtplib.SMTP(smtp_server, port)
            server.starttls()
            text = msg.as_string()
            server.sendmail(msg['From'], recipient_email, text)
            logger.info("send mail successfully")
        except Exception as e:
            logger.warning(f"fail to send mail: {e}")
        finally:
            server.quit()

    def notify_user_by_email_with_html(self, subject:str, body:str, email_list:list):
        msg = MIMEMultipart("alternative")
        msg['From'] = 'no-reply@cisco.com'
        msg['To'] = ', '.join(email_list)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html', 'utf-8'))

        smtp_server =  "outbound.cisco.com"
        port = 25
        recipient_email = email_list
        try:
            server = smtplib.SMTP(smtp_server, port)
            server.starttls()
            text = msg.as_string()
            server.sendmail(msg['From'], recipient_email, text)
            logger.info("send mail successfully")
        except Exception as e:
            logger.warning(f"fail to send mail: {e}")
        finally:
            server.quit()


    def notify_user_by_webex(self, subject, context, to_list):
        # 初始化 API
        api = WebexTeamsAPI(access_token='Mzk3MGU4YTQtNTc3YS00ODVmLWI5NTEtMzgwN2IyODMxYTNhYjczZDBmMjgtZTYx_PF84_1eb65fdf-9643-417f-9974-ad72cae0e10f')
        contextStr = subject + context
        # 发送消息
        for person in to_list:
            if not person:
                continue
            logger.info(f"Sending Webex message to {person}")
            # check if person is a valid email format
            if not isinstance(person, str):
                logger.warning(f"Invalid email format: {person}")
                continue
            api.messages.create(toPersonEmail=person, text=contextStr)
