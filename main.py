from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Importar la función para cerrar el pool de DB y el pool mismo para verificar
from database import close_db_pool, db_pool

# Importar tus routers existentes
from routers import (
    login,
)  # Asumo que este es para la autenticación de usuarios/clientes
from routers import users
from routers import products
from routers import orders

# Importar el nuevo router de repartidores
from routers import delivery as repartidores_router  # <--- AÑADIDO

# Importar el middleware de autenticación para usuarios (si lo usas a nivel de router o endpoint)
from middleware.authenticator import get_current_user  # Ya lo tenías


# Lifespan manager para inicializar y cerrar recursos como el pool de DB
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código de inicio: se ejecuta cuando la aplicación arranca
    if db_pool:
        print("main.py: El pool de conexiones de base de datos parece estar listo.")
    else:
        print(
            "main.py: ALERTA - El pool de conexiones de base de datos NO está inicializado. Verifica database.py y .env."
        )
    yield
    # Código de cierre: se ejecuta cuando la aplicación se detiene
    print("main.py: Cerrando la aplicación y los recursos...")
    close_db_pool()  # Llama a la función para cerrar el pool
    print(
        "main.py: Pool de conexiones de base de datos cerrado (si estaba inicializado)."
    )


app = FastAPI(
    title="QuickBite API",
    description="API para la aplicación de delivery QuickBite.",
    version="0.1.0",
    lifespan=lifespan,  # <--- AÑADIDO LIFESPAN MANAGER
)

# Configuración de CORS (Cross-Origin Resource Sharing)
# Ajusta origins según tus necesidades (ej. la URL de tu frontend Flutter)
origins = [
    "http://localhost",  # Para desarrollo local general
    "http://localhost:3000",  # Común para React, Vue, Angular
    "http://localhost:8080",  # Común para algunos servidores de desarrollo o Flutter web
    "http://localhost:8081",  # Otro puerto común
    # "http://192.168.X.X:PORT" # Si pruebas desde un dispositivo móvil en tu red local
    # Añade aquí la URL de tu frontend en producción cuando la tengas
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # Importante si usas cookies o tokens de autorización
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Permite todos los headers (incluyendo Authorization)
)


# Ruta raíz de prueba
@app.get("/", tags=["Root"])  # Añadida etiqueta para Swagger
def root():
    return {"mensaje": "API de Quickbite activa"}


# Registrar routers en la aplicación
# Router para autenticación de usuarios/clientes
app.include_router(
    login.router, prefix="/api/auth", tags=["Autenticación Usuarios"]
)  # <--- MODIFICADO: Añadido /api y mejorado tag

# Router para gestión de usuarios/clientes
app.include_router(
    users.router, prefix="/api/users", tags=["Usuarios"]
)  # <--- MODIFICADO: Añadido /api y tag

# Router para productos
app.include_router(
    products.router, prefix="/api/products", tags=["Productos"]
)  # <--- MODIFICADO: Añadido /api y tag

# Router para pedidos (protegido para usuarios autenticados)
app.include_router(
    orders.router,
    prefix="/api/orders",  # <--- MODIFICADO: Añadido /api
    tags=["Pedidos (Clientes)"],
    dependencies=[Depends(get_current_user)],  # Protege todas las rutas de este router
)

# Router para repartidores
app.include_router(
    repartidores_router.router, prefix="/api/repartidores", tags=["Repartidores"]
)  # <--- AÑADIDO


# Ejemplo de una ruta protegida individualmente (ya la tenías)
# Asegúrate que el prefijo no choque o sea claro
@app.get(
    "/api/protected/item", tags=["Ejemplo Protegido"]
)  # <--- MODIFICADO: Añadido /api y tag
async def get_protected_item(current_user: dict = Depends(get_current_user)):
    # Asumiendo que get_current_user devuelve un TokenDataUser que tiene user_id
    # Si get_current_user devuelve el modelo TokenDataUser, sería current_user.user_id
    user_identifier = (
        current_user.user_id
        if hasattr(current_user, "user_id")
        else current_user.get("user_id", "ID no disponible")
    )
    return {
        "item": "This is a protected item for a logged-in user",
        "user_id": user_identifier,
    }


# Endpoint de health check (recomendado)
@app.get("/health", tags=["Health Check"])
async def health_check():
    # Podrías añadir verificaciones más complejas aquí (ej. estado de la DB)
    # Por ejemplo, intentar obtener una conexión del pool
    try:
        conn = db_pool.getconn()
        db_pool.putconn(conn)
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok", "database_status": db_status}
