from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import DecodeError, ExpiredSignatureError
from config import SECRET_KEY, ALGORITHM
from database import get_connection  # Asegúrate de usar tu función correcta de conexión
from typing import Optional
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

security = HTTPBearer()


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = None):
    logger.debug(f"Verificando token: {credentials}")
    if credentials:
        token = credentials.credentials
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id is None:
                logger.warning("Token inválido: 'sub' no encontrado.")
                raise HTTPException(status_code=401, detail="Invalid token")
            # Aquí podrías buscar el usuario en la base de datos si necesitas más información
            # conn = get_connection()
            # cursor = conn.cursor(cursor_factory=RealDictCursor)
            # cursor.execute("SELECT * FROM tbl_cliente WHERE id_cliente = %s", (user_id,))
            # user = cursor.fetchone()
            # cursor.close()
            # conn.close()
            # if user is None:
            #     logger.warning(f"Usuario no encontrado con ID: {user_id}")
            #     raise HTTPException(status_code=404, detail="User not found")
            logger.debug(f"Usuario autenticado con ID: {user_id}")
            return {
                "user_id": user_id
            }  # Devuelve la información del usuario autenticado
        except ExpiredSignatureError:
            logger.warning("Token expirado.")
            raise HTTPException(status_code=401, detail="Token has expired")
        except DecodeError:
            logger.warning("Error al decodificar el token.")
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            logger.error(f"Error inesperado al verificar el token: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")
    else:
        logger.warning("No se proporcionó token.")
        raise HTTPException(status_code=401, detail="Not authenticated")
