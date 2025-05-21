from pydantic import (
    BaseModel,
    EmailStr,
)  # EmailStr podría ser útil para otros modelos de usuario
from typing import Optional  # Optional ya no es necesario para 'role' en TokenDataUser


class TokenDataUser(BaseModel):
    user_id: str  # Confirmamos que 'sub' es el ID de cliente como string
    role: str  # <--- MODIFICADO: Ahora es un campo requerido, ya que el token siempre lo incluirá.


# Tu clase User existente puede permanecer si la usas para otros propósitos.
# Si planeas usar Pydantic para las respuestas de API de usuarios/clientes,
# también definirías modelos como UserResponse, UserCreate, etc., aquí.
class User:
    def __init__(
        self,
        id_cliente,
        nombre_cliente,
        apellido_cliente,
        direccion_cliente,
        telefono_cliente,
        correo_cliente,
        fecha_registro_cliente,
        contrasenia,
    ):
        self.id_cliente = id_cliente
        self.nombre_cliente = nombre_cliente
        self.apellido_cliente = apellido_cliente
        self.direccion_cliente = direccion_cliente
        self.telefono_cliente = telefono_cliente
        self.correo_cliente = correo_cliente
        self.fecha_registro_cliente = fecha_registro_cliente
        self.contrasenia = contrasenia  # hash de la contraseña

    def to_dict(self):
        return {
            "id_cliente": self.id_cliente,
            "nombre_cliente": self.nombre_cliente,
            "apellido_cliente": self.apellido_cliente,
            "direccion_cliente": self.direccion_cliente,
            "telefono_cliente": self.telefono_cliente,
            "correo_cliente": self.correo_cliente,
            "fecha_registro_cliente": str(self.fecha_registro_cliente),
            "contrasenia": self.contrasenia,
        }


# Ejemplo de otros modelos Pydantic que podrías tener para usuarios/clientes:
# class UserBase(BaseModel):
#     nombre_cliente: str
#     apellido_cliente: str
#     correo_cliente: EmailStr
#     direccion_cliente: Optional[str] = None
#     telefono_cliente: Optional[str] = None

# class UserCreate(UserBase):
#     contrasenia: str

# class UserResponse(UserBase):
#     id_cliente: int
#     fecha_registro_cliente: datetime.date # o datetime.datetime según tu DB
#     # estado_cliente: Optional[str] = None # si tienes este campo

#     class Config:
#         from_attributes = True
