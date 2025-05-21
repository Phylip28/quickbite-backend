from database import get_db_cursor
from models.order_model import Pedido  # Importamos el modelo Pydantic para Pedido
from fastapi import HTTPException, status
import psycopg2

# Estados de pedido que podrías estar usando (ajusta según tu sistema)
# Es buena idea definirlos como constantes si los usas en múltiples lugares.
ESTADO_PEDIDO_LISTO_PARA_RECOGER = (
    "listo_para_recoger"  # Ejemplo: El restaurante lo marcó como listo
)
ESTADO_PEDIDO_RECOGIDO_POR_REPARTIDOR = "recogido_por_repartidor"
ESTADO_PEDIDO_EN_CAMINO = "en_camino"
ESTADO_PEDIDO_ENTREGADO = "entregado"
ESTADO_PEDIDO_PENDIENTE_ASIGNACION = (
    "pendiente_asignacion_repartidor"  # Un estado posible antes de 'listo_para_recoger'
)


def get_pedidos_disponibles_para_repartidor():
    """
    Obtiene una lista de pedidos que están listos para ser recogidos
    y aún no tienen un repartidor asignado.
    """
    with get_db_cursor() as cursor:
        try:
            # La condición para "disponible" puede variar.
            # Aquí asumimos que un pedido está disponible si:
            # 1. id_repartidor ES NULL
            # 2. estado_pedido es algo como 'listo_para_recoger' o 'pendiente_asignacion_repartidor'
            # Ajusta la consulta SQL según tus estados de pedido.
            cursor.execute(
                f"""
                SELECT id_pedido, id_cliente, id_restaurante, estado_pedido, total_pedido, fecha_pedido, id_repartidor
                FROM tbl_pedido
                WHERE id_repartidor IS NULL AND estado_pedido = %s;
                """,
                (
                    ESTADO_PEDIDO_LISTO_PARA_RECOGER,
                ),  # O el estado que uses para "listo y sin repartidor"
            )
            pedidos_db = cursor.fetchall()
            return pedidos_db  # Lista de diccionarios de pedidos
        except Exception as e:
            print(
                f"Error de base de datos (get_pedidos_disponibles_para_repartidor): {e}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al obtener pedidos disponibles.",
            )


def asignar_pedido_a_repartidor(id_pedido: int, id_repartidor: int):
    """
    Asigna un pedido a un repartidor y actualiza su estado.
    """
    with get_db_cursor(commit=True) as cursor:
        try:
            # Primero, verificar que el pedido esté realmente disponible para ser asignado
            cursor.execute(
                """
                SELECT id_repartidor, estado_pedido
                FROM tbl_pedido
                WHERE id_pedido = %s;
                """,
                (id_pedido,),
            )
            pedido_actual = cursor.fetchone()

            if not pedido_actual:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pedido no encontrado.",
                )

            if pedido_actual["id_repartidor"] is not None:
                if pedido_actual["id_repartidor"] == id_repartidor:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Ya tienes este pedido asignado.",
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="El pedido ya ha sido asignado a otro repartidor.",
                    )

            # Ajusta esta lógica de estado según tu flujo.
            # Por ejemplo, si el estado era 'listo_para_recoger', ahora podría ser 'recogido_por_repartidor'.
            if pedido_actual["estado_pedido"] != ESTADO_PEDIDO_LISTO_PARA_RECOGER:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"El pedido no está en estado '{ESTADO_PEDIDO_LISTO_PARA_RECOGER}' para ser asignado/recogido.",
                )

            nuevo_estado_tras_asignacion = (
                ESTADO_PEDIDO_RECOGIDO_POR_REPARTIDOR  # O el estado apropiado
            )

            cursor.execute(
                """
                UPDATE tbl_pedido
                SET id_repartidor = %s, estado_pedido = %s
                WHERE id_pedido = %s
                RETURNING id_pedido, id_cliente, id_restaurante, estado_pedido, total_pedido, fecha_pedido, id_repartidor;
                """,
                (id_repartidor, nuevo_estado_tras_asignacion, id_pedido),
            )
            pedido_actualizado_db = cursor.fetchone()

            if not pedido_actualizado_db:
                # Esto no debería pasar si las verificaciones anteriores fueron correctas
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No se pudo asignar el pedido después de la actualización.",
                )
            return pedido_actualizado_db
        except psycopg2.Error as e:
            print(f"Error de base de datos (asignar_pedido_a_repartidor): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de base de datos al asignar pedido: {e.pgcode}",
            )
        except HTTPException:
            raise  # Re-lanza las HTTPExceptions que ya hemos lanzado
        except Exception as e:
            print(f"Excepción inesperada (asignar_pedido_a_repartidor): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ocurrió un error inesperado al asignar el pedido.",
            )


def update_estado_pedido_por_repartidor(
    id_pedido: int, id_repartidor_actual: int, nuevo_estado: str
):
    """
    Permite a un repartidor actualizar el estado de un pedido que tiene asignado.
    """
    # Validar que el nuevo_estado sea uno de los permitidos para repartidores
    estados_permitidos_repartidor = [
        ESTADO_PEDIDO_EN_CAMINO,
        ESTADO_PEDIDO_ENTREGADO,
    ]  # Añade otros si es necesario
    if nuevo_estado not in estados_permitidos_repartidor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado '{nuevo_estado}' no es válido o no permitido para esta acción.",
        )

    with get_db_cursor(commit=True) as cursor:
        try:
            # Verificar que el pedido existe y está asignado al repartidor correcto
            cursor.execute(
                """
                SELECT id_repartidor, estado_pedido
                FROM tbl_pedido
                WHERE id_pedido = %s;
                """,
                (id_pedido,),
            )
            pedido_actual = cursor.fetchone()

            if not pedido_actual:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pedido no encontrado.",
                )

            if pedido_actual["id_repartidor"] != id_repartidor_actual:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para actualizar este pedido o no te ha sido asignado.",
                )

            # Aquí podrías añadir lógica para validar transiciones de estado
            # Por ejemplo, no se puede pasar de 'recogido' a 'recogido' de nuevo, o de 'entregado' a 'en_camino'.
            # if pedido_actual["estado_pedido"] == ESTADO_PEDIDO_ENTREGADO and nuevo_estado != ESTADO_PEDIDO_ENTREGADO:
            #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El pedido ya fue entregado.")
            # if pedido_actual["estado_pedido"] == ESTADO_PEDIDO_RECOGIDO_POR_REPARTIDOR and nuevo_estado != ESTADO_PEDIDO_EN_CAMINO:
            #     # etc.

            cursor.execute(
                """
                UPDATE tbl_pedido
                SET estado_pedido = %s
                WHERE id_pedido = %s AND id_repartidor = %s
                RETURNING id_pedido, id_cliente, id_restaurante, estado_pedido, total_pedido, fecha_pedido, id_repartidor;
                """,
                (nuevo_estado, id_pedido, id_repartidor_actual),
            )
            pedido_actualizado_db = cursor.fetchone()

            if not pedido_actualizado_db:
                # Podría ocurrir si, por alguna razón, el id_repartidor no coincidió en el UPDATE
                # aunque la verificación previa pasó.
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No se pudo actualizar el estado del pedido o no se encontró el pedido asignado a ti.",
                )
            return pedido_actualizado_db
        except psycopg2.Error as e:
            print(f"Error de base de datos (update_estado_pedido_por_repartidor): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de base de datos al actualizar estado del pedido: {e.pgcode}",
            )
        except HTTPException:
            raise  # Re-lanza las HTTPExceptions que ya hemos lanzado
        except Exception as e:
            print(f"Excepción inesperada (update_estado_pedido_por_repartidor): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ocurrió un error inesperado al actualizar el estado del pedido.",
            )


def get_pedidos_asignados_a_repartidor(id_repartidor: int):
    """
    Obtiene una lista de pedidos actualmente asignados a un repartidor específico
    que no han sido marcados como 'entregado' o 'cancelado'.
    """
    with get_db_cursor() as cursor:
        try:
            # Excluir pedidos ya entregados o cancelados (ajusta según tus estados)
            cursor.execute(
                """
                SELECT id_pedido, id_cliente, id_restaurante, estado_pedido, total_pedido, fecha_pedido, id_repartidor
                FROM tbl_pedido
                WHERE id_repartidor = %s AND estado_pedido NOT IN (%s, %s);
                """,
                (
                    id_repartidor,
                    ESTADO_PEDIDO_ENTREGADO,
                    "cancelado",
                ),  # Asume que tienes un estado 'cancelado'
            )
            pedidos_db = cursor.fetchall()
            return pedidos_db
        except Exception as e:
            print(f"Error de base de datos (get_pedidos_asignados_a_repartidor): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al obtener pedidos asignados.",
            )


def get_detalle_pedido_para_repartidor(id_pedido: int, id_repartidor_actual: int):
    """
    Obtiene los detalles de un pedido específico si está asignado al repartidor.
    """
    with get_db_cursor() as cursor:
        try:
            cursor.execute(
                """
                SELECT id_pedido, id_cliente, id_restaurante, estado_pedido, total_pedido, fecha_pedido, id_repartidor
                FROM tbl_pedido
                WHERE id_pedido = %s AND id_repartidor = %s;
                """,
                (id_pedido, id_repartidor_actual),
            )
            pedido_db = cursor.fetchone()
            if not pedido_db:
                # Podría ser que el pedido no exista o no esté asignado a este repartidor
                cursor.execute(
                    "SELECT id_repartidor FROM tbl_pedido WHERE id_pedido = %s;",
                    (id_pedido,),
                )
                existe_pedido = cursor.fetchone()
                if not existe_pedido:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Pedido no encontrado.",
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Este pedido no te ha sido asignado.",
                    )
            return pedido_db
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error de base de datos (get_detalle_pedido_para_repartidor): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al obtener detalle del pedido.",
            )


# Si tienes una tabla de detalles de venta (tbl_detalles_venta) y quieres incluirla:
# def get_detalle_pedido_con_productos_para_repartidor(id_pedido: int, id_repartidor_actual: int):
#     pedido_info = get_detalle_pedido_para_repartidor(id_pedido, id_repartidor_actual) # Reutiliza la función anterior para validación
#     if not pedido_info:
#         # La excepción ya fue lanzada por la función anterior
#         return None

#     with get_db_cursor() as cursor:
#         try:
#             cursor.execute(
#                 """
#                 SELECT id_detalle_venta, id_producto, cantidad, precio_unitario, subtotal -- y otros campos de tbl_detalles_venta
#                 FROM tbl_detalles_venta
#                 WHERE id_pedido = %s;
#                 """,
#                 (id_pedido,)
#             )
#             detalles_productos = cursor.fetchall()
#             pedido_info["detalles_productos"] = detalles_productos # Añade la lista de productos al diccionario del pedido
#             return pedido_info
#         except Exception as e:
#             print(f"Error de base de datos (get_detalle_pedido_con_productos_para_repartidor): {e}")
#             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
