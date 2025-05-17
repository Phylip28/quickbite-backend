# routers/users.py
from fastapi import APIRouter, HTTPException, status
from models.login_model import RegisterRequest
from services.auth_service import AuthService

router = APIRouter(prefix="/users", tags=["users"])
auth_service = AuthService()


@router.post("/register", status_code=status.HTTP_201_CREATED)
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
        return {
            "message": "Usuario registrado exitosamente",
            "user_id": user["id_cliente"],
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
