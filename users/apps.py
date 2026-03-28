from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        # Charge les signaux (post_save pour créer le Profil automatiquement)
        import users.models  # noqa: F401
