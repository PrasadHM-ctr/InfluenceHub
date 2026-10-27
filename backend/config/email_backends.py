"""Amazon SES email backend (optional).

Activated ONLY when USE_SES=true. When disabled (the default) Django uses its
console/smtp backends, so local development sends $0 of AWS traffic.

Design notes (cost + security):
- Uses the boto3 library that is already a project dependency — no extra package.
- Only calls SES ``SendEmail`` (transactional messages: verification codes and
  resends). Nothing here supports bulk/marketing sending.
- Credentials come exclusively from the normal AWS credential chain
  (environment variables / ~/.aws), never from source code.
- A delivery failure is logged; signup itself never breaks because of email.
"""

import logging

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class SESEmailBackend(BaseEmailBackend):
    """Send Django EmailMessage objects through Amazon SES v2."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        # Imported lazily so environments without boto3 still boot when SES is off.
        import boto3

        client = boto3.client(
            "sesv2",
            region_name=getattr(settings, "AWS_SES_REGION_NAME", "us-east-1"),
        )

        sent = 0
        for message in email_messages:
            try:
                destination: dict = {"ToAddresses": list(message.to)}
                if message.cc:
                    destination["CcAddresses"] = list(message.cc)
                if message.bcc:
                    destination["BccAddresses"] = list(message.bcc)

                payload = {
                    "FromEmailAddress": str(message.from_email),
                    "Destination": destination,
                    "Content": {"Simple": self._simple_content(message)},
                }
                reply_to = [str(address) for address in message.reply_to]
                if reply_to:
                    payload["ReplyToAddresses"] = reply_to

                client.send_email(**payload)
                sent += 1
            except Exception:
                logger.exception("SES delivery failed for %s", list(message.to))
                if not self.fail_silently:
                    raise
        return sent

    @staticmethod
    def _simple_content(message) -> dict:
        body: dict = {"Text": {"Data": message.body, "Charset": "UTF-8"}}
        for alternative_content, alternative_type in getattr(message, "alternatives", []) or []:
            if alternative_type == "text/html":
                body["Html"] = {"Data": alternative_content, "Charset": "UTF-8"}
                break
        return {"Subject": {"Data": message.subject, "Charset": "UTF-8"}, "Body": body}
