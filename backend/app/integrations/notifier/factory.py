from app.core.settings import Settings
from app.integrations.notifier.base import Notifier
from app.integrations.notifier.telegram import TelegramNotifier
from app.integrations.notifier.twilio import TwilioNotifier


def make_real_notifier(settings: Settings) -> Notifier | None:
    """The configured real channel, or None for console-only."""
    if settings.notifier == "twilio":
        if (
            settings.twilio_account_sid
            and settings.twilio_auth_token
            and settings.twilio_from_number
        ):
            return TwilioNotifier(
                settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_from_number
            )
        return None
    if settings.notifier == "telegram" and settings.telegram_bot_token:
        return TelegramNotifier(settings.telegram_bot_token)
    return None
