from typing import List
import psycopg2
from database import get_db_cursor
from models.order_model import Pedido, PedidoCreate, OrderItem, OrderItemCreate
from fastapi import HTTPException, status
import datetime

# Estados de pedido (mantén los que ya tienes y añade/ajustar si es necesario)
ESTADO_PEDIDO_PENDIENTE_CONFIRMACION = "pendiente_confirmacion"
ESTADO_PEDIDO_CONFIRMADO_POR_RESTAURANTE = "confirmado_por_restaurante"
ESTADO_PEDIDO_LISTO_PARA_RECOGER = "listo_para_recoger"
ESTADO_PEDIDO_RECOGIDO_POR_REPARTIDOR = "recogido_por_repartidor"
ESTADO_PEDIDO_EN_CAMINO = "en_camino"
ESTADO_PEDIDO_ENTREGADO = "entregado"
ESTADO_PEDIDO_CANCELADO = "cancelado"
# ... otros estados que puedas tener


async def create_order_with_items(order_data: PedidoCreate) -> Pedido:
    """
    Crea un nuevo pedido junto con sus ítems (detalles de venta).
    Verifica que el total_pedido coincida con la suma de los subtotales de los ítems.
    Busca el id_producto basado en nombre_producto.
    Inserta metodo_pago y direccion_entrega en tbl_pedido.
    """
    # 1. Verificar el total_pedido usando los nombres de campo correctos
    calculated_total = sum(
        item.cantidad * item.precio_unitario for item in order_data.items
    )
    if abs(calculated_total - order_data.total_pedido) > 0.01:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El total del pedido ({order_data.total_pedido}) no coincide con el total calculado de los ítems ({calculated_total}).",
        )

    with get_db_cursor(commit=True) as cursor:
        try:
            current_timestamp = datetime.datetime.now()

            sql_insert_pedido = """
                INSERT INTO tbl_pedido (id_cliente, id_restaurante, estado_pedido, total_pedido, fecha_pedido, metodo_pago, direccion_entrega)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id_pedido, id_cliente, id_restaurante, estado_pedido, total_pedido, fecha_pedido, id_repartidor, metodo_pago, direccion_entrega;
            """
            params_pedido = (
                order_data.id_cliente,
                order_data.id_restaurante,
                ESTADO_PEDIDO_PENDIENTE_CONFIRMACION,  # <--- CORREGIDO: Usar directamente el estado por defecto
                order_data.total_pedido,
                current_timestamp,
                order_data.metodo_pago,
                order_data.direccion_entrega,
            )

            cursor.execute(sql_insert_pedido, params_pedido)
            pedido_creado_db = cursor.fetchone()
            if not pedido_creado_db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No se pudo crear el registro del pedido principal.",
                )

            id_pedido_nuevo = pedido_creado_db["id_pedido"]
            order_items_created = []

            # 3. Insertar cada ítem del pedido (tbl_detalles_venta)
            for item_data in order_data.items:
                # Buscar el producto en tbl_producto para obtener su id_producto
                cursor.execute(
                    "SELECT id_producto FROM tbl_producto WHERE nombre_producto = %s LIMIT 1;",
                    (item_data.nombre_producto,),
                )
                producto_en_db = cursor.fetchone()
                if not producto_en_db:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Producto '{item_data.nombre_producto}' no encontrado en tbl_producto.",
                    )
                id_producto_para_detalle = producto_en_db["id_producto"]

                # Insertar en tbl_detalles_venta usando la columna id_producto y cantidad_articulo
                cursor.execute(
                    """
                    INSERT INTO tbl_detalles_venta (id_pedido, id_producto, cantidad_articulo)
                    VALUES (%s, %s, %s)
                    RETURNING id_detalle_venta, id_pedido, id_producto, cantidad_articulo;
                    """,
                    (
                        id_pedido_nuevo,
                        id_producto_para_detalle,  # Este es el id_producto de tbl_producto
                        item_data.cantidad,  # Esta es la cantidad del item
                    ),
                )
                detalle_creado_db = cursor.fetchone()
                if not detalle_creado_db:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"No se pudo crear el detalle para el producto '{item_data.nombre_producto}'.",
                    )

                order_items_created.append(
                    OrderItem(
                        id=detalle_creado_db["id_detalle_venta"],
                        order_id=detalle_creado_db["id_pedido"],
                        # product_id=detalle_creado_db["id_producto"], # Si quieres añadir product_id al modelo OrderItem
                        nombre_producto=item_data.nombre_producto,
                        cantidad=detalle_creado_db[
                            "cantidad_articulo"
                        ],  # Usar la columna correcta de la BD
                        precio_unitario=item_data.precio_unitario,  # Tomado del input, ya que no está en tbl_detalles_venta
                    )
                )

            # Construir el objeto Pedido para la respuesta
            # Ahora metodo_pago y direccion_entrega vienen de pedido_creado_db
            pedido_response = Pedido(
                id_pedido=pedido_creado_db["id_pedido"],
                id_cliente=pedido_creado_db["id_cliente"],
                id_restaurante=pedido_creado_db["id_restaurante"],
                estado_pedido=pedido_creado_db["estado_pedido"],
                total_pedido=pedido_creado_db["total_pedido"],
                fecha_pedido=pedido_creado_db["fecha_pedido"],
                id_repartidor=pedido_creado_db.get("id_repartidor"),
                metodo_pago=pedido_creado_db["metodo_pago"],  # Tomado de la DB
                direccion_entrega=pedido_creado_db[
                    "direccion_entrega"
                ],  # Tomado de la DB
                items=order_items_created,
            )
            return pedido_response

        except psycopg2.Error as e:
            print(
                f"Error de base de datos (create_order_with_items): {e.pgcode} - {e.pgerror} - {e.diag.message_detail if hasattr(e, 'diag') else ''}"
            )
            detail_msg = (
                e.diag.message_detail
                if hasattr(e, "diag") and hasattr(e.diag, "message_detail")
                else str(e.pgerror or e)
            )

            if e.pgcode == "23503":  # foreign_key_violation
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Error de referencia: Verifique los IDs. ({detail_msg})",
                )
            elif e.pgcode == "42703":  # undefined_column
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error de configuración de base de datos: Columna no encontrada. ({detail_msg})",
                )
            elif e.pgcode == "42P01":  # undefined_table
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error de configuración de base de datos: Tabla no encontrada. ({detail_msg})",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de base de datos al crear pedido: {detail_msg}",
            )
        except HTTPException:
            raise
        except Exception as e:
            print(
                f"Excepción inesperada (create_order_with_items): {type(e).__name__} - {e}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ocurrió un error inesperado al crear el pedido: {str(e)}",
            )


async def get_orders_by_client_id(
    client_id: int,
) -> List[Pedido]:  # List[Pedido] en lugar de list[Pedido] es más común
    """
    Recupera todos los pedidos de un cliente específico, incluyendo los detalles de los ítems.
    """
    lista_pedidos_completos: List[Pedido] = []
    # El bloque try principal comienza aquí
    try:  # <--- ASEGÚRATE QUE ESTE 'try' ESTÉ ALINEADO CORRECTAMENTE
        with get_db_cursor() as cursor:
            # 1. Obtener todos los pedidos para el cliente
            cursor.execute(
                """
                SELECT id_pedido, id_cliente, id_restaurante, estado_pedido, total_pedido, 
                       fecha_pedido, id_repartidor, metodo_pago, direccion_entrega
                FROM tbl_pedido
                WHERE id_cliente = %s
                ORDER BY fecha_pedido DESC; 
                """,
                (client_id,),
            )
            pedidos_db = cursor.fetchall()

            if not pedidos_db:
                return []

            for pedido_row in pedidos_db:
                order_items_list: List[OrderItem] = []
                # 2. Para cada pedido, obtener sus ítems y la información del producto
                cursor.execute(
                    """
                    SELECT 
                        dv.id_detalle_venta, 
                        dv.id_pedido, 
                        dv.id_producto, 
                        dv.cantidad_articulo,
                        p.nombre_producto, 
                        p.precio_producto
                    FROM tbl_detalles_venta dv
                    INNER JOIN tbl_producto p ON dv.id_producto = p.id_producto
                    WHERE dv.id_pedido = %s;
                    """,
                    (pedido_row["id_pedido"],),
                )
                detalles_db = cursor.fetchall()

                for detalle_item_row in detalles_db:
                    order_items_list.append(
                        OrderItem(
                            id=detalle_item_row["id_detalle_venta"],
                            order_id=detalle_item_row["id_pedido"],
                            nombre_producto=detalle_item_row["nombre_producto"],
                            cantidad=int(detalle_item_row["cantidad_articulo"]),
                            precio_unitario=float(detalle_item_row["precio_producto"]),
                        )
                    )

                lista_pedidos_completos.append(
                    Pedido(
                        id_pedido=pedido_row["id_pedido"],
                        id_cliente=pedido_row["id_cliente"],
                        id_restaurante=pedido_row["id_restaurante"],
                        estado_pedido=pedido_row["estado_pedido"],
                        total_pedido=float(pedido_row["total_pedido"]),
                        fecha_pedido=pedido_row["fecha_pedido"],
                        id_repartidor=pedido_row.get("id_repartidor"),
                        metodo_pago=pedido_row["metodo_pago"],
                        direccion_entrega=pedido_row["direccion_entrega"],
                        items=order_items_list,
                    )
                )
        # El 'with get_db_cursor()' termina aquí, pero seguimos dentro del 'try' principal
        return lista_pedidos_completos  # Esta línea debe estar indentada al mismo nivel que el 'with'

    # Los bloques except deben estar al mismo nivel de indentación que el 'try' al que pertenecen
    except psycopg2.Error as db_error:
        print(f"Database error in get_orders_by_client_id: {db_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while fetching client orders.",
        )
    except Exception as e:
        print(f"Unexpected error in get_orders_by_client_id: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching client orders.",
        )


# --- MANTÉN TUS FUNCIONES EXISTENTES PARA REPARTIDORES ---
# (get_pedidos_disponibles_para_repartidor, asignar_pedido_a_repartidor, etc.)
# ... (el resto de tu código de servicio para repartidores va aquí)


def get_pedidos_disponibles_para_repartidor():
    """
    Obtiene una lista de pedidos que están listos para ser recogidos
    y aún no tienen un repartidor asignado.
    """
    with get_db_cursor() as cursor:
        try:
            cursor.execute(
                f"""
                SELECT id_pedido, id_cliente, id_restaurante, estado_pedido, total_pedido, fecha_pedido, id_repartidor
                FROM tbl_pedido
                WHERE id_repartidor IS NULL AND estado_pedido = %s; 
                """,
                (ESTADO_PEDIDO_LISTO_PARA_RECOGER,),
            )
            pedidos_db = cursor.fetchall()
            # Convertir a objetos Pedido si es necesario para consistencia, o devolver diccionarios
            # Por simplicidad aquí, devolvemos los diccionarios directamente como antes.
            # Si quieres devolver objetos Pedido, necesitarías también buscar sus items.
            return pedidos_db
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
    Devuelve el objeto Pedido completo.
    """
    with get_db_cursor(commit=True) as cursor:
        try:
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

            if pedido_actual["estado_pedido"] != ESTADO_PEDIDO_LISTO_PARA_RECOGER:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"El pedido no está en estado '{ESTADO_PEDIDO_LISTO_PARA_RECOGER}' para ser asignado/recogido.",
                )

            nuevo_estado_tras_asignacion = ESTADO_PEDIDO_RECOGIDO_POR_REPARTIDOR

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
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No se pudo asignar el pedido después de la actualización.",
                )

            # Obtener los items del pedido para devolver el objeto Pedido completo
            cursor.execute(
                """
                SELECT id_detalle_venta, id_pedido, id_producto, cantidad, precio_unitario, subtotal
                FROM tbl_detalles_venta
                WHERE id_pedido = %s;
                """,
                (id_pedido,),
            )
            detalles_db = cursor.fetchall()
            order_items = [
                OrderItem(
                    id=detalle["id_detalle_venta"],
                    order_id=detalle["id_pedido"],
                    product_id=detalle["id_producto"],
                    quantity=detalle["cantidad"],
                    price=detalle["precio_unitario"],
                )
                for detalle in detalles_db
            ]

            return Pedido(
                id_pedido=pedido_actualizado_db["id_pedido"],
                id_cliente=pedido_actualizado_db["id_cliente"],
                id_restaurante=pedido_actualizado_db["id_restaurante"],
                estado_pedido=pedido_actualizado_db["estado_pedido"],
                total_pedido=pedido_actualizado_db["total_pedido"],
                fecha_pedido=pedido_actualizado_db["fecha_pedido"],
                id_repartidor=pedido_actualizado_db["id_repartidor"],
                items=order_items,
            )

        except psycopg2.Error as e:
            print(f"Error de base de datos (asignar_pedido_a_repartidor): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de base de datos al asignar pedido: {e.pgcode}",
            )
        except HTTPException:
            raise
        except Exception as e:
            print(f"Excepción inesperada (asignar_pedido_a_repartidor): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ocurrió un error inesperado al asignar el pedido.",
            )


# ... (resto de tus funciones para repartidores, adaptándolas si es necesario para que devuelvan objetos Pedido)


def update_estado_pedido_por_repartidor(
    id_pedido: int, id_repartidor_actual: int, nuevo_estado: str
):
    estados_permitidos_repartidor = [
        ESTADO_PEDIDO_EN_CAMINO,
        ESTADO_PEDIDO_ENTREGADO,
    ]
    if nuevo_estado not in estados_permitidos_repartidor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado '{nuevo_estado}' no es válido o no permitido para esta acción.",
        )

    with get_db_cursor(commit=True) as cursor:
        try:
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
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,  # O 500 si es inesperado
                    detail="No se pudo actualizar el estado del pedido o no se encontró el pedido asignado a ti.",
                )

            # Obtener items para devolver el objeto Pedido completo
            cursor.execute(
                """
                SELECT id_detalle_venta, id_pedido, id_producto, cantidad, precio_unitario, subtotal
                FROM tbl_detalles_venta
                WHERE id_pedido = %s;
                """,
                (id_pedido,),
            )
            detalles_db = cursor.fetchall()
            order_items = [
                OrderItem(
                    id=detalle["id_detalle_venta"],
                    order_id=detalle["id_pedido"],
                    product_id=detalle["id_producto"],
                    quantity=detalle["cantidad"],
                    price=detalle["precio_unitario"],
                )
                for detalle in detalles_db
            ]

            return Pedido(
                id_pedido=pedido_actualizado_db["id_pedido"],
                id_cliente=pedido_actualizado_db["id_cliente"],
                id_restaurante=pedido_actualizado_db["id_restaurante"],
                estado_pedido=pedido_actualizado_db["estado_pedido"],
                total_pedido=pedido_actualizado_db["total_pedido"],
                fecha_pedido=pedido_actualizado_db["fecha_pedido"],
                id_repartidor=pedido_actualizado_db["id_repartidor"],
                items=order_items,
            )
        except psycopg2.Error as e:
            print(f"Error de base de datos (update_estado_pedido_por_repartidor): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de base de datos al actualizar estado del pedido: {e.pgcode}",
            )
        except HTTPException:
            raise
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
    Devuelve una lista de objetos Pedido.
    """
    with get_db_cursor() as cursor:
        try:
            cursor.execute(
                """
                SELECT id_pedido, id_cliente, id_restaurante, estado_pedido, total_pedido, fecha_pedido, id_repartidor
                FROM tbl_pedido
                WHERE id_repartidor = %s AND estado_pedido NOT IN (%s, %s);
                """,
                (
                    id_repartidor,
                    ESTADO_PEDIDO_ENTREGADO,
                    ESTADO_PEDIDO_CANCELADO,
                ),
            )
            pedidos_db = cursor.fetchall()

            lista_pedidos_completos = []
            if not pedidos_db:
                return []

            for pedido_row in pedidos_db:
                id_pedido_actual = pedido_row["id_pedido"]
                cursor.execute(
                    """
                    SELECT id_detalle_venta, id_pedido, id_producto, cantidad, precio_unitario, subtotal
                    FROM tbl_detalles_venta
                    WHERE id_pedido = %s;
                    """,
                    (id_pedido_actual,),
                )
                detalles_db = cursor.fetchall()
                order_items = [
                    OrderItem(
                        id=detalle["id_detalle_venta"],
                        order_id=detalle["id_pedido"],
                        product_id=detalle["id_producto"],
                        quantity=detalle["cantidad"],
                        price=detalle["precio_unitario"],
                    )
                    for detalle in detalles_db
                ]

                pedido_completo = Pedido(
                    id_pedido=pedido_row["id_pedido"],
                    id_cliente=pedido_row["id_cliente"],
                    id_restaurante=pedido_row["id_restaurante"],
                    estado_pedido=pedido_row["estado_pedido"],
                    total_pedido=pedido_row["total_pedido"],
                    fecha_pedido=pedido_row["fecha_pedido"],
                    id_repartidor=pedido_row["id_repartidor"],
                    items=order_items,
                )
                lista_pedidos_completos.append(pedido_completo)

            return lista_pedidos_completos
        except Exception as e:
            print(f"Error de base de datos (get_pedidos_asignados_a_repartidor): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al obtener pedidos asignados.",
            )


def get_detalle_pedido_para_repartidor(id_pedido: int, id_repartidor_actual: int):
    """
    Obtiene los detalles de un pedido específico si está asignado al repartidor.
    Devuelve un objeto Pedido.
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

            # Obtener items
            cursor.execute(
                """
                SELECT id_detalle_venta, id_pedido, id_producto, cantidad, precio_unitario, subtotal
                FROM tbl_detalles_venta
                WHERE id_pedido = %s;
                """,
                (id_pedido,),
            )
            detalles_db = cursor.fetchall()
            order_items = [
                OrderItem(
                    id=detalle["id_detalle_venta"],
                    order_id=detalle["id_pedido"],
                    product_id=detalle["id_producto"],
                    quantity=detalle["cantidad"],
                    price=detalle["precio_unitario"],
                )
                for detalle in detalles_db
            ]

            return Pedido(
                id_pedido=pedido_db["id_pedido"],
                id_cliente=pedido_db["id_cliente"],
                id_restaurante=pedido_db["id_restaurante"],
                estado_pedido=pedido_db["estado_pedido"],
                total_pedido=pedido_db["total_pedido"],
                fecha_pedido=pedido_db["fecha_pedido"],
                id_repartidor=pedido_db["id_repartidor"],
                items=order_items,
            )
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error de base de datos (get_detalle_pedido_para_repartidor): {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al obtener detalle del pedido.",
            )
