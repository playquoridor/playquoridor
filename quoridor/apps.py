from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError


class QuoridorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'quoridor'

    def ready(self):
        from game.models import UserDetails

        # Resetting online users
        try:
            UserDetails.objects.update(online=0)
        except (OperationalError, ProgrammingError):
            pass  # UserDetails does not exist
