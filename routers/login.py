from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
from services.auth_service import AuthService  # Importa tu AuthService

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

router = APIRouter()
auth_service = AuthService()  # Instancia de AuthService


class LoginInput(BaseModel):
    correo: str
    contrasena: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    id_cliente: int
    nombre_cliente: str
    apellido_cliente: str
    direccion_cliente: str
    telefono_cliente: str
    correo_cliente: str


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginInput):
    logger.debug(f"Intento de login para el correo: {data.correo}")
    try:
        user = await auth_service.authenticate_user(
            correo_cliente=data.correo, contrasenia=data.contrasena
        )
        if user:
            access_token = auth_service._create_access_token(
                data={"sub": user["correo_cliente"]}
            )
            logger.info(f"Login exitoso para el correo: {data.correo}")
            return LoginResponse(
                access_token=access_token,
                id_cliente=user["id_cliente"],
                nombre_cliente=user["nombre_cliente"],
                apellido_cliente=user["apellido_cliente"],
                direccion_cliente=user["direccion_cliente"],
                telefono_cliente=user["telefono_cliente"],
                correo_cliente=user["correo_cliente"],
            )
        else:
            logger.warning(
                f"Intento de login fallido para el correo: {data.correo} - Credenciales inválidas."
            )
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
    except Exception as e:
        logger.error(
            f"Error durante el login para el correo: {data.correo} - {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))
