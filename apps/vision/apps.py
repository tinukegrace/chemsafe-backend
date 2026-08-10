from django.apps import AppConfig


class VisionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.vision"

    def ready(self):
        from django.conf import settings

        if getattr(settings, "TESSERACT_CMD", None):
            import pytesseract

            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
