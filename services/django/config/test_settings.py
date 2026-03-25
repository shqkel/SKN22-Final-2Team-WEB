from .settings import *  # noqa: F403,F401

# PostgreSQL 필수 (ArrayField, VectorField, SearchVectorField 사용)
# docker compose 로 postgres 실행 후 테스트:
#   cd infra && docker compose up -d postgres
#   cd ../services/django && python manage.py test --settings=config.test_settings
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DATABASES["default"].get("NAME", "tailtalk"),  # noqa: F405
        "USER": DATABASES["default"].get("USER", "tailtalk"),  # noqa: F405
        "PASSWORD": DATABASES["default"].get("PASSWORD", "changeme"),  # noqa: F405
        "HOST": DATABASES["default"].get("HOST", "localhost"),  # noqa: F405
        "PORT": DATABASES["default"].get("PORT", "5432"),  # noqa: F405
        "TEST": {
            "NAME": "test_tailtalk",
        },
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


# pgvector extension을 테스트 DB 생성 시 자동 설치
from django.db.backends.signals import connection_created


def _install_pgvector(sender, connection, **kwargs):
    with connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")


connection_created.connect(_install_pgvector)
