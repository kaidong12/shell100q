"""
Notification manager for the Lab Management System.
"""

import logging
from typing import Dict, Any
import smtplib
from webexteamssdk import WebexTeamsAPI
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys

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

    def send_device_notification(
        self, device_id: int, message: str, data: Dict[str, Any]
    ):
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
        # subject = f'Subject: {subject} \n\n {context}'
        # configure SMTP server
        smtp_server = "outbound.cisco.com"
        port = 25
        sender_email = "no-reply@cisco.com"

        recipient_email = email_list
        message = MIMEMultipart()
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = ", ".join(email_list)
        message.attach(MIMEText(context, "plain", "utf-8"))
        try:
            with smtplib.SMTP(smtp_server, port) as server:
                server.starttls()
                server.sendmail(sender_email, recipient_email, message.as_string())

                logger.info("send mail successfully")
        except Exception as e:
            logger.warning(f"fail to send mail: {e}")

    def notify_user_by_email_with_plain_txt(
        self, subject: str, body: str, email_list: list
    ):
        msg = MIMEMultipart()
        msg["From"] = "no-reply@cisco.com"
        msg["To"] = ", ".join(email_list)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        smtp_server = "outbound.cisco.com"
        port = 25
        recipient_email = email_list
        try:
            server = smtplib.SMTP(smtp_server, port)
            server.starttls()
            text = msg.as_string()
            server.sendmail(msg["From"], recipient_email, text)
            logger.info("send mail successfully")
        except Exception as e:
            logger.warning(f"fail to send mail: {e}")
        finally:
            server.quit()

    def notify_user_by_email_with_html(self, subject: str, body: str, email_list: list):
        msg = MIMEMultipart("alternative")
        msg["From"] = "no-reply@cisco.com"
        msg["To"] = ", ".join(email_list)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html", "utf-8"))

        smtp_server = "outbound.cisco.com"
        port = 25
        recipient_email = email_list
        try:
            server = smtplib.SMTP(smtp_server, port)
            server.starttls()
            text = msg.as_string()
            server.sendmail(msg["From"], recipient_email, text)
            logger.info("send mail successfully")
        except Exception as e:
            logger.warning(f"fail to send mail: {e}")
        finally:
            server.quit()

    def build_summary_columnset(self, summary_text):
        """
        Convert 'key : value' lines into an Adaptive Card ColumnSet
        compatible with Cisco Webex (Adaptive Card v1.2).
        """
        left_items = []
        right_items = []

        for line in summary_text.strip().splitlines():
            if ":" not in line:
                continue

            key, value = map(str.strip, line.split(":", 1))

            if value == "" or key == "":
                continue
            if key.count("percentage"):
                key = key.replace("percentage", "%")

            left_items.append({
                "type": "TextBlock",
                "text": key,
                "wrap": True
            })

            right_items.append({
                "type": "TextBlock",
                "text": value,
                "wrap": True
            })

        return {
            "type": "ColumnSet",
            "columns": [
                {
                    "type": "Column",
                    "width": "auto",
                    "horizontalAlignment": "Left",
                    "items": left_items
                },
                {
                    "type": "Column",
                    "width": "stretch",
                    "horizontalAlignment": "Left",
                    "items": right_items
                }
            ]
        }

    def notify_user_by_webex(self, subject, content, webex_id):
        api = WebexTeamsAPI(
            access_token="ZmNmM2M2MzktNTEzMy00N2VhLTgzOWMtNDE0N2E3NmRjYmE5Y2I5OTVmNDgtMGE5_PF84_1eb65fdf-9643-417f-9974-ad72cae0e10f"
        )

        # get room list of webex bot
        # rooms = api.rooms.list()
        # for room in rooms:
        #     print(f"{room.title}: {room.id}")

        if content.count('Test results summary:'):
            subject = "Test Results Summary"
        content_lst = " ".join(content).split('|')
        if content_lst[0].count("db_build_id"):
            db_build_id = content_lst[0].split(':')[1].strip()
            subject = f"{subject} [{db_build_id}](http://vip-oldregressdb.cisco.com:8080/regressdb/{db_build_id}/)"
            msg = "\n".join(content_lst[1:])
        else:
            msg = "\n".join(content_lst)

        card_content = {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.3",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": subject,
                        "weight": "Bolder",
                        "horizontalAlignment": "Center",
                        "size": "Medium"
                    },
                    {
                        "type": "ColumnSet",
                        "separator": True,
                        "columns": [
                            {
                            "type": "Column",
                            "width": "stretch",
                            "items": []
                            }
                        ]
                    },
                    # {
                    #     "type": "TextBlock",
                    #     "text": "Test Execution Summary",
                    #     "weight": "Bolder",
                    #     "size": "Medium",
                    #     "horizontalAlignment": "Left",
                    #     "spacing": "Medium"
                    # },
                    self.build_summary_columnset(msg)
                ]
            }
        }

        # send message
        if not webex_id:
            logger.warning("No Webex ID provided for notification.")
            return
        logger.info(f"Sending Webex message to {webex_id}")
        # check if webex_id is a valid email format
        if not isinstance(webex_id, str):
            logger.warning(f"Invalid Webex ID format: {webex_id}")
            return
        if webex_id.count('@')==1:
            #api.messages.create(toPersonEmail=webex_id, text=contextStr)
            api.messages.create(
                toPersonEmail=webex_id,
                text=subject,
                attachments=[card_content]
            )
        elif webex_id.count('-')==4:
            # api.messages.create(
            #     # roomId="c582edc0-3443-11ef-a59e-497ab6833a4a", text=contextStr
            #     roomId="306d3220-eadd-11f0-8ed5-e7669d71f2e3", text=contextStr
            # )
            api.messages.create(
                roomId=webex_id, 
                text=subject,
                attachments=[card_content]
            )
        else:
            logger.warning(f"Invalid Webex ID format: {webex_id}")

if __name__ == "__main__":
    # Example usage
    nm = NotificationManager()
    nm.notify_user_by_webex(
        subject="Regression Notification",
        content=sys.argv[2:],
        webex_id=sys.argv[1].strip()
    )
