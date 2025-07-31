from allauth.account import app_settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_email, user_field

try:
    from allauth.mfa.models import Authenticator

    def user_has_valid_totp_device(user) -> bool:
        if not user.is_authenticated:
            return False
        return user.authenticator_set.filter(type=Authenticator.Type.TOTP).exists()

except ImportError:
    # allauth.mfa is not installed
    def user_has_valid_totp_device(user) -> bool:
        return False


class AccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter:
    - Uses email as username
    - Disables public sign-ups
    """

    def populate_username(self, request, user):
        """
        Override default to set username as the user's email.
        """
        user_field(user, app_settings.USER_MODEL_USERNAME_FIELD, user_email(user))

    def is_open_for_signup(self, request):
        """
        Disable public sign-ups. Only allow account creation through admin/programmatically.
        """
        return False
