from fastapi import APIRouter, HTTPException, status
from models.login_model import (
    RegisterRequest,
)  # Asumo que RegisterRequest es tu modelo de entrada
from services.auth_service import AuthService  # Solo necesitas importar AuthService
from pydantic import BaseModel

# No necesitas timedelta ni create_access_token aquí directamente si AuthService lo maneja

router = APIRouter(prefix="/users", tags=["users"])
auth_service = AuthService()  # Instancia del servicio


# Modelo de respuesta base (sin token)
class UserBaseResponse(BaseModel):
    id_cliente: int
    nombre_cliente: str
    apellido_cliente: str
    direccion_cliente: str
    telefono_cliente: str
    correo_cliente: str


# Modelo de respuesta para el registro, incluyendo el token
class UserRegisterResponse(UserBaseResponse):
    access_token: str
    token_type: str = "bearer"  # Es buena práctica incluir el tipo de token


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserRegisterResponse,  # Usa el modelo que incluye el token
)
async def register_user(request: RegisterRequest):
    try:
        # auth_service.register_user ya devuelve un diccionario
        # que incluye el access_token y los datos del usuario.
        user_data_with_token = await auth_service.register_user(
            nombre_cliente=request.nombre_cliente,
            apellido_cliente=request.apellido_cliente,
            direccion_cliente=request.direccion_cliente,
            telefono_cliente=request.telefono_cliente,
            correo_cliente=request.correo_cliente,
            contrasenia=request.contrasenia,
        )

        if not user_data_with_token or "access_token" not in user_data_with_token:
            # Esto no debería suceder si auth_service.register_user funciona como se espera
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User registration succeeded but token was not generated.",
            )

        # Simplemente pasamos el diccionario completo al modelo de respuesta Pydantic.
        # Pydantic se encargará de validar y mapear los campos.
        return UserRegisterResponse(**user_data_with_token)

    except (
        HTTPException
    ) as http_exc:  # Re-lanzar HTTPExceptions para que FastAPI las maneje
        raise http_exc
    except Exception as e:
        # El logger en AuthService ya debería haber capturado detalles.
        # Aquí puedes devolver un mensaje más genérico al cliente.
        # O si el 'e' ya es un mensaje de error útil de AuthService, puedes usarlo.
        error_detail = (
            str(e) if str(e) else "An unexpected error occurred during registration."
        )
        if "Email already exists" in error_detail:  # Ejemplo de manejo específico
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=error_detail
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,  # O 500 si es más apropiado
            detail=error_detail,
        )
