import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from config import settings  # <--- IMPORTANTE: Importar settings desde config.py

print(
    f"Configuración de DB desde settings: Nombre='{settings.DB_NAME}', Usuario='{settings.DB_USER}', Host='{settings.DB_HOST}', Puerto='{settings.DB_PORT}'"
)

db_pool = None

try:
    # Crear un pool de conexiones usando la configuración de settings
    db_pool = psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,  # Ajusta según tus necesidades
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
    )
    # Intenta obtener una conexión para verificar que el pool funciona
    conn_test = db_pool.getconn()
    if conn_test:
        print(
            f"Pool de conexiones a PostgreSQL para '{settings.DB_NAME}' creado exitosamente."
        )
        db_pool.putconn(conn_test)  # Devuelve la conexión al pool
    else:
        print(
            "Error: El pool de conexiones devolvió None al intentar obtener una conexión de prueba."
        )
        db_pool = None  # Marcar como no inicializado si la prueba falla

except psycopg2.OperationalError as e:
    print(
        f"Error Crítico de Conexión a PostgreSQL (OperationalError al crear el pool): {e}"
    )
    print(
        "Por favor, verifica tus credenciales de base de datos en .env y que config.py las esté cargando correctamente, y que el servidor PostgreSQL esté corriendo y accesible."
    )
    db_pool = None
except Exception as error:
    print(f"Error general al crear el pool de conexiones: {error}")
    db_pool = None


def get_db_connection_from_pool():
    """Obtiene una conexión del pool."""
    if not db_pool:
        # Podrías lanzar una excepción más específica o permitir que la aplicación falle si el pool es esencial.
        print(
            "ALERTA: El pool de conexiones no está inicializado. Intentando obtener conexión."
        )
        raise psycopg2.OperationalError("El pool de conexiones no está inicializado.")
    try:
        conn = db_pool.getconn()
        if conn is None:  # Comprobación adicional
            print("Error: db_pool.getconn() devolvió None.")
            raise psycopg2.OperationalError(
                "No se pudo obtener una conexión válida del pool (getconn devolvió None)."
            )
        return conn
    except Exception as e:
        print(f"Error al obtener conexión del pool: {e}")
        # Considera relanzar la excepción o una personalizada para que el llamador pueda manejarla.
        raise  # Relanzar la excepción para que sea manejada por el llamador


def release_db_connection_to_pool(conn):
    """Libera una conexión de vuelta al pool."""
    if db_pool and conn:
        try:
            db_pool.putconn(conn)
        except Exception as e:
            print(f"Error al liberar conexión al pool: {e}")
            # Decide cómo manejar esto. ¿Cerrar la conexión directamente?
            # conn.close() podría ser una opción si putconn falla repetidamente.


@contextmanager
def get_db_cursor(commit=False):
    """
    Context manager para obtener un cursor y manejar la conexión del pool.
    Usa RealDictCursor para devolver filas como diccionarios.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_from_pool()
        # conn ya no debería ser None aquí si get_db_connection_from_pool lanza excepción en caso de fallo
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        yield cursor
        if commit:
            conn.commit()
    except psycopg2.Error as db_op_error:  # Captura errores de psycopg2 específicamente
        if conn:
            conn.rollback()
        print(f"Error de base de datos (get_db_cursor - psycopg2.Error): {db_op_error}")
        raise  # Relanza la excepción original para que los servicios la manejen
    except Exception as e:  # Captura otras excepciones inesperadas
        if conn:
            conn.rollback()  # Intenta rollback también para excepciones generales
        print(f"Error inesperado en get_db_cursor: {e}")
        raise  # Relanza la excepción original
    finally:
        if cursor:
            cursor.close()
        if conn:
            release_db_connection_to_pool(conn)


def close_db_pool():
    """Cierra todas las conexiones en el pool."""
    global db_pool
    if db_pool:
        try:
            db_pool.closeall()
            print(f"Pool de conexiones a '{settings.DB_NAME}' cerrado.")
        except Exception as e:
            print(f"Error al cerrar el pool de conexiones: {e}")
        finally:
            db_pool = None


# La función original get_connection() que tenías ya no es necesaria si todo usa el pool.
# Si auth_service.py aún la usa, necesitará ser refactorizado o debes mantenerla.
# Por ahora, la comentaremos para fomentar el uso del pool.
# def get_connection():
#     print("ADVERTENCIA: Se está utilizando la función get_connection() heredada en lugar del pool.")
#     return psycopg2.connect(
#         dbname=settings.DB_NAME,
#         user=settings.DB_USER,
#         password=settings.DB_PASSWORD,
#         host=settings.DB_HOST,
#         port=settings.DB_PORT,
#     )
