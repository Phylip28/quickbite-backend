from fastapi import FastAPI
from routers import login

app = FastAPI()


# Ruta raíz de prueba
@app.get("/")
def root():
    return {"mensaje": "API de Quickbite activa"}


app.include_router(login.router)
