from pydantic import BaseModel
from typing import Optional, List
import datetime


# Modelo base para los campos comunes de un pedido
class PedidoBase(BaseModel):
    id_cliente: int
    id_restaurante: int
    estado_pedido: Optional[str] = (
        "pendiente_confirmacion"  # Valor por defecto si aplica
    )
    total_pedido: float  # numeric(10,2) se puede representar como float


# Modelo para crear un nuevo pedido
# Podrías necesitar más campos aquí dependiendo de tu lógica de creación,
# por ejemplo, una lista de productos del pedido.
# Por ahora, lo mantenemos simple.
class PedidoCreate(PedidoBase):
    # Ejemplo: si los detalles del pedido vienen en la creación
    # detalles: Optional[List[DetallePedidoCreate]] = None # Necesitarías definir DetallePedidoCreate
    pass


# Modelo para representar un pedido en las respuestas de la API
class Pedido(PedidoBase):
    id_pedido: int
    fecha_pedido: datetime.datetime  # Coincide con 'timestamp with time zone'
    id_repartidor: Optional[int] = None  # Campo para el repartidor asignado

    class Config:
        from_attributes = True  # Para Pydantic V2
        # orm_mode = True # Para Pydantic V1 si usas esa versión


# Modelo para actualizar un pedido (ej. cambiar estado o asignar repartidor)
class PedidoUpdate(BaseModel):
    estado_pedido: Optional[str] = None
    id_repartidor: Optional[int] = (
        None  # Para permitir asignar/desasignar un repartidor
    )
    # Puedes añadir otros campos que se puedan actualizar


# Si tienes una tabla de detalles de pedido (tbl_detalles_venta),
# también necesitarías modelos para ella. Por ejemplo:
# class DetalleVentaBase(BaseModel):
#     id_producto: int
#     cantidad: int
#     precio_unitario: float
#     subtotal: float

# class DetalleVentaCreate(DetalleVentaBase):
#     pass

# class DetalleVenta(DetalleVentaBase):
#     id_detalle_venta: int
#     id_pedido: int # Para vincularlo al pedido

#     class Config:
#         from_attributes = True
#         # orm_mode = True

# Y luego podrías tener un modelo de Pedido con sus detalles:
# class PedidoConDetalles(Pedido):
#    detalles: List[DetalleVenta] = []
