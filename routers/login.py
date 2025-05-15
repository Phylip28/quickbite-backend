from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from database import get_connection

router = APIRouter()


class LoginInput(BaseModel):
    correo: str
    contrasena: str


@router.post("/login")
def login(data: LoginInput):
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT * FROM clientes WHERE correo = %s AND contrasenia = %s",
            (data.correo, data.contrasena),
        )
        cliente = cursor.fetchone()
        cursor.close()
        conn.close()

        if cliente:
            return {"mensaje": "Login exitoso", "cliente": cliente}
        else:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
