from fastapi import FastAPI, Depends
from routers import (
    login,
    users,
    products,
    orders,
)
from middleware.authenticator import get_current_user

app = FastAPI()


# Ruta raíz de prueba
@app.get("/")
def root():
    return {"mensaje": "API de Quickbite activa"}


app.include_router(login.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router)
app.include_router(products.router)
app.include_router(
    orders.router, dependencies=[Depends(get_current_user)]
)  # Protege las rutas de orders


# Ejemplo de una ruta protegida individualmente
@app.get("/protected/item")
async def get_protected_item(current_user: dict = Depends(get_current_user)):
    return {"item": "This is a protected item", "user_id": current_user["user_id"]}
