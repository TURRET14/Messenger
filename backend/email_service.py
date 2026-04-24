import aiosmtplib
import aiosmtplib.errors
import asyncio
import email.message
import fastapi
import socket

from backend import environment
from backend.routers.errors import ErrorRegistry


class EmailService:
    _ACCENT = "#3b5bdb"
    _TEXT = "#1f2940"
    _MUTED = "#5c6478"
    _BORDER = "#d8dce6"
    _SURFACE = "#ffffff"
    _SURFACE_ALT = "#f4f7ff"

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
    def _build_code_email_html(tag: str, title: str, lead: str, code: str, hint: str) -> str:
        service_name = environment.SERVICE_PUBLIC_NAME
        return f"""
        <!doctype html>
        <html lang="ru">
          <body style="margin:0;padding:0;background:{EmailService._SURFACE_ALT};font-family:Segoe UI,Arial,sans-serif;color:{EmailService._TEXT};">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:{EmailService._SURFACE_ALT};padding:32px 16px;">
              <tr>
                <td align="center">
                  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:{EmailService._SURFACE};border:1px solid {EmailService._BORDER};border-radius:20px;overflow:hidden;box-shadow:0 12px 40px rgba(20,31,56,.08);">
                    <tr>
                      <td style="padding:28px 32px 20px;background:linear-gradient(135deg,{EmailService._SURFACE_ALT} 0%,#ffffff 100%);border-bottom:1px solid {EmailService._BORDER};">
                        <div style="display:inline-block;padding:6px 10px;border-radius:999px;background:rgba(59,91,219,.1);color:{EmailService._ACCENT};font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;">{tag}</div>
                        <h1 style="margin:16px 0 8px;font-size:28px;line-height:1.2;">{service_name}</h1>
                        <p style="margin:0;font-size:15px;line-height:1.6;color:{EmailService._MUTED};">{lead}</p>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:28px 32px 32px;">
                        <h2 style="margin:0 0 12px;font-size:22px;line-height:1.3;">{title}</h2>
                        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:{EmailService._MUTED};">
                          Используйте этот код в приложении. Он действует ограниченное время и подходит только для одного подтверждения.
                        </p>
                        <div style="margin:0 0 24px;padding:18px 20px;border-radius:16px;border:1px solid {EmailService._BORDER};background:{EmailService._SURFACE_ALT};text-align:center;">
                          <div style="font-size:13px;line-height:1.5;color:{EmailService._MUTED};margin-bottom:10px;">Код подтверждения</div>
                          <div style="font-size:34px;line-height:1;font-weight:800;letter-spacing:.22em;color:{EmailService._ACCENT};">{code}</div>
                        </div>
                        <p style="margin:0;font-size:14px;line-height:1.7;color:{EmailService._MUTED};">{hint}</p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </body>
        </html>
        """


    @staticmethod
    async def send_registration_confirmation(receiver_email: str, code: str):
        subject = f"{environment.SERVICE_PUBLIC_NAME}: подтверждение регистрации"
        html_message = EmailService._build_code_email_html(
            tag = "Регистрация",
            title = "Подтвердите адрес электронной почты",
            lead = "Мы получили запрос на создание нового аккаунта.",
            code = code,
            hint = "Если вы не регистрировались в сервисе, просто проигнорируйте это письмо.",
        )
        await EmailService.send_email(receiver_email, html_message, subject)


    @staticmethod
    async def send_email_change_confirmation(receiver_email: str, code: str):
        subject = f"{environment.SERVICE_PUBLIC_NAME}: подтверждение новой почты"
        html_message = EmailService._build_code_email_html(
            tag = "Смена почты",
            title = "Подтвердите новый адрес электронной почты",
            lead = "Мы получили запрос на изменение адреса электронной почты в профиле.",
            code = code,
            hint = "Если вы не меняли адрес, не вводите код и проверьте безопасность аккаунта.",
        )
        await EmailService.send_email(receiver_email, html_message, subject)


    @staticmethod
    async def send_password_reset_code(receiver_email: str, code: str):
        subject = f"{environment.SERVICE_PUBLIC_NAME}: восстановление пароля"
        html_message = EmailService._build_code_email_html(
            tag = "Восстановление",
            title = "Сбросьте пароль от аккаунта",
            lead = "Мы получили запрос на восстановление доступа к вашему аккаунту.",
            code = code,
            hint = "Если вы не запрашивали сброс пароля, просто проигнорируйте письмо.",
        )
        await EmailService.send_email(receiver_email, html_message, subject)
