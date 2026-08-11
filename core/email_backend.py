import os

import resend

from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail import EmailMessage


class ResendEmailBackend(BaseEmailBackend):

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)

        self.api_key = os.getenv("RESEND_API_KEY")

        if self.api_key:
            resend.api_key = self.api_key

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent_count = 0

        for email_message in email_messages:

            try:
                if self._send(email_message):
                    sent_count += 1

            except Exception as e:

                if not self.fail_silently:
                    raise

                print(
                    f"RESEND EMAIL ERROR: {type(e).__name__}: {e}"
                )

        return sent_count

    def _send(self, email_message: EmailMessage):

        if not self.api_key:
            raise ValueError(
                "RESEND_API_KEY is not configured."
            )

        recipients = email_message.to

        if not recipients:
            return False

        from_email = (
            email_message.from_email
            or os.getenv(
                "DEFAULT_FROM_EMAIL",
                "onboarding@resend.dev"
            )
        )

        params = {
            "from": from_email,
            "to": recipients,
            "subject": email_message.subject,
            "text": email_message.body,
        }

        if email_message.cc:
            params["cc"] = email_message.cc

        if email_message.bcc:
            params["bcc"] = email_message.bcc

        resend.Emails.send(params)

        print(
            "RESEND EMAIL SENT TO: "
            + ", ".join(recipients)
        )

        return True
