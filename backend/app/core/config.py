"""
Configuración central de NOVA (variables de entorno).
Nunca hardcodear credenciales: todo se lee de .env / entorno del contenedor.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "NOVA - Plataforma de Agentes Financieros"
    ENV: str = "local"
    DEBUG: bool = True

    # Base de datos (Postgres + pgvector para memoria RAG de agentes)
    DATABASE_URL: str = "postgresql+asyncpg://nova:nova@postgres:5432/nova"

    # Redis / Celery (cola de tareas asíncronas para picos de fin de mes)
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # Claude API (Agente Contable / Agente Receptor)
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-5"

    # OCR local para RUTs escaneados sin capa de texto (ver app/services/rut_extractor.py).
    # Tesseract se instala fuera de Program Files (sin permiso de escritura ahí)
    # — ver README para instalación. Vacío por defecto: pytesseract busca
    # "tesseract" en PATH, que es lo correcto tanto en el contenedor Linux
    # (imagen con tesseract-ocr instalado vía apt, sin Program Files) como en
    # un dev Windows que lo agregó al PATH. Solo hay que fijar esta variable
    # si el binario no está en PATH.
    TESSERACT_CMD: str = ""
    TESSDATA_PREFIX: str = ""

    # Multi-tenancy: header con el ID del tenant en cada request
    TENANT_HEADER: str = "X-Tenant-Id"

    # DIAN (consulta periódica simulada vía CSV; ver app/services/dian_portal_connector.py
    # para la integración real del catálogo de documentos recibidos)
    DIAN_SIMULATED: bool = True
    DIAN_MOCK_CSV_PATH: str = "app/services/dian_mock_facturas.csv"

    # Almacenamiento de PDFs subidos manualmente (representaciones gráficas de factura)
    PDF_STORAGE_DIR: str = "storage/facturas"

    # Seguridad / autenticación (ver app/core/security.py)
    JWT_SECRET: str = "CAMBIA_ESTO_EN_PRODUCCION"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRA_MINUTOS: int = 480
    COOKIE_SESION: str = "nova_session"
    COOKIE_SECURE: bool = False  # True en producción (HTTPS)

    # Origen exacto del frontend: con cookies httpOnly, CORS no puede usar "*"
    FRONTEND_ORIGIN: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
