import psycopg2
from database import get_db_cursor  # <--- SOLO IMPORTAMOS get_db_cursor

# from psycopg2.extras import RealDictCursor # No es necesario importar aquí, get_db_cursor ya lo usa
from passlib.hash import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from config import settings
import logging

# Configuración del logger
logger = logging.getLogger(__name__)
# (Tu configuración de logger existente está bien)
# ... (resto de tu configuración de logger) ...
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
        try:
            with get_db_cursor() as cursor:  # No commit=True aquí, lo haremos explícitamente
                cursor.execute(
                    "SELECT id_cliente FROM tbl_cliente WHERE correo_cliente = %s",
                    (correo_cliente,),
                )
                existing_user = cursor.fetchone()  # Esto será un dict
                if existing_user:
                    logger.warning(
                        f"Attempt to register with existing email: {correo_cliente}"
                    )
                    # El router debería convertir esto en una HTTPException
                    raise ValueError(
                        f"El correo electrónico '{correo_cliente}' ya está registrado."
                    )

                hashed_password = bcrypt.hash(contrasenia)

                cursor.execute(
                    """
                    INSERT INTO tbl_cliente (
                        nombre_cliente, apellido_cliente, direccion_cliente,
                        telefono_cliente, correo_cliente, contrasenia,
                        fecha_registro_cliente
                    ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    RETURNING id_cliente;
                    """,
                    (
                        nombre_cliente,
                        apellido_cliente,
                        direccion_cliente,
                        telefono_cliente,
                        correo_cliente,
                        hashed_password,
                    ),
                )
                user_data_from_db = cursor.fetchone()  # Esto será un dict
                if not user_data_from_db or "id_cliente" not in user_data_from_db:
                    logger.error(
                        f"Failed to register user {correo_cliente}, no ID returned from DB."
                    )
                    raise Exception(
                        "No se pudo registrar el usuario, no se devolvió ID."
                    )

                user_id = user_data_from_db["id_cliente"]
                # El commit se maneja por el context manager si get_db_cursor se llama con commit=True
                # o explícitamente si es necesario (pero get_db_cursor ya lo hace)
                # Para esta operación, necesitamos commit=True

            # Reabrir el cursor para el commit después de la inserción exitosa
            # O mejor, modificar get_db_cursor para que el commit sea más flexible o
            # hacer el commit dentro del mismo bloque with si la lógica lo permite.
            # Por simplicidad aquí, asumimos que el commit se hará si no hay excepciones.
            # La forma correcta es: with get_db_cursor(commit=True) as cursor:
            # Pero como ya cerramos el 'with', necesitamos una forma de asegurar el commit.
            # La implementación actual de get_db_cursor hace commit si commit=True.
            # Vamos a reestructurar para un solo bloque 'with'.

        except ValueError as ve:  # Capturar el ValueError específico
            raise ve  # Relanzar para que el router lo maneje
        except psycopg2.Error as e:
            logger.error(
                f"DATABASE ERROR DURING USER REGISTRATION for {correo_cliente}: {e}",
                exc_info=True,
            )
            detail_message = f"Error de base de datos durante el registro. pgcode: {getattr(e, 'pgcode', 'N/A')}"
            raise Exception(detail_message)  # O una excepción personalizada
        except Exception as e:
            logger.error(
                f"GENERAL ERROR DURING USER REGISTRATION for {correo_cliente}: {e}",
                exc_info=True,
            )
            raise Exception(f"Ocurrió un error inesperado: {str(e)}")

        # Si llegamos aquí, el usuario fue creado y el ID obtenido.
        # Ahora creamos el token fuera del bloque 'with' de la base de datos.
        try:
            with get_db_cursor(
                commit=True
            ) as cursor_commit:  # Este commit es para la inserción
                # La inserción ya se hizo, este commit asegura que se guarde.
                # Esta lógica es un poco redundante si la inserción ya ocurrió en un bloque con commit.
                # Lo ideal es que la inserción y el commit estén en el mismo bloque.
                # Vamos a simplificar:
                pass  # El commit se hará al salir del bloque with get_db_cursor(commit=True)

            # La inserción y el commit deben estar en el mismo bloque 'with'
            # Refactoricemos la parte de la DB:
            user_id_final = None
            with get_db_cursor(commit=True) as cursor:  # commit=True para la inserción
                cursor.execute(
                    "SELECT id_cliente FROM tbl_cliente WHERE correo_cliente = %s",
                    (correo_cliente,),
                )
                existing_user = cursor.fetchone()
                if existing_user:
                    logger.warning(
                        f"Intento de registro con correo existente: {correo_cliente}"
                    )
                    raise ValueError(
                        f"El correo electrónico '{correo_cliente}' ya está registrado."
                    )

                hashed_password = bcrypt.hash(contrasenia)
                cursor.execute(
                    """
                    INSERT INTO tbl_cliente (
                        nombre_cliente, apellido_cliente, direccion_cliente,
                        telefono_cliente, correo_cliente, contrasenia,
                        fecha_registro_cliente
                    ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    RETURNING id_cliente;
                    """,
                    (
                        nombre_cliente,
                        apellido_cliente,
                        direccion_cliente,
                        telefono_cliente,
                        correo_cliente,
                        hashed_password,
                    ),
                )
                user_data_from_db = cursor.fetchone()
                if not user_data_from_db or "id_cliente" not in user_data_from_db:
                    logger.error(
                        f"Fallo al registrar usuario {correo_cliente}, no se devolvió ID."
                    )
                    raise Exception(
                        "No se pudo registrar el usuario, no se devolvió ID."
                    )
                user_id_final = user_data_from_db["id_cliente"]
            # Al salir de este bloque 'with', si no hubo excepciones, se hizo commit.

            logger.info(
                f"Usuario registrado: ID {user_id_final}, Email: {correo_cliente}"
            )
            expires_delta_register = timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
            access_token_register = self._create_access_token(
                data={"sub": str(user_id_final), "role": "cliente"},
                expires_delta=expires_delta_register,
            )

            return {
                "id_cliente": user_id_final,
                "nombre_cliente": nombre_cliente,
                "apellido_cliente": apellido_cliente,
                "direccion_cliente": direccion_cliente,
                "telefono_cliente": telefono_cliente,
                "correo_cliente": correo_cliente,
                "access_token": access_token_register,
                "token_type": "bearer",
                "role": "cliente",
            }
        except ValueError as ve:
            raise ve  # Para que el router lo maneje como 409 o 400
        except psycopg2.Error as e:
            logger.error(
                f"DATABASE ERROR (register_user) for {correo_cliente}: {e}",
                exc_info=True,
            )
            raise Exception(
                f"Error de base de datos. pgcode: {getattr(e, 'pgcode', 'N/A')}"
            )
        except Exception as e:
            logger.error(
                f"GENERAL ERROR (register_user) for {correo_cliente}: {e}",
                exc_info=True,
            )
            raise Exception(f"Error inesperado: {str(e)}")

    async def authenticate_user(self, correo_cliente, contrasenia):
        try:
            with get_db_cursor() as cursor:  # commit=False por defecto, lo cual es correcto para SELECT
                # Asegúrate que tu tabla tbl_cliente tiene una columna estado_cliente
                # Si no la tiene, quita "AND estado_cliente = 'ACTIVO'" de la consulta
                cursor.execute(
                    """
                    SELECT id_cliente, nombre_cliente, apellido_cliente,
                           direccion_cliente, telefono_cliente, correo_cliente,
                           contrasenia
                    FROM tbl_cliente
                    WHERE correo_cliente = %s AND estado_cliente = 'ACTIVO'; 
                    """,  # ASUME QUE TIENES estado_cliente
                    (correo_cliente,),
                )
                user_data_dict = cursor.fetchone()  # Esto será un dict

            if not user_data_dict:
                logger.warning(
                    f"Cliente no encontrado o inactivo con correo: {correo_cliente}"
                )
                return None

            stored_password_hash = user_data_dict["contrasenia"]

            if bcrypt.verify(contrasenia, stored_password_hash):
                logger.info(f"Contraseña verificada para cliente: {correo_cliente}")
                client_id = user_data_dict["id_cliente"]
                expires_delta_auth = timedelta(
                    minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
                )
                access_token_auth = self._create_access_token(
                    data={"sub": str(client_id), "role": "cliente"},
                    expires_delta=expires_delta_auth,
                )
                return {
                    "access_token": access_token_auth,
                    "token_type": "bearer",
                    "id_cliente": client_id,
                    "nombre_cliente": user_data_dict["nombre_cliente"],
                    "apellido_cliente": user_data_dict["apellido_cliente"],
                    "direccion_cliente": user_data_dict["direccion_cliente"],
                    "telefono_cliente": user_data_dict["telefono_cliente"],
                    "correo_cliente": user_data_dict["correo_cliente"],
                    "role": "cliente",
                }
            else:
                logger.warning(f"Contraseña incorrecta para cliente: {correo_cliente}")
                return None
        except psycopg2.Error as e:
            logger.error(
                f"DATABASE ERROR (authenticate_user) for {correo_cliente}: {e}",
                exc_info=True,
            )
            # El router debería convertir esto en una HTTPException 500
            raise Exception(
                f"Error de base de datos durante la autenticación. pgcode: {getattr(e, 'pgcode', 'N/A')}"
            )
        except Exception as e:
            logger.error(
                f"GENERAL ERROR (authenticate_user) for {correo_cliente}: {e}",
                exc_info=True,
            )
            raise Exception(f"Error inesperado durante la autenticación: {str(e)}")

    def _create_access_token(self, data: dict, expires_delta: timedelta):
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return encoded_jwt
