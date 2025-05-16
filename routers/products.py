from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/products")
async def get_products():
    # Aquí va la lógica para obtener los productos de tu base de datos
    return {"message": "List of products"}


# Define más rutas para productos aquí usando el objeto 'router'
# @router.post("/products")
# async def create_product(product: ProductModel):
#     ...
