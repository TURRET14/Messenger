import email.mime.text

import aiosmtplib

from backend import environment


class EmailService:
    @staticmethod
    async def send_email(receiver_email: str, message_text: str, subject_data: str):
        message = email.message.EmailMessage()
        message["From"] = environment.SMTP_FROM
        message["To"] = receiver_email
        message["Subject"] = subject_data
        message.set_content(message_text)

        await aiosmtplib.send(
            message,
            hostname=environment.SMTP_HOSTNAME,
            port=465,
            username=environment.SMTP_USERNAME,
            password=environment.SMTP_PASSWORD,
            use_tls=True,
        )

    @staticmethod
    async def send_email_confirmation(receiver_email: str, code: str):
        html_message = f"""
        <h1>{environment.SERVICE_PUBLIC_NAME}: Регистрация</h1>
        <h2>Подтверждение почты</h2>
        <p>Ваш код подтверждения:</p>
        <p><b style="font-size:30px">{code}</b></p>
        """
        subject = f"{environment.SERVICE_PUBLIC_NAME}: Регистрация"

        await EmailService.send_email(receiver_email, html_message, subject)
