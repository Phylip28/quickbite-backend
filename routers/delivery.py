from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from pydantic import BaseModel

# Modelos Pydantic
from models.delivery_model import (
    RepartidorCreate,
    Repartidor,
    RepartidorLogin,
    TokenRepartidor,
    TokenDataRepartidor,
    RepartidorUpdate,
)
from models.order_model import (
    Pedido,
    PedidoUpdate,
)  # Asumiendo que PedidoUpdate puede usarse para actualizar estado o crear un modelo específico

# Servicios
from services import delivery_service, order_service

# Middleware de autenticación
from middleware.authenticator import get_current_repartidor

router = APIRouter(
    # prefix="/api/repartidores",  # Prefijo para todas las rutas en este router
    tags=["Repartidores"],  # Etiqueta para la documentación de Swagger/OpenAPI
)

# --- Endpoints de Autenticación y Gestión de Repartidores ---


@router.post(
    "/register", response_model=Repartidor, status_code=status.HTTP_201_CREATED
)
async def register_repartidor(repartidor_data: RepartidorCreate):
    """
    Registra un nuevo repartidor en el sistema.
    """
    try:
        # El servicio create_repartidor ya debería hashear la contraseña
        nuevo_repartidor = await delivery_service.create_repartidor(repartidor_data)
        if not nuevo_repartidor:
            # Esta condición podría ser más específica si el servicio devuelve None en ciertos errores
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo registrar el repartidor, correo podría ya existir.",
            )
        return nuevo_repartidor
    except HTTPException as http_exc:
        raise http_exc  # Re-lanzar HTTPExceptions que ya vienen del servicio
    except Exception as e:
        # Captura de excepciones generales del servicio que no son HTTPException
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/login", response_model=TokenRepartidor)
async def login_repartidor(form_data: RepartidorLogin):
    """
    Autentica a un repartidor y devuelve un token de acceso.
    Este es el endpoint que se usa en `tokenUrl` de OAuth2PasswordBearer.
    """
    try:
        token_data = await delivery_service.authenticate_repartidor(
            correo_repartidor=form_data.correo_repartidor,
            contrasenia=form_data.contrasenia,
        )
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo o contraseña incorrectos para el repartidor",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token_data  # El servicio ya debería devolver el modelo TokenRepartidor
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/me", response_model=Repartidor)
async def read_repartidores_me(
    current_repartidor_token: TokenDataRepartidor = Depends(get_current_repartidor),
):
    """
    Obtiene la información del repartidor actualmente autenticado.
    """
    repartidor = await delivery_service.get_repartidor_by_id(
        current_repartidor_token.id_repartidor
    )
    if not repartidor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repartidor no encontrado."
        )
    return repartidor


@router.put("/me/update", response_model=Repartidor)
async def update_repartidor_me(
    repartidor_update_data: RepartidorUpdate,
    current_repartidor_token: TokenDataRepartidor = Depends(get_current_repartidor),
):
    """
    Actualiza la información del repartidor actualmente autenticado.
    La contraseña no se actualiza aquí; requeriría un endpoint separado.
    """
    try:
        updated_repartidor = await delivery_service.update_repartidor(
            id_repartidor=current_repartidor_token.id_repartidor,
            repartidor_update=repartidor_update_data,
        )
        if not updated_repartidor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repartidor no encontrado para actualizar.",
            )
        return updated_repartidor
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# --- Endpoints de Gestión de Pedidos para Repartidores ---


@router.get("/pedidos/disponibles", response_model=List[Pedido])
async def get_pedidos_disponibles(
    current_repartidor_token: TokenDataRepartidor = Depends(
        get_current_repartidor
    ),  # Asegura que solo repartidores autenticados accedan
):
    """
    Obtiene una lista de pedidos disponibles para ser recogidos por un repartidor.
    """
    try:
        # El id del repartidor actual no es necesario para esta función específica,
        # pero la dependencia asegura que el usuario es un repartidor autenticado.
        pedidos = await order_service.get_pedidos_disponibles_para_repartidor()
        return pedidos
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/pedidos/{id_pedido}/aceptar", response_model=Pedido)
async def aceptar_pedido(
    id_pedido: int,
    current_repartidor_token: TokenDataRepartidor = Depends(get_current_repartidor),
):
    """
    Permite a un repartidor autenticado aceptar/asignarse un pedido disponible.
    """
    try:
        pedido_asignado = await order_service.asignar_pedido_a_repartidor(
            id_pedido=id_pedido, id_repartidor=current_repartidor_token.id_repartidor
        )
        return pedido_asignado
    except HTTPException as http_exc:
        raise http_exc  # Re-lanzar HTTPExceptions que ya vienen del servicio (404, 409, etc.)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Modelo para actualizar solo el estado del pedido
class PedidoEstadoUpdate(BaseModel):
    nuevo_estado: str


@router.patch("/pedidos/{id_pedido}/estado", response_model=Pedido)
async def actualizar_estado_pedido(
    id_pedido: int,
    estado_update: PedidoEstadoUpdate,  # Recibe el nuevo estado desde el body
    current_repartidor_token: TokenDataRepartidor = Depends(get_current_repartidor),
):
    """
    Permite a un repartidor actualizar el estado de un pedido que tiene asignado.
    (ej. 'en_camino', 'entregado')
    """
    try:
        pedido_actualizado = await order_service.update_estado_pedido_por_repartidor(
            id_pedido=id_pedido,
            id_repartidor_actual=current_repartidor_token.id_repartidor,
            nuevo_estado=estado_update.nuevo_estado,
        )
        return pedido_actualizado
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/pedidos/mis-asignados", response_model=List[Pedido])
async def get_mis_pedidos_asignados(
    current_repartidor_token: TokenDataRepartidor = Depends(get_current_repartidor),
):
    """
    Obtiene la lista de pedidos actualmente asignados al repartidor autenticado.
    """
    try:
        pedidos = await order_service.get_pedidos_asignados_a_repartidor(
            id_repartidor=current_repartidor_token.id_repartidor
        )
        return pedidos
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/pedidos/{id_pedido}/detalle", response_model=Pedido)
async def get_mi_detalle_pedido(
    id_pedido: int,
    current_repartidor_token: TokenDataRepartidor = Depends(get_current_repartidor),
):
    """
    Obtiene los detalles de un pedido específico si está asignado al repartidor autenticado.
    """
    try:
        pedido = await order_service.get_detalle_pedido_para_repartidor(
            id_pedido=id_pedido,
            id_repartidor_actual=current_repartidor_token.id_repartidor,
        )
        # El servicio ya debería lanzar HTTPException 404 o 403 si es necesario
        return pedido
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Podrías añadir más endpoints según necesidad, como:
# - Ver historial de pedidos entregados por el repartidor.
# - Actualizar disponibilidad del repartidor (si no se hace en /me/update).
