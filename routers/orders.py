from fastapi import APIRouter, HTTPException, Depends, status
from typing import List

# --- IMPORTACIÓN CORRECTA ---
from models.user_model import (
    TokenDataUser,
)  # <--- CORREGIDO: Apunta a models/user_model.py

from middleware.authenticator import get_current_user
from models.order_model import Pedido, PedidoCreate
from services import order_service

router = APIRouter(tags=["Orders"])


@router.post(
    "/",
    response_model=Pedido,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_order(
    order_data: PedidoCreate,
    current_user: TokenDataUser = Depends(get_current_user),  # <--- TIPO CORRECTO
):
    """
    Crea un nuevo pedido para el usuario autenticado.
    """
    try:
        # --- ATRIBUTO CORRECTO ---
        # El ID del usuario en TokenDataUser se llama 'user_id' según tu authenticator.py
        client_id_from_token_str = (
            current_user.user_id
        )  # <--- CORREGIDO: Usa current_user.user_id

        if not client_id_from_token_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate user credentials for order creation (token invalid or missing user ID).",
            )

        # El ID del token (client_id_from_token_str) es un string.
        # order_data.id_cliente es un int.
        if order_data.id_cliente != int(client_id_from_token_str):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Order client ID ({order_data.id_cliente}) does not match authenticated user ID ({client_id_from_token_str}).",
            )

        created_order = await order_service.create_order_with_items(
            order_data=order_data,
        )

        if not created_order:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create the order due to an internal issue.",
            )
        return created_order
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error creating order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while creating the order: {str(e)}",
        )


@router.get("/", response_model=List[Pedido])
async def get_user_orders(
    current_user: TokenDataUser = Depends(get_current_user),
):  # <--- TIPO CORRECTO
    """
    Obtiene todos los pedidos para el usuario autenticado.
    """
    try:
        # --- ATRIBUTO CORRECTO ---
        client_id_from_token_str = (
            current_user.user_id
        )  # <--- CORREGIDO: Usa current_user.user_id

        if not client_id_from_token_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate user credentials (token invalid or missing user ID).",
            )

        orders = await order_service.get_orders_by_client_id(
            client_id=int(client_id_from_token_str)
        )
        return orders
    except Exception as e:
        print(f"Error fetching orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while fetching orders: {str(e)}",
        )


@router.get(
    "/client/{client_id_param}",
    response_model=List[Pedido],
)  # CAMBIO DE RUTA
async def get_user_orders_by_client_id_param(  # Nombre de función cambiado para claridad
    client_id_param: int,  # El ID de la ruta
    current_user: TokenDataUser = Depends(get_current_user),
):
    """
    Obtiene todos los pedidos para un ID de cliente específico,
    verificando la autorización del usuario autenticado.
    """
    try:
        client_id_from_token = int(current_user.user_id)

        if not current_user.user_id:  # Ya es un string, no necesita ser None
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate user credentials (token invalid or missing user ID).",
            )

        # Autorización: El usuario solo puede ver sus propios pedidos
        # (a menos que implementes roles de administrador más adelante)
        if client_id_from_token != client_id_param:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view these orders.",
            )

        orders = await order_service.get_orders_by_client_id(
            client_id=client_id_param  # Usa el client_id de la ruta para la consulta
        )
        return orders
    except HTTPException as e:  # Re-lanzar HTTPExceptions conocidas
        raise e
    except Exception as e:
        print(f"Error fetching orders for client {client_id_param}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while fetching orders: {str(e)}",
        )


# ... (otras rutas si las tienes)
