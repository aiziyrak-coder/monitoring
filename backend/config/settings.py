"""
Django settings — ClinicMonitoring backend.
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

_DEFAULT_DEV_SECRET = "dev-only-change-in-production-clinic-monitoring-unsafe"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", _DEFAULT_DEV_SECRET)

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() in ("1", "true", "yes")

if not DEBUG and SECRET_KEY == _DEFAULT_DEV_SECRET:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is required when DEBUG=false (default development secret is not allowed)."
    )

if not DEBUG and len(SECRET_KEY) < 32:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY juda qisqa (kamida 32 belgi; tavsiya: 50+ tasodifiy)."
    )

ALLOWED_HOSTS = list(
    dict.fromkeys(
        h.strip()
        for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
        if h.strip()
    )
)

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173,https://clinicmonitoring.ziyrak.org,https://clinicmonitoringapi.ziyrak.org",
    ).split(",")
    if o.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "corsheaders",
    "monitoring",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        # HL7 thread + ASGI bir vaqtda — lock kutish (default 5s yetarli emas bo‘lishi mumkin)
        "OPTIONS": {
            "timeout": 30,
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOW_ALL_ORIGINS = DEBUG
# Production domenlar defaultda (env bo‘lmasa ham SPA + API kross-domen ishlashi uchun)
_CORS_DEFAULT = (
    "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:3000,http://localhost:3000,"
    "https://clinicmonitoring.ziyrak.org,https://clinicmonitoringapi.ziyrak.org"
)
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ALLOWED_ORIGINS", _CORS_DEFAULT).split(",")
    if o.strip()
]
if not DEBUG:
    CORS_ALLOW_ALL_ORIGINS = False
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Mindray HL7 MLLP (monitor «Server IP» / «Port»)
HL7_LISTENER_ENABLED = os.environ.get("HL7_LISTENER_ENABLED", "1").lower() in (
    "1",
    "true",
    "yes",
)
HL7_LISTEN_HOST = os.environ.get("HL7_LISTEN_HOST", "0.0.0.0")
try:
    _hl7_port = int(os.environ.get("HL7_LISTEN_PORT", "6006"))
except ValueError as e:
    raise ImproperlyConfigured("HL7_LISTEN_PORT butun son bo‘lishi kerak.") from e
if not (1 <= _hl7_port <= 65535):
    raise ImproperlyConfigured("HL7_LISTEN_PORT 1–65535 orasida bo‘lishi kerak.")
HL7_LISTEN_PORT = _hl7_port
# HL7 klienti yuborgan yig‘ma bufer (DoS / xotira himoyasi)
try:
    _hl7_buf = int(os.environ.get("HL7_MAX_BUFFER_BYTES", str(2 * 1024 * 1024)))
except ValueError as e:
    raise ImproperlyConfigured("HL7_MAX_BUFFER_BYTES butun son bo‘lishi kerak.") from e
HL7_MAX_BUFFER_BYTES = max(65_536, min(_hl7_buf, 50 * 1024 * 1024))

# REST orqali vital yuborish (faqat POST .../vitals). Bo'sh = tekshiruv yo'q (Mindray mosligi).
DEVICE_INGEST_TOKEN = (os.environ.get("DEVICE_INGEST_TOKEN") or "").strip()

# monitoring.* (HL7 MLLP va boshqalar) — aks holda faqat uvicorn qatorlari journalctl da ko‘rinadi
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "monitoring": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Shu vaqtdan oshsa qurilma API bo‘yicha «oflayn» (vitallar kelmayapti)
try:
    _silence = int(os.environ.get("DEVICE_ONLINE_SILENCE_SEC", "120"))
except ValueError as e:
    raise ImproperlyConfigured("DEVICE_ONLINE_SILENCE_SEC butun son bo‘lishi kerak.") from e
DEVICE_ONLINE_SILENCE_SEC = max(30, min(_silence, 86_400))

# HL7: bitta qurilma bo'lsa, har qanday IP dan kelgan HL7 xabarni o'sha qurilmaga yo'naltirish.
# Bu NAT/router orqasidagi bitta monitor uchun foydali.
HL7_NAT_SINGLE_DEVICE_FALLBACK = os.environ.get(
    "HL7_NAT_SINGLE_DEVICE_FALLBACK", "true"
).lower() in ("1", "true", "yes")

# TCP ulanish kelganda monitora HL7 QRY^Q01 yuborib vitals so'rash (Creative K12 uchun)
HL7_SEND_QRY_ON_CONNECT = os.environ.get("HL7_SEND_QRY_ON_CONNECT", "true").lower() in (
    "1", "true", "yes"
)

# Agar monitor QRY ga javob bermasa, har N sekundda qayta so'raymiz (ulanish davomida)
try:
    _qry_interval = int(os.environ.get("HL7_QRY_INTERVAL_SEC", "30"))
except ValueError:
    _qry_interval = 30
HL7_QRY_INTERVAL_SEC = max(10, min(_qry_interval, 300))

# Taqdimot: 8 ta demo bemorda vitallarni yengil o'zgartirish (seed_demo_patients dan keyin)
DEMO_VITALS_ENABLED = os.environ.get("DEMO_VITALS_ENABLED", "false").lower() in (
    "1",
    "true",
    "yes",
)
try:
    _demo_iv = float(os.environ.get("DEMO_VITALS_INTERVAL_SEC", "5"))
except ValueError as e:
    raise ImproperlyConfigured("DEMO_VITALS_INTERVAL_SEC haqiqiy son bo'lishi kerak.") from e
DEMO_VITALS_INTERVAL_SEC = max(2.0, min(_demo_iv, 120.0))

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S.%fZ",
}
