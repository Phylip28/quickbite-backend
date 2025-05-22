from pydantic import BaseModel
from typing import Optional, List
import datetime


# --- Modelos para los Items del Pedido ---
class OrderItemBase(BaseModel):
    nombre_producto: str
    cantidad: int
    precio_unitario: float


class OrderItemCreate(OrderItemBase):
    pass


class OrderItem(OrderItemBase):
    id: int
    order_id: int

    class Config:
        from_attributes = True


# --- Modelos para el Pedido ---
class PedidoBase(BaseModel):
    id_cliente: int
    id_restaurante: int
    total_pedido: float
    metodo_pago: str
    direccion_entrega: str


class PedidoCreate(PedidoBase):
    items: List[OrderItemCreate]


class Pedido(PedidoBase):
    id_pedido: int
    fecha_pedido: datetime.datetime
    estado_pedido: str
    id_repartidor: Optional[int] = None
    items: List["OrderItem"] = []  # <--- CAMBIO: Usar string para la forward reference

    class Config:
        from_attributes = True


# Si estás usando Pydantic v1, podrías necesitar esto al final del archivo,
# aunque Pydantic v2 generalmente no lo requiere.
# Pedido.update_forward_refs() # Descomenta si es necesario para Pydantic v1


class PedidoUpdate(BaseModel):
    estado_pedido: Optional[str] = None
    id_repartidor: Optional[int] = None
