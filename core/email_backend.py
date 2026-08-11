from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage
from django.conf import settings
import resend


class ResendEmailBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if not settings.RESEND_API_KEY:
            if not self.fail_silently:
                raise ValueError(
                    "RESEND_API_KEY is not configured."
                )
            return 0

        resend.api_key = settings.RESEND_API_KEY

        sent_count = 0

        for message in email_messages:

            if not message.recipients():
                continue

            try:
                resend.Emails.send({
                    "from": message.from_email,
                    "to": message.recipients(),
                    "subject": message.subject,
                    "text": message.body,
                })

                sent_count += 1

            except Exception:
                if not self.fail_silently:
                    raise

        return sent_count
