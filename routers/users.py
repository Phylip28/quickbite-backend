# routers/users.py
from fastapi import APIRouter, HTTPException, status
from models.login_model import RegisterRequest
from services.auth_service import AuthService
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["users"])
auth_service = AuthService()


class UserResponse(BaseModel):
    id_cliente: int
    nombre_cliente: str
    apellido_cliente: str
    direccion_cliente: str
    telefono_cliente: str
    correo_cliente: str


@router.post(
    "/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse
)
async def register_user(request: RegisterRequest):
    try:
        user = await auth_service.register_user(
            nombre_cliente=request.nombre_cliente,
            apellido_cliente=request.apellido_cliente,
            direccion_cliente=request.direccion_cliente,
            telefono_cliente=request.telefono_cliente,
            correo_cliente=request.correo_cliente,
            contrasenia=request.contrasenia,
        )
        return UserResponse(
            id_cliente=user["id_cliente"],
            nombre_cliente=user["nombre_cliente"],
            apellido_cliente=user["apellido_cliente"],
            direccion_cliente=user["direccion_cliente"],
            telefono_cliente=user["telefono_cliente"],
            correo_cliente=user["correo_cliente"],
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
