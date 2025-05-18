import psycopg2
from database import get_connection
from passlib.hash import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
import logging

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
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id_cliente FROM tbl_cliente WHERE correo_cliente = %s",
                (correo_cliente,),
            )
            existing_user = cursor.fetchone()
            if existing_user:
                logger.warning(
                    f"Attempt to register with existing email: {correo_cliente}"
                )
                raise Exception("Email already exists")

            hashed_password = bcrypt.hash(contrasenia)

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
            logger.info(
                f"User registered successfully: ID {user_id}, Email: {correo_cliente}"
            )

            expires_delta_register = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token_register = self._create_access_token(
                data={"sub": str(user_id)}, expires_delta=expires_delta_register
            )

            return {
                "id_cliente": user_id,
                "nombre_cliente": nombre_cliente,
                "apellido_cliente": apellido_cliente,
                "direccion_cliente": direccion_cliente,
                "telefono_cliente": telefono_cliente,
                "correo_cliente": correo_cliente,
                "access_token": access_token_register,
            }
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            logger.error(
                f"DATABASE ERROR DURING USER REGISTRATION for {correo_cliente}: "
                f"Type: {type(e)}, Error: '{e}', Args: {e.args}, "
                f"pgcode: {getattr(e, 'pgcode', 'N/A')}, pgerror: {getattr(e, 'pgerror', 'N/A')}"
            )
            detail_message = f"A database error occurred during registration. pgerror: {getattr(e, 'pgerror', 'Details not available')}"
            raise Exception(detail_message)
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(
                f"GENERAL ERROR DURING USER REGISTRATION for {correo_cliente}: Type: {type(e)}, Error: '{e}'",
                exc_info=True,
            )
            raise Exception(f"An unexpected error occurred: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    async def authenticate_user(self, correo_cliente, contrasenia):

        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id_cliente, nombre_cliente, apellido_cliente, direccion_cliente, telefono_cliente, correo_cliente, contrasenia FROM tbl_cliente WHERE correo_cliente = %s AND estado_cliente = 'ACTIVO'",
                (correo_cliente,),
            )
            user_data = cursor.fetchone()

            if not user_data:
                logger.warning(
                    f"Client not found or inactive with email: {correo_cliente}"
                )
                return None

            (
                client_id,
                nombre_cliente_db,
                apellido_cliente_db,
                direccion_cliente_db,
                telefono_cliente_db,
                correo_cliente_db,
                stored_password_hash,
            ) = user_data

            if bcrypt.verify(contrasenia, stored_password_hash):
                logger.info(f"Password verified for client: {correo_cliente}")
                expires_delta_auth = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                access_token_auth = self._create_access_token(
                    data={"sub": str(client_id)}, expires_delta=expires_delta_auth
                )
                # logger.debug(f"Access token generated: {access_token_auth}")
                return {
                    "access_token": access_token_auth,
                    "id_cliente": client_id,
                    "nombre_cliente": nombre_cliente_db,
                    "apellido_cliente": apellido_cliente_db,
                    "direccion_cliente": direccion_cliente_db,
                    "telefono_cliente": telefono_cliente_db,
                    "correo_cliente": correo_cliente_db,
                }
            else:
                logger.warning(f"Incorrect password for client: {correo_cliente}")
                return None
        except psycopg2.Error as e:
            logger.error(
                f"DATABASE ERROR DURING AUTHENTICATION for {correo_cliente}: "
                f"Type: {type(e)}, Error: '{e}', Args: {e.args}, "
                f"pgcode: {getattr(e, 'pgcode', 'N/A')}, pgerror: {getattr(e, 'pgerror', 'N/A')}",
                exc_info=True,
            )
            raise Exception(
                f"Database error during authentication. pgerror: {getattr(e, 'pgerror', 'Details not available')}"
            )
        except Exception as e:
            logger.error(
                f"GENERAL ERROR DURING AUTHENTICATION for {correo_cliente}: Type: {type(e)}, Error: '{e}'",
                exc_info=True,
            )
            raise Exception(
                f"An unexpected error occurred during authentication: {str(e)}"
            )
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            # logger.debug(f"Database connection closed for authenticate_user attempt: {correo_cliente}")

    def _create_access_token(
        self,
        data: dict,
        expires_delta: timedelta,
    ):
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

        return encoded_jwt
