from fastapi import APIRouter, HTTPException, Depends
from middleware.authenticator import get_current_user

router = APIRouter()


@router.get("/orders", dependencies=[Depends(get_current_user)])
async def get_orders(current_user: dict = Depends(get_current_user)):
    # Aquí va la lógica para obtener las órdenes del usuario autenticado
    return {"message": f"List of orders for user {current_user['user_id']}"}


# Define más rutas para órdenes aquí usando el objeto 'router'
# @router.post("/orders")
# async def create_order(order: OrderModel, current_user: dict = Depends(get_current_user)):
#     ...
