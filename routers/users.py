from fastapi import APIRouter, HTTPException
from models.login_model import RegisterRequest
from services.auth_service import AuthService

router = APIRouter()
auth_service = AuthService()


@router.post("/register")
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
            "message": "User registered successfully",
            "user_id": user["id_cliente"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
