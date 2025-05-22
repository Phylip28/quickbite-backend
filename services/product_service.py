from database import get_db_cursor
from models.product_model import Product, ProductCreate, ProductUpdate
from fastapi import HTTPException, status
import psycopg2
import datetime
from typing import List, Optional


async def create_product(product_data: ProductCreate) -> Product:
    """
    Crea un nuevo producto en la base de datos.
    """
    # fecha_creacion_producto se establece por defecto en la BD (CURRENT_TIMESTAMP)
    # fecha_modificacion_producto será NULL inicialmente
    with get_db_cursor(commit=True) as cursor:
        try:
            # Asumiendo que ProductCreate tiene: nombre_producto, precio_producto, descripcion_producto
            cursor.execute(
                """
                INSERT INTO tbl_producto (nombre_producto, descripcion_producto, precio_producto)
                VALUES (%s, %s, %s)
                RETURNING id_producto, nombre_producto, descripcion_producto, precio_producto, 
                          fecha_creacion_producto, fecha_modificacion_producto;
                """,
                (
                    product_data.nombre_producto,
                    product_data.descripcion_producto,  # Puede ser None
                    product_data.precio_producto,
                ),
            )
            created_product_db = cursor.fetchone()
            if not created_product_db:
                # Esto no debería ocurrir si la inserción fue exitosa y RETURNING se usó correctamente
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No se pudo obtener el producto después de la creación.",
                )
            return Product(**created_product_db)
        except (
            psycopg2.IntegrityError
        ) as e:  # Captura errores de integridad como unique_violation
            print(f"Error de integridad al crear producto: {e}")
            # Podrías verificar e.pgcode para ser más específico, ej. '23505' para unique_violation
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflicto al crear producto: {e.diag.message_detail or e.pgerror}",
            )
        except psycopg2.Error as e:  # Otros errores de psycopg2
            print(f"Error de base de datos (create_product): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de base de datos al crear producto: {e.pgerror}",
            )
        except Exception as e:  # Cualquier otra excepción
            print(f"Excepción inesperada (create_product): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ocurrió un error inesperado al crear el producto.",
            )


async def get_product_by_id(product_id: int) -> Optional[Product]:
    """
    Obtiene un producto específico por su ID.
    Devuelve None si el producto no se encuentra.
    """
    with get_db_cursor() as cursor:
        try:
            cursor.execute(
                """
                SELECT id_producto, nombre_producto, descripcion_producto, precio_producto, 
                       fecha_creacion_producto, fecha_modificacion_producto
                FROM tbl_producto
                WHERE id_producto = %s;
                """,
                (product_id,),
            )
            product_db = cursor.fetchone()
            if product_db:
                return Product(**product_db)
            return None
        except psycopg2.Error as e:
            print(f"Error de base de datos (get_product_by_id): {e}")
            # Considera si quieres levantar una excepción aquí o dejar que el router maneje el None
            # Levantar una excepción aquí podría ser más limpio para el servicio.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de base de datos al obtener producto por ID: {e.pgerror}",
            )
        except Exception as e:
            print(f"Excepción inesperada (get_product_by_id): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ocurrió un error inesperado al obtener el producto por ID.",
            )


async def get_products(skip: int = 0, limit: int = 100) -> List[Product]:
    """
    Obtiene una lista de productos con paginación.
    """
    # Aquí podrías añadir filtros, por ejemplo, por id_restaurante si lo tuvieras
    with get_db_cursor() as cursor:
        try:
            cursor.execute(
                """
                SELECT id_producto, nombre_producto, descripcion_producto, precio_producto, 
                       fecha_creacion_producto, fecha_modificacion_producto
                FROM tbl_producto
                ORDER BY nombre_producto -- o id_producto, o fecha_creacion_producto
                LIMIT %s OFFSET %s;
                """,
                (limit, skip),
            )
            products_db = cursor.fetchall()
            return [Product(**prod_row) for prod_row in products_db]
        except psycopg2.Error as e:
            print(f"Error de base de datos (get_products): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de base de datos al obtener lista de productos: {e.pgerror}",
            )
        except Exception as e:
            print(f"Excepción inesperada (get_products): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ocurrió un error inesperado al obtener la lista de productos.",
            )


async def update_product(
    product_id: int, product_update_data: ProductUpdate
) -> Optional[Product]:
    """
    Actualiza un producto existente.
    Solo actualiza los campos proporcionados en product_update_data.
    Devuelve el producto actualizado o None si no se encontró.
    """
    # Obtener los campos a actualizar del modelo Pydantic
    update_fields = product_update_data.model_dump(exclude_unset=True)  # Pydantic v2
    # Para Pydantic v1: update_fields = product_update_data.dict(exclude_unset=True)

    if not update_fields:
        # No hay campos para actualizar, podrías devolver el producto sin cambios o un error 400
        # Devolver el producto actual podría ser una opción si no se considera un error.
        existing_product = await get_product_by_id(product_id)
        if not existing_product:  # Si además no existe, el router lo convertirá en 404
            return None
        # Opcionalmente, levantar un error si no se proporcionaron campos:
        # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update.")
        return existing_product  # Devolver el producto sin cambios

    # Añadir fecha_modificacion_producto
    update_fields["fecha_modificacion_producto"] = datetime.datetime.now(
        datetime.timezone.utc
    )  # O datetime.now() si no es TZ-aware

    # Construir la parte SET de la consulta dinámicamente
    set_clauses = [f"{key} = %s" for key in update_fields.keys()]
    values = list(update_fields.values())
    values.append(product_id)  # Para la cláusula WHERE

    with get_db_cursor(commit=True) as cursor:
        try:
            query = f"""
                UPDATE tbl_producto
                SET {', '.join(set_clauses)}
                WHERE id_producto = %s
                RETURNING id_producto, nombre_producto, descripcion_producto, precio_producto, 
                          fecha_creacion_producto, fecha_modificacion_producto;
            """
            cursor.execute(query, tuple(values))
            updated_product_db = cursor.fetchone()
            if not updated_product_db:
                # El producto no existía
                return None
            return Product(**updated_product_db)
        except psycopg2.IntegrityError as e:
            print(f"Error de integridad al actualizar producto: {e}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflicto al actualizar producto: {e.diag.message_detail or e.pgerror}",
            )
        except psycopg2.Error as e:
            print(f"Error de base de datos (update_product): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de base de datos al actualizar producto: {e.pgerror}",
            )
        except Exception as e:
            print(f"Excepción inesperada (update_product): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ocurrió un error inesperado al actualizar el producto.",
            )


async def delete_product(product_id: int) -> int:
    """
    Elimina un producto de la base de datos.
    Devuelve el número de filas eliminadas (debería ser 1 si se encontró y eliminó, 0 si no).
    """
    with get_db_cursor(commit=True) as cursor:
        try:
            cursor.execute(
                """
                DELETE FROM tbl_producto
                WHERE id_producto = %s;
                """,
                (product_id,),
            )
            # cursor.rowcount te da el número de filas afectadas por la última operación DML
            return cursor.rowcount
        except (
            psycopg2.IntegrityError
        ) as e:  # Específicamente para foreign_key_violation
            if e.pgcode == "23503":  # foreign_key_violation
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"No se puede eliminar el producto: está referenciado en otros registros (ej. pedidos). ({e.diag.message_detail or e.pgerror})",
                )
            print(f"Error de integridad al eliminar producto: {e}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,  # Genérico para otros errores de integridad
                detail=f"Error de integridad al eliminar producto: {e.diag.message_detail or e.pgerror}",
            )
        except psycopg2.Error as e:
            print(f"Error de base de datos (delete_product): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de base de datos al eliminar producto: {e.pgerror}",
            )
        except Exception as e:
            print(f"Excepción inesperada (delete_product): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ocurrió un error inesperado al eliminar el producto.",
            )
