"""
Backend email Django qui envoie via l'API HTTP Brevo (v3).
Contourne le blocage SMTP de Railway.
"""
import requests
import logging
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'


class BrevoAPIBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        api_key = getattr(settings, 'BREVO_API_V3_KEY', '')
        if not api_key:
            logger.error("BREVO_API_V3_KEY manquante — email non envoye")
            return 0
        sent = 0
        for msg in email_messages:
            try:
                payload = {
                    'sender': self._parse_email(msg.from_email),
                    'to': [self._parse_email(addr) for addr in msg.to],
                    'subject': msg.subject,
                }
                # Contenu HTML ou texte
                if hasattr(msg, 'alternatives') and msg.alternatives:
                    for content, mimetype in msg.alternatives:
                        if mimetype == 'text/html':
                            payload['htmlContent'] = content
                            break
                if 'htmlContent' not in payload:
                    payload['htmlContent'] = msg.body.replace('\n', '<br>')
                payload['textContent'] = msg.body

                resp = requests.post(
                    BREVO_API_URL,
                    json=payload,
                    headers={
                        'api-key': api_key,
                        'Content-Type': 'application/json',
                    },
                    timeout=15,
                )
                if resp.status_code in (200, 201):
                    sent += 1
                    logger.info("Email envoye via Brevo API: %s", msg.subject)
                else:
                    logger.error("Brevo API erreur %s: %s", resp.status_code, resp.text)
            except Exception as e:
                logger.error("Brevo API exception: %s", e)
        return sent

    @staticmethod
    def _parse_email(email_str):
        """Convertit 'Nom <addr@x.com>' en dict {'name': 'Nom', 'email': 'addr@x.com'}."""
        if '<' in email_str and '>' in email_str:
            name = email_str[:email_str.index('<')].strip()
            email = email_str[email_str.index('<') + 1:email_str.index('>')]
            return {'name': name, 'email': email}
        return {'email': email_str}
