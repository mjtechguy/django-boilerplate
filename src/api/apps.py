from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = "api"

    def ready(self):
        """Import signals when Django app is ready."""
        import api.signals  # noqa: F401
