from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import (
    OAuth2PasswordRequestForm,
)  # Para usar el flujo estándar de OAuth2
from pydantic import BaseModel
import logging
from services.auth_service import AuthService
from config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
)  # Importar para la duración del token si es necesario aquí
from datetime import timedelta

# Configuración del logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Cambiado a INFO para menos verbosidad en producción

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

router = APIRouter(tags=["login"])  # Añadir tags es una buena práctica
auth_service = AuthService()


# Modelo Pydantic para la respuesta del token (estándar)
class Token(BaseModel):
    access_token: str
    token_type: str


# Modelo Pydantic para la respuesta completa del login, incluyendo datos del usuario
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    id_cliente: int
    nombre_cliente: str
    apellido_cliente: str
    direccion_cliente: str
    telefono_cliente: str
    correo_cliente: str


# Usar OAuth2PasswordRequestForm para el cuerpo de la solicitud es más estándar para login
# El endpoint de login usualmente está en la raíz del router de autenticación, ej. /auth o /token
@router.post(
    "", response_model=LoginResponse
)  # Ruta POST a / (relativo al prefijo del router en main.py)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # form_data.username será el correo
    # form_data.password será la contraseña
    logger.info(f"Login attempt for email: {form_data.username}")
    try:
        user_data_with_token = await auth_service.authenticate_user(
            correo_cliente=form_data.username, contrasenia=form_data.password
        )

        if not user_data_with_token:
            logger.warning(
                f"Login failed for email: {form_data.username} - Invalid credentials."
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # auth_service.authenticate_user ya debería devolver el token y los datos del usuario
        # según la última versión de auth_service.py
        if "access_token" not in user_data_with_token:
            logger.error(
                f"Authentication service did not return an access token for {form_data.username}."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service failed to provide an access token.",
            )

        logger.info(f"Login successful for email: {form_data.username}")
        return LoginResponse(
            access_token=user_data_with_token["access_token"],
            token_type="bearer",  # Ya está por defecto en el modelo, pero se puede ser explícito
            id_cliente=user_data_with_token["id_cliente"],
            nombre_cliente=user_data_with_token["nombre_cliente"],
            apellido_cliente=user_data_with_token["apellido_cliente"],
            direccion_cliente=user_data_with_token["direccion_cliente"],
            telefono_cliente=user_data_with_token["telefono_cliente"],
            correo_cliente=user_data_with_token["correo_cliente"],
        )
    except HTTPException as http_exc:
        # Re-lanzar excepciones HTTP conocidas para que FastAPI las maneje
        raise http_exc
    except Exception as e:
        logger.error(
            f"Error during login for email: {form_data.username} - {str(e)}",
            exc_info=True,  # Incluye el traceback en los logs del servidor
        )
        # Para el cliente, devuelve un error genérico
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during login.",
        )
