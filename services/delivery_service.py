from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import datetime  # Para fecha_registro_repartidor y datetime


# Modelo base con los campos comunes del repartidor
class RepartidorBase(BaseModel):
    nombre_repartidor: str = Field(..., min_length=1)
    apellido_repartidor: str = Field(..., min_length=1)
    correo_repartidor: EmailStr
    direccion_repartidor: Optional[str] = None
    telefono_repartidor: Optional[str] = None
    dni_repartidor: Optional[str] = None
    vehiculo_repartidor: Optional[str] = (
        None  # Renombrado desde tipo_vehiculo para consistencia si es el vehículo general
    )
    disponibilidad: bool = True
    estado_repartidor: str = "ACTIVO"


# Modelo para crear un nuevo rfrom database import get_db_cursor
from models.delivery_model import (
    RepartidorCreate,
    Repartidor,
    RepartidorUpdate,
    TokenRepartidor,  # Asegúrate que este es el modelo que definimos en el paso anterior
    # RepartidorLogin no se usa directamente aquí pero es bueno tenerlo importado si otros módulos lo necesitan
)
from database import (
    get_db_cursor,
)  # Asumo que esta es tu función para obtener el cursor
from passlib.context import CryptContext
from fastapi import HTTPException, status
import psycopg2
import jwt
from datetime import datetime, timedelta, timezone
from config import settings
import logging

logger = logging.getLogger(__name__)
if not logger.handlers:  # Evitar duplicar handlers si el módulo se recarga
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def _create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


async def create_repartidor(
    repartidor_data: RepartidorCreate,
) -> Repartidor:
    hashed_contrasenia = hash_password(repartidor_data.contrasenia)
    with get_db_cursor(commit=True) as cursor:
        try:
            cursor.execute(
                """
                INSERT INTO tbl_repartidor (
                    nombre_repartidor, apellido_repartidor, correo_repartidor,
                    direccion_repartidor, telefono_repartidor, dni_repartidor,
                    vehiculo_repartidor, contrasenia, disponibilidad,
                    fecha_registro_repartidor, estado_repartidor
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                RETURNING id_repartidor, nombre_repartidor, apellido_repartidor, correo_repartidor,
                          direccion_repartidor, telefono_repartidor, dni_repartidor,
                          vehiculo_repartidor, disponibilidad, fecha_registro_repartidor, estado_repartidor;
                """,
                (
                    repartidor_data.nombre_repartidor,
                    repartidor_data.apellido_repartidor,
                    repartidor_data.correo_repartidor,
                    repartidor_data.direccion_repartidor,
                    repartidor_data.telefono_repartidor,
                    repartidor_data.dni_repartidor,
                    repartidor_data.vehiculo_repartidor,
                    hashed_contrasenia,  # Usar la contraseña hasheada
                    (
                        repartidor_data.disponibilidad
                        if repartidor_data.disponibilidad is not None
                        else True
                    ),
                    (
                        repartidor_data.estado_repartidor
                        if repartidor_data.estado_repartidor
                        else "ACTIVO"
                    ),
                ),
            )
            nuevo_repartidor_db = cursor.fetchone()
            if not nuevo_repartidor_db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No se pudo crear el repartidor después de la inserción.",
                )
            return Repartidor(**nuevo_repartidor_db)
        except psycopg2.Error as e:
            logger.error(f"Error de BD al crear repartidor (pgcode: {e.pgcode}): {e}")
            if e.pgcode == "23505":
                detail_message = "Error al crear repartidor: "
                if "correo_repartidor" in str(e).lower():
                    detail_message += (
                        f"El correo '{repartidor_data.correo_repartidor}' ya existe."
                    )
                elif "dni_repartidor" in str(e).lower():
                    detail_message += (
                        f"El DNI '{repartidor_data.dni_repartidor}' ya existe."
                    )
                elif "telefono_repartidor" in str(e).lower():
                    detail_message += f"El teléfono '{repartidor_data.telefono_repartidor}' ya existe."
                else:
                    detail_message += "Un valor único ya existe."
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail=detail_message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error interno del servidor.",
                )
        except Exception as e:
            logger.error(
                f"Excepción inesperada al crear repartidor: {e}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error inesperado al crear repartidor.",
            )


async def authenticate_repartidor(
    correo_repartidor: str, contrasenia: str
) -> TokenRepartidor | None:
    repartidor_db = await get_repartidor_by_correo(correo_repartidor)

    if not repartidor_db:
        logger.warning(
            f"Login fallido: Repartidor no encontrado con correo {correo_repartidor}"
        )
        return None

    if repartidor_db.get("estado_repartidor") != "ACTIVO":
        logger.warning(f"Login fallido: Repartidor {correo_repartidor} no está activo.")
        return None

    # Asegúrate que la columna de contraseña en tu DB se llame 'contrasenia' o ajusta aquí
    if not verify_password(contrasenia, repartidor_db["contrasenia"]):
        logger.warning(f"Login fallido: Contraseña incorrecta para {correo_repartidor}")
        return None

    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = _create_access_token(
        data={
            "sub": str(repartidor_db["id_repartidor"]),  # ID como 'sub'
            "id_repartidor": repartidor_db[
                "id_repartidor"
            ],  # Mantenemos id_repartidor para conveniencia
            "role": "repartidor",
        },
        expires_delta=expires_delta,
    )
    logger.info(f"Repartidor {correo_repartidor} autenticado exitosamente.")

    # Construir el objeto TokenRepartidor con todos los campos necesarios
    return TokenRepartidor(
        access_token=access_token,
        token_type="bearer",
        id_repartidor=repartidor_db["id_repartidor"],
        nombre_repartidor=repartidor_db["nombre_repartidor"],
        apellido_repartidor=repartidor_db["apellido_repartidor"],  # Añadido
        correo_repartidor=repartidor_db["correo_repartidor"],
        role="repartidor",  # Añadido y MUY IMPORTANTE
        # Opcional: puedes añadir más campos del repartidor_db aquí si los definiste en TokenRepartidor
        # telefono_repartidor=repartidor_db.get("telefono_repartidor"),
        # disponibilidad=repartidor_db.get("disponibilidad"),
        # vehiculo_repartidor=repartidor_db.get("vehiculo_repartidor"),
        # placa_vehiculo=repartidor_db.get("placa_vehiculo"), # Si tienes este campo
    )


async def get_repartidor_by_correo(correo_repartidor: str) -> dict | None:
    with get_db_cursor() as cursor:
        try:
            # Asegúrate que la columna de contraseña se llama 'contrasenia' en tbl_repartidor
            cursor.execute(
                """
                SELECT id_repartidor, nombre_repartidor, apellido_repartidor, correo_repartidor,
                       direccion_repartidor, telefono_repartidor, dni_repartidor,
                       vehiculo_repartidor, contrasenia, disponibilidad, fecha_registro_repartidor,
                       estado_repartidor
                FROM tbl_repartidor
                WHERE correo_repartidor = %s;
                """,
                (correo_repartidor,),
            )
            return cursor.fetchone()  # Devuelve un dict o None
        except psycopg2.Error as e:
            logger.error(
                f"Error de BD al buscar repartidor por correo {correo_repartidor} (pgcode: {e.pgcode}): {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al buscar repartidor por correo.",
            )
        except Exception as e:
            logger.error(
                f"Excepción inesperada al buscar repartidor por correo {correo_repartidor}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error inesperado al buscar repartidor por correo.",
            )


async def get_repartidor_by_id(id_repartidor: int) -> Repartidor | None:
    with get_db_cursor() as cursor:
        try:
            cursor.execute(
                """
                SELECT id_repartidor, nombre_repartidor, apellido_repartidor, correo_repartidor,
                       direccion_repartidor, telefono_repartidor, dni_repartidor,
                       vehiculo_repartidor, disponibilidad, fecha_registro_repartidor, estado_repartidor
                FROM tbl_repartidor
                WHERE id_repartidor = %s;
                """,
                (id_repartidor,),
            )
            repartidor_db_dict = cursor.fetchone()
            if repartidor_db_dict:
                return Repartidor(**repartidor_db_dict)
            return None
        except psycopg2.Error as e:
            logger.error(
                f"Error de BD al buscar repartidor por ID {id_repartidor} (pgcode: {e.pgcode}): {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al buscar repartidor por ID.",
            )
        except Exception as e:
            logger.error(
                f"Excepción inesperada al buscar repartidor por ID {id_repartidor}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error inesperado al buscar repartidor por ID.",
            )


async def update_repartidor(
    id_repartidor: int, repartidor_update: RepartidorUpdate
) -> Repartidor | None:
    update_data = repartidor_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se proporcionaron datos para actualizar.",
        )

    set_clauses = []
    values = []
    # Validar que los campos existan en el modelo RepartidorCreate (que define campos válidos para la DB)
    # y no sea 'contrasenia'
    valid_fields = RepartidorCreate.model_fields.keys()

    for key, value in update_data.items():
        if key in valid_fields and key != "contrasenia":
            set_clauses.append(f"{key} = %s")
            values.append(value)
        # else: logger.warning(f"Campo '{key}' ignorado durante la actualización del repartidor.")

    if not set_clauses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ningún campo válido proporcionado para la actualización.",
        )

    values.append(id_repartidor)
    query = f"""
        UPDATE tbl_repartidor
        SET {', '.join(set_clauses)}
        WHERE id_repartidor = %s
        RETURNING id_repartidor, nombre_repartidor, apellido_repartidor, correo_repartidor,
                  direccion_repartidor, telefono_repartidor, dni_repartidor,
                  vehiculo_repartidor, disponibilidad, fecha_registro_repartidor, estado_repartidor;
    """
    with get_db_cursor(commit=True) as cursor:
        try:
            cursor.execute(query, tuple(values))
            repartidor_actualizado_db = cursor.fetchone()
            if not repartidor_actualizado_db:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Repartidor con ID {id_repartidor} no encontrado.",
                )
            return Repartidor(**repartidor_actualizado_db)
        except psycopg2.Error as e:
            logger.error(
                f"Error de BD al actualizar repartidor {id_repartidor} (pgcode: {e.pgcode}): {e}",
                exc_info=True,
            )
            if e.pgcode == "23505":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Error al actualizar: un valor único ya está en uso.",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al actualizar repartidor.",
            )
        except Exception as e:
            logger.error(
                f"Excepción inesperada al actualizar repartidor {id_repartidor}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error inesperado al actualizar repartidor.",
            )


async def update_repartidor_disponibilidad(
    id_repartidor: int, disponibilidad: bool
) -> Repartidor | None:
    with get_db_cursor(commit=True) as cursor:
        try:
            cursor.execute(
                """
                UPDATE tbl_repartidor
                SET disponibilidad = %s
                WHERE id_repartidor = %s
                RETURNING id_repartidor, nombre_repartidor, apellido_repartidor, correo_repartidor,
                          direccion_repartidor, telefono_repartidor, dni_repartidor,
                          vehiculo_repartidor, disponibilidad, fecha_registro_repartidor, estado_repartidor;
                """,
                (disponibilidad, id_repartidor),
            )
            repartidor_actualizado_db = cursor.fetchone()
            if not repartidor_actualizado_db:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Repartidor con ID {id_repartidor} no encontrado.",
                )
            return Repartidor(**repartidor_actualizado_db)
        except psycopg2.Error as e:
            logger.error(
                f"Error de BD al actualizar disponibilidad {id_repartidor} (pgcode: {e.pgcode}): {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al actualizar disponibilidad.",
            )
        except Exception as e:
            logger.error(
                f"Excepción inesperada al actualizar disponibilidad {id_repartidor}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error inesperado al actualizar disponibilidad.",
            )
