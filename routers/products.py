from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from models.product_model import (
    Product,
    ProductCreate,
    ProductUpdate,
)  # Asegúrate de que ProductUpdate esté definido si lo usas
from services import product_service

# Opcional: Si necesitas autenticación para ciertas rutas de productos
# from middleware.authenticator import get_current_user # Descomenta si necesitas proteger rutas

router = APIRouter(prefix="/products", tags=["Products"])


# --- Endpoint para crear un nuevo producto ---
# Considera proteger esta ruta (ej. solo para administradores)
# Añade, por ejemplo, dependencies=[Depends(get_current_user_admin_role)]
@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_new_product(product_data: ProductCreate):
    """
    Crea un nuevo producto.
    El cuerpo del request debe contener:
    - nombre_producto: str
    - precio_producto: float
    - (Opcional) descripcion_producto: str
    """
    try:
        created_product = await product_service.create_product(
            product_data=product_data
        )
        # El servicio create_product ya debería levantar una HTTPException si falla la creación
        # y devolver el producto si tiene éxito.
        return created_product
    except HTTPException as e:
        # Re-lanzar HTTPExceptions que vienen del servicio o de validaciones
        raise e
    except Exception as e:
        # Para cualquier otra excepción inesperada en el router
        print(f"Error inesperado en router al crear producto: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error inesperado en el servidor: {str(e)}",
        )


# --- Endpoint para obtener todos los productos ---
# Esta ruta es generalmente pública.
@router.get("/", response_model=List[Product])
async def get_all_products(
    skip: int = 0,
    limit: int = 100,
    # restaurant_id: Optional[int] = None # Descomenta y añade al servicio si necesitas filtrar por restaurante
):
    """
    Obtiene una lista de todos los productos disponibles.
    Soporta paginación con `skip` y `limit`.
    """
    try:
        products = await product_service.get_products(skip=skip, limit=limit)
        return products
    except Exception as e:
        print(f"Error inesperado en router al obtener productos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error inesperado en el servidor: {str(e)}",
        )


# --- Endpoint para obtener un producto específico por su ID ---
@router.get("/{product_id}", response_model=Product)
async def get_product_by_id_route(
    product_id: int,
):  # Renombrado para evitar conflicto con posible variable 'product_id'
    """
    Obtiene los detalles de un producto específico por su ID.
    """
    try:
        product = await product_service.get_product_by_id(product_id=product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado.",
            )
        return product
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error inesperado en router al obtener producto {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error inesperado en el servidor: {str(e)}",
        )


# --- Endpoint para actualizar un producto existente ---
# Considera proteger esta ruta
@router.put("/{product_id}", response_model=Product)
async def update_existing_product(
    product_id: int,
    product_update_data: ProductUpdate,  # Usa el modelo ProductUpdate para actualizaciones parciales
):
    """
    Actualiza un producto existente.
    Solo los campos proporcionados en el cuerpo del request serán actualizados.
    """
    try:
        updated_product = await product_service.update_product(
            product_id=product_id, product_update_data=product_update_data
        )
        if not updated_product:
            # El servicio update_product debería devolver None si el producto no se encontró
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado para actualizar.",
            )
        return updated_product
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error inesperado en router al actualizar producto {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error inesperado en el servidor: {str(e)}",
        )


# --- Endpoint para eliminar un producto existente ---
# Considera proteger esta ruta
@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_product(product_id: int):
    """
    Elimina un producto existente.
    Devuelve 204 No Content si la eliminación es exitosa.
    """
    try:
        # El servicio delete_product devuelve el número de filas eliminadas
        deleted_count = await product_service.delete_product(product_id=product_id)
        if deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado para eliminar.",
            )
        # No se devuelve contenido en un 204, FastAPI lo maneja automáticamente
    except HTTPException as e:  # Captura HTTPExceptions del servicio (ej. 409 por FK)
        raise e
    except Exception as e:
        print(f"Error inesperado en router al eliminar producto {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error inesperado en el servidor: {str(e)}",
        )
