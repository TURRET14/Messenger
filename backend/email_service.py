import aiosmtplib
import aiosmtplib.errors
import asyncio
import email.message
import email.mime.text
import fastapi
import socket
from backend import environment
from backend.routers.errors import ErrorRegistry

class EmailService:
    @staticmethod
    async def send_email(receiver_email: str, message_text: str, subject_data: str):
        message = email.message.EmailMessage()
        message["From"] = environment.SMTP_FROM
        message["To"] = receiver_email
        message["Subject"] = subject_data
        message.set_content(message_text, subtype = "html")

        try:
            await aiosmtplib.send(
            message,
            hostname = environment.SMTP_HOSTNAME,
            port = 465,
            username = environment.SMTP_USERNAME,
            password = environment.SMTP_PASSWORD,
            use_tls = True)
        except (
            aiosmtplib.errors.SMTPException,
            asyncio.TimeoutError,
            OSError,
            socket.gaierror,
        ):
            raise fastapi.exceptions.HTTPException(
                status_code = ErrorRegistry.email_delivery_error.error_status_code,
                detail = ErrorRegistry.email_delivery_error,
            )


    @staticmethod
    async def send_email_confirmation(receiver_email: str, code: str):
        html_message = f"""
        <H1>{environment.SERVICE_PUBLIC_NAME}: Регистрация</H1>
        <H1>Подтверждение почты</H1>
        <H2>Ваш код:</H2>
        <H2><b style="font-size:30PX">{code}</b></H2>
        """
        subject = f"{environment.SERVICE_PUBLIC_NAME}: Регистрация"

        await EmailService.send_email(receiver_email, html_message, subject)
