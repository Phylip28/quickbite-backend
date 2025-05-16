from pydantic import BaseModel, EmailStr
from datetime import date


class RegisterRequest(BaseModel):
    nombre_cliente: str
    apellido_cliente: str
    direccion_cliente: str
    telefono_cliente: str
    correo_cliente: EmailStr
    contrasenia: str


class LoginRequest(BaseModel):
    correo_cliente: EmailStr
    contrasenia: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
