from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import logging
from services.auth_service import AuthService

# from config import settings # Solo sería necesario si usaras settings.VARIABLE aquí directamente

# Configuración del logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

router = APIRouter(
    # prefix="/auth",  # Es buena práctica tener un prefijo para el router de autenticación
    tags=["Authentication - Clients"],  # Tag para la documentación de Swagger
)
auth_service = AuthService()


# Modelo Pydantic para la respuesta completa del login, incluyendo datos del usuario
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # Valor por defecto
    id_cliente: int
    nombre_cliente: str
    apellido_cliente: str
    direccion_cliente: str
    telefono_cliente: str
    correo_cliente: str
    role: str  # Añadido para que coincida con lo que devuelve auth_service


# El endpoint de login usualmente está en la raíz del router de autenticación, ej. /auth/token o /auth
# Si tu router se monta en main.py con un prefijo como /api, la ruta completa sería /api/auth
@router.post(
    "", response_model=LoginResponse
)  # Ruta POST a /auth (si el prefijo del router es /auth)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # form_data.username será el correo
    # form_data.password será la contraseña
    logger.info(f"Login attempt for email: {form_data.username}")
    try:
        # Asumimos que auth_service.authenticate_user devuelve un diccionario con todos los campos
        # necesarios para LoginResponse, incluyendo 'access_token', 'id_cliente', 'nombre_cliente', etc., y 'role'.
        user_data_with_token = await auth_service.authenticate_user(
            correo_cliente=form_data.username, contrasenia=form_data.password
        )

        if not user_data_with_token:
            logger.warning(
                f"Login failed for email: {form_data.username} - Invalid credentials."
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo o contraseña incorrectos",  # Mensaje más amigable
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verificar que todos los campos esperados por LoginResponse estén en user_data_with_token
        # Esto es importante si auth_service.authenticate_user no devuelve exactamente lo que LoginResponse espera.
        # El código de auth_service.py que te di sí devuelve 'role' y los demás campos.
        if (
            "access_token" not in user_data_with_token
            or "id_cliente" not in user_data_with_token
        ):
            logger.error(
                f"Authentication service did not return complete data for {form_data.username}."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="El servicio de autenticación no devolvió los datos completos.",
            )

        logger.info(f"Login successful for email: {form_data.username}")
        # Construir la respuesta directamente desde el diccionario devuelto por el servicio
        # si este ya coincide con la estructura de LoginResponse.
        return LoginResponse(**user_data_with_token)

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
            detail="Ocurrió un error interno en el servidor durante el inicio de sesión.",
        )


# Si tienes un endpoint de registro de clientes aquí, podría ser algo así:
# from models.auth_model import UserCreate # Asume que tienes este modelo Pydantic
# from models.user_model import UserResponse # Asume que tienes este modelo para la respuesta

# @router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
# async def register_client_user(user_create_data: UserCreate):
#     logger.info(f"Registration attempt for email: {user_create_data.correo_cliente}")
#     try:
#         created_user_response = await auth_service.register_user(
#             nombre_cliente=user_create_data.nombre_cliente,
#             apellido_cliente=user_create_data.apellido_cliente,
#             direccion_cliente=user_create_data.direccion_cliente,
#             telefono_cliente=user_create_data.telefono_cliente,
#             correo_cliente=user_create_data.correo_cliente,
#             contrasenia=user_create_data.contrasenia,
#         )
#         # Asumimos que auth_service.register_user devuelve un diccionario
#         # que coincide con el modelo UserResponse (incluyendo el token y datos del usuario)
#         return UserResponse(**created_user_response)
#     except ValueError as ve: # Captura el error de correo duplicado
#         logger.warning(f"Registration failed for {user_create_data.correo_cliente}: {str(ve)}")
#         raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ve))
#     except Exception as e:
#         logger.error(f"Error during registration for {user_create_data.correo_cliente}: {str(e)}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Ocurrió un error interno durante el registro."
#         )
