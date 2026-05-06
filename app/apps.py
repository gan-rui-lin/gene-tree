from django.apps import AppConfig as DjangoAppConfig


class GenealogyAppConfig(DjangoAppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app"
