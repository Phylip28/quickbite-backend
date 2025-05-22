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


# Modelo para crear un nuevo repartidor (incluye la contraseña)
class RepartidorCreate(RepartidorBase):
    contrasenia: str = Field(..., min_length=8)
    # Los siguientes campos ya tienen default en RepartidorBase,
    # pero se pueden redefinir aquí si se quiere un default diferente en creación
    # o para hacerlos explícitamente opcionales en el payload de creación.
    disponibilidad: Optional[bool] = Field(default=True)
    estado_repartidor: Optional[str] = Field(default="ACTIVO")


# Modelo para actualizar un repartidor (todos los campos son opcionales)
class RepartidorUpdate(BaseModel):
    nombre_repartidor: Optional[str] = Field(default=None, min_length=1)
    apellido_repartidor: Optional[str] = Field(default=None, min_length=1)
    correo_repartidor: Optional[EmailStr] = None
    direccion_repartidor: Optional[str] = None
    telefono_repartidor: Optional[str] = None
    dni_repartidor: Optional[str] = None
    vehiculo_repartidor: Optional[str] = None
    disponibilidad: Optional[bool] = None
    estado_repartidor: Optional[str] = None
    # Si se permite actualizar la contraseña, se añadiría aquí:
    # contrasenia: Optional[str] = Field(default=None, min_length=8)


# Modelo para representar un repartidor en las respuestas de la API (sin la contraseña)
class Repartidor(RepartidorBase):
    id_repartidor: int
    fecha_registro_repartidor: datetime.datetime

    class Config:
        from_attributes = True  # Para Pydantic v2 (o orm_mode = True para v1)


# Modelo para el login del repartidor
class RepartidorLogin(BaseModel):
    correo_repartidor: EmailStr
    contrasenia: str


# Modelo para los datos contenidos en el token JWT del repartidor
# CORREGIDO para coincidir con el uso en authenticator.py
class TokenDataRepartidor(BaseModel):
    correo_repartidor: EmailStr  # 'sub' del JWT se espera que sea el correo
    id_repartidor: int  # Campo 'id_repartidor' del JWT
    role: str  # Campo 'role' del JWT, se espera 'repartidor'


# Modelo para la respuesta del token al hacer login
class TokenRepartidor(BaseModel):
    access_token: str
    token_type: str = "bearer"
    id_repartidor: int
    nombre_repartidor: str
    apellido_repartidor: str
    correo_repartidor: EmailStr
    telefono_repartidor: Optional[str] = None
    vehiculo_repartidor: Optional[str] = None
    role: str  # MUY IMPORTANTE para que Flutter sepa que es un repartidor


# Modelo para actualizar solo la disponibilidad
class RepartidorDisponibilidadUpdate(BaseModel):
    disponibilidad: bool
