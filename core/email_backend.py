import os
import requests

from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):

    def send_messages(self, email_messages):

        if not email_messages:
            return 0

        api_key = os.getenv("RESEND_API_KEY")

        if not api_key:
            print("RESEND ERROR: RESEND_API_KEY is missing.")
            return 0

        sent_count = 0

        for message in email_messages:

            try:

                from_email = (
                    message.from_email
                    or os.getenv(
                        "DEFAULT_FROM_EMAIL",
                        "onboarding@resend.dev"
                    )
                )

                recipients = message.to

                if not recipients:
                    continue

                payload = {
                    "from": from_email,
                    "to": recipients,
                    "subject": message.subject,
                    "text": message.body,
                }

                response = requests.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=20,
                )

                if response.status_code in (200, 201):

                    sent_count += 1

                    print(
                        "RESEND EMAIL SENT:",
                        recipients
                    )

                else:

                    print(
                        "RESEND EMAIL ERROR:",
                        response.status_code,
                        response.text
                    )

            except Exception as e:

                print(
                    "RESEND EMAIL ERROR:",
                    repr(e)
                )

        return sent_count
