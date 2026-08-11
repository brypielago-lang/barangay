import resend

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):

    def send_messages(self, email_messages):

        if not email_messages:
            return 0

        if not settings.RESEND_API_KEY:
            raise ValueError(
                "RESEND_API_KEY is not configured."
            )

        resend.api_key = settings.RESEND_API_KEY

        sent_count = 0

        for message in email_messages:

            if not message.recipients():
                continue

            try:

                params = {
                    "from": settings.DEFAULT_FROM_EMAIL,
                    "to": message.recipients(),
                    "subject": message.subject,
                    "text": message.body,
                }

                resend.Emails.send(params)

                sent_count += 1

            except Exception as e:

                if not self.fail_silently:
                    raise

                print(
                    f"RESEND EMAIL ERROR: {e}"
                )

        return sent_count
