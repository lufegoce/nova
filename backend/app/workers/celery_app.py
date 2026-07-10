"""
Configuración de Celery: cola de tareas asíncronas para trabajo pesado
(ej. procesar 1000 facturas en un pico de fin de mes) sin bloquear la API.
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "nova",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Bogota",
    enable_utc=True,
)

# Consulta periódica al conector DIAN simulado (cada 5 minutos)
celery_app.conf.beat_schedule = {
    "consultar-dian-periodicamente": {
        "task": "app.workers.tasks.consultar_dian_task",
        "schedule": crontab(minute="*/5"),
    },
    "escanear-seguridad-periodicamente": {
        "task": "app.workers.tasks.escanear_seguridad_task",
        "schedule": crontab(minute="*/10"),
    },
}
