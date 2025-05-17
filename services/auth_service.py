import psycopg2
from database import get_connection  # Asegúrate de usar tu función correcta de conexión
from passlib.hash import bcrypt
import jwt
from datetime import datetime, timedelta
from config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)  # Asegúrate de la sintaxis correcta
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class AuthService:
    async def register_user(
        self,
        nombre_cliente,
        apellido_cliente,
        direccion_cliente,
        telefono_cliente,
        correo_cliente,
        contrasenia,
    ):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Verificar si el correo ya existe
            cursor.execute(
                "SELECT id_cliente FROM tbl_cliente WHERE correo_cliente = %s",
                (correo_cliente,),
            )
            existing_user = cursor.fetchone()
            if existing_user:
                raise Exception("Email already exists")

            # Hashear la contraseña
            hashed_password = bcrypt.hash(contrasenia)

            # Insertar el nuevo usuario en la base de datos
            cursor.execute(
                "INSERT INTO tbl_cliente (nombre_cliente, apellido_cliente, direccion_cliente, telefono_cliente, correo_cliente, contrasenia, fecha_registro_cliente) VALUES (%s, %s, %s, %s, %s, %s, NOW()) RETURNING id_cliente",
                (
                    nombre_cliente,
                    apellido_cliente,
                    direccion_cliente,
                    telefono_cliente,
                    correo_cliente,
                    hashed_password,
                ),
            )
            user_id = cursor.fetchone()[0]
            conn.commit()
            return {"id_cliente": user_id, "correo_cliente": correo_cliente}
        except psycopg2.Error as e:
            conn.rollback()
            raise Exception(f"Database error: {e}")
        finally:
            cursor.close()
            conn.close()

    async def authenticate_user(self, correo_cliente, contrasenia):
        logger.debug(f"Autenticando usuario con correo: {correo_cliente}")
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Buscar al cliente por correo electrónico Y que esté ACTIVO
            cursor.execute(
                "SELECT id_cliente, nombre_cliente, apellido_cliente, direccion_cliente, telefono_cliente, correo_cliente, contrasenia FROM tbl_cliente WHERE correo_cliente = %s AND estado_cliente = 'ACTIVO'",
                (correo_cliente,),
            )
            user_data = cursor.fetchone()
            cursor.close()
            conn.close()
            logger.debug(f"Resultado de la búsqueda del cliente: {user_data}")

            if not user_data:
                logger.warning(
                    f"Cliente no encontrado o inactivo con el correo: {correo_cliente}"
                )
                return None

            (
                client_id,
                nombre_cliente,
                apellido_cliente,
                direccion_cliente,
                telefono_cliente,
                correo_cliente_db,
                stored_password_hash,
            ) = user_data

            # Verificar la contraseña
            if bcrypt.verify(contrasenia, stored_password_hash):
                logger.info(f"Contraseña verificada para el cliente: {correo_cliente}")
                # Generar el token de acceso
                access_token = self._create_access_token(data={"sub": str(client_id)})
                logger.debug(f"Token de acceso generado: {access_token}")
                return {
                    "access_token": access_token,
                    "id_cliente": client_id,
                    "nombre_cliente": nombre_cliente,
                    "apellido_cliente": apellido_cliente,
                    "direccion_cliente": direccion_cliente,
                    "telefono_cliente": telefono_cliente,
                    "correo_cliente": correo_cliente_db,
                }
            else:
                logger.warning(
                    f"Contraseña incorrecta para el cliente: {correo_cliente}"
                )
                return None
        except psycopg2.Error as e:
            logger.error(
                f"Error de base de datos durante la autenticación: {e}", exc_info=True
            )
            raise Exception(f"Database error: {e}")
        finally:
            if conn:
                conn.close()

    def _create_access_token(
        self,
        data: dict,
        expires_delta: timedelta = timedelta(minutes=15),  # Valor por defecto
    ):
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
