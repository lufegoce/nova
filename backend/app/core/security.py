"""
Hashing de contraseñas y emisión/verificación de JWT de sesión.

El JWT viaja en una cookie httpOnly (ver app/api/routes/auth.py), nunca en
localStorage, para reducir el riesgo de robo del token vía XSS. Diseñado para
poder insertar un paso de verificación 2FA entre el login y la emisión del
JWT final sin cambiar el resto de la app (ver TODO en login_empresa/login_contador).
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()


def hash_password(password_plano: str) -> str:
    return bcrypt.hashpw(password_plano.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password_plano: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password_plano.encode("utf-8"), password_hash.encode("utf-8"))


def crear_token_sesion(claims: dict[str, Any]) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRA_MINUTOS)
    payload = {**claims, "exp": expira}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


class TokenInvalidoError(Exception):
    pass


def decodificar_token_sesion(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise TokenInvalidoError(str(exc)) from exc
