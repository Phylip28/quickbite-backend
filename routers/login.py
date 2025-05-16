from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from database import get_connection
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

router = APIRouter()


class LoginInput(BaseModel):
    correo: str
    contrasena: str


@router.post("/login")
def login(data: LoginInput):
    logger.debug(f"Intento de login para el correo: {data.correo}")
    try:
        conn = get_connection()
        logger.debug("Conexión a la base de datos exitosa.")
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        logger.debug("Cursor creado.")
        cursor.execute(
            "SELECT * FROM tbl_cliente WHERE correo_cliente = %s AND contrasenia = %s",
            (data.correo, data.contrasena),
        )
        logger.debug("Consulta SQL ejecutada.")
        cliente = cursor.fetchone()
        logger.debug(f"Resultado de la consulta: {cliente}")
        cursor.close()
        conn.close()
        logger.debug("Cursor y conexión cerrados.")

        if cliente:
            logger.info(f"Login exitoso para el cliente: {cliente['correo_cliente']}")
            return {"mensaje": "Login exitoso", "cliente": cliente}
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
