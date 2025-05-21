from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
    OAuth2PasswordBearer,
)
import jwt
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    PyJWTError,
)  # Añadir JWTError aquí también
from config import settings
from models.delivery_model import TokenDataRepartidor
from models.user_model import TokenDataUser
from typing import (
    Optional,
)  # Optional ya no es necesario para el 'role' en TokenDataUser si siempre está
import logging

# Configuración del logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)

# --- Configuración de Seguridad ---
user_security_scheme = HTTPBearer(auto_error=False)

oauth2_scheme_repartidor = OAuth2PasswordBearer(
    tokenUrl="/api/repartidores/login",  # Ajusta si tu prefijo o ruta de login es diferente
    description="Token de acceso OAuth2 para Repartidores",
)

# Opcional: Si quieres migrar get_current_user a OAuth2PasswordBearer también:
# oauth2_scheme_user = OAuth2PasswordBearer(
#     tokenUrl="/api/auth/login", # Ajusta a tu endpoint de login de usuarios (ej. /api/auth/login)
#     description="Token de acceso OAuth2 para Usuarios"
# )

# --- Funciones de Autenticación ---


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(user_security_scheme),
) -> TokenDataUser:
    """
    Decodifica el token JWT para usuarios, valida su contenido y devuelve los datos del usuario.
    """
    credentials_exception = (
        HTTPException(  # Definir una excepción común para reutilizar
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudieron validar las credenciales del usuario",
            headers={"WWW-Authenticate": "Bearer"},
        )
    )

    if credentials is None:
        logger.debug("get_current_user: No se proporcionaron credenciales.")
        raise credentials_exception  # Reutilizar

    token = credentials.credentials
    logger.debug(f"get_current_user: Verificando token de usuario: {token[:10]}...")

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        user_id_from_token: Optional[str] = payload.get("sub")
        role_from_token: Optional[str] = payload.get(
            "role"
        )  # Obtenemos el rol del token

        if (
            user_id_from_token is None or role_from_token is None
        ):  # <--- MODIFICADO: Verificar que el rol también exista
            logger.warning(
                "get_current_user: Token de usuario inválido - 'sub' o 'role' no encontrado."
            )
            raise credentials_exception  # Reutilizar

        # Opcional: Verificación más estricta del rol si es necesario
        if (
            role_from_token != "cliente"
        ):  # Asumiendo que el rol para usuarios siempre será "cliente"
            logger.warning(
                f"get_current_user: Token de usuario con rol inesperado: '{role_from_token}'. Se esperaba 'cliente'."
            )
            # Podrías lanzar una excepción de Forbidden si el rol es válido pero no el esperado para esta función
            # o una de Unauthorized si el rol es completamente desconocido.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,  # 403 Forbidden si el rol no es el esperado
                detail=f"Rol de usuario no autorizado: {role_from_token}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(
            f"get_current_user: Usuario autenticado con ID/sub: {user_id_from_token}, Rol: {role_from_token}"
        )
        # Ahora TokenDataUser espera 'role' como un campo requerido.
        return TokenDataUser(
            user_id=user_id_from_token, role=role_from_token
        )  # <--- MODIFICADO

    except ExpiredSignatureError:
        logger.warning("get_current_user: Token de usuario expirado.")
        # Reutilizar credentials_exception con un detalle más específico si se desea, o una nueva.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de usuario ha expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (
        PyJWTError
    ) as e:  # Usar JWTError para cubrir DecodeError y otros errores de JWT
        logger.warning(
            f"get_current_user: Error de JWT al decodificar token de usuario: {e}"
        )
        raise credentials_exception  # Reutilizar
    except Exception as e:
        logger.error(
            f"get_current_user: Error inesperado al verificar el token de usuario: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor durante la autenticación del usuario",
        )


async def get_current_repartidor(
    token: str = Depends(oauth2_scheme_repartidor),
) -> TokenDataRepartidor:
    """
    Decodifica el token JWT para repartidores, valida su contenido y devuelve los datos del repartidor.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales del repartidor",
        headers={"WWW-Authenticate": "Bearer"},
    )
    logger.debug(
        f"get_current_repartidor: Verificando token de repartidor: {token[:10]}..."
    )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        correo_repartidor: Optional[str] = payload.get("sub")
        id_repartidor_from_token: Optional[int] = payload.get("id_repartidor")
        role_from_token: Optional[str] = payload.get("role")

        # Verificar que todos los campos esperados estén presentes
        if (
            correo_repartidor is None
            or id_repartidor_from_token is None
            or role_from_token is None
        ):
            logger.warning(
                "get_current_repartidor: Token de repartidor inválido - falta 'sub' (correo), 'id_repartidor' o 'role'."
            )
            raise credentials_exception

        if role_from_token != "repartidor":
            logger.warning(
                f"get_current_repartidor: Token con rol incorrecto. Se esperaba 'repartidor', se obtuvo '{role_from_token}'."
            )
            # Podría ser un 403 Forbidden si el token es válido pero el rol no es el esperado para esta función
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol no autorizado para repartidor: {role_from_token}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_data = TokenDataRepartidor(
            correo_repartidor=correo_repartidor,
            id_repartidor=id_repartidor_from_token,
            role=role_from_token,  # Usar el rol del token
        )
        logger.info(
            f"get_current_repartidor: Repartidor autenticado: ID {id_repartidor_from_token}, Correo {correo_repartidor}, Rol: {role_from_token}"
        )

    except ExpiredSignatureError:
        logger.warning("get_current_repartidor: Token de repartidor expirado.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de repartidor ha expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except PyJWTError as e:
        logger.warning(
            f"get_current_repartidor: Error de JWT al decodificar token de repartidor: {e}"
        )
        raise credentials_exception
    except Exception as e:
        logger.error(
            f"get_current_repartidor: Error inesperado al verificar el token de repartidor: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor durante la autenticación del repartidor",
        )

    # La verificación opcional en DB sigue siendo válida aquí si la necesitas.

    return token_data
