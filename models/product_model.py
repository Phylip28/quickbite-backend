from pydantic import BaseModel
from typing import Optional


class ProductBase(BaseModel):
    name: str
    price: float
    # Considera añadir otros campos que puedas necesitar, como:
    # description: Optional[str] = None
    # image_url: Optional[str] = None
    # restaurant_id: int # Si los productos están vinculados a restaurantes


class ProductCreate(ProductBase):
    pass


class Product(ProductBase):
    id: int  # Asumiendo que el ID es un entero y se genera en la BD

    class Config:
        from_attributes = True  # Cambiado de orm_mode para Pydantic v2+


# --- AÑADIR ESTA CLASE ---
class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    # description: Optional[str] = None
    # image_url: Optional[str] = None
    # restaurant_id: Optional[int] = None
    # Añade aquí cualquier otro campo de ProductBase que quieras que sea actualizable

    class Config:
        from_attributes = True  # Cambiado de orm_mode para Pydantic v2+


# --- FIN DE LA ADICIÓN ---
