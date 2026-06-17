import uuid
import logging
from datetime import datetime
from django.db import transaction

from pedidos.models import CabeceraPedido, GuiaDespacho, EstadoPedido
from pedidos.repositories import PedidoRepository, BodegaRepository, GuiaDespachoRepository
from pedidos.factories import PedidoFactoryProvider
import httpx
logger = logging.getLogger(__name__)


class PedidoService:

    def __init__(self):
        self.repository       = PedidoRepository()
        self.bodega_repo      = BodegaRepository()
        self.guia_repo        = GuiaDespachoRepository()


    # Verificación de stock (delegada al BFF)

    # Crear pedido

    @transaction.atomic
    def crear_pedido(
        self,
        cliente_id: str,
        destinatario: dict,
        items: list,
        tipo: str = 'estandar',
        notas: str = None,
    ) -> CabeceraPedido:

        try:
            cliente_uuid = uuid.UUID(cliente_id)
        except (ValueError, AttributeError):
            logger.warning(f"cliente_id inválido, generando UUID automático: {cliente_id}")
            cliente_uuid = uuid.uuid4()

        factory = PedidoFactoryProvider.obtener_factory(tipo, self.repository, self.bodega_repo)
        pedido = factory.crear_pedido(
            cliente_id=cliente_uuid,
            destinatario=destinatario,
            items=items,
            notas=notas,
        )

        logger.info(f"[PedidoService] Creado: ID={pedido.id} Tipo={tipo} Total={pedido.total}")
        return pedido


    # Transiciones de estado del pedido (ciclo de vida)
    # Secuencia válida: Pendiente → Aprobado → Enviado → Entregado


    def aprobar_pedido(self, pedido_id: str) -> CabeceraPedido:
        pedido = self._obtener_o_error(pedido_id)
        if pedido.estado != EstadoPedido.PENDIENTE:
            raise ValueError(
                f"Solo se puede aprobar un pedido en estado 'Pendiente'. "
                f"Estado actual: '{pedido.estado}'."
            )
        return self.repository.cambiar_estado(pedido, EstadoPedido.APROBADO)

    def enviar_pedido(self, pedido_id: str) -> CabeceraPedido:
        pedido = self._obtener_o_error(pedido_id)
        if pedido.estado != EstadoPedido.APROBADO:
            raise ValueError(
                f"Solo se puede enviar un pedido en estado 'Aprobado'. "
                f"Estado actual: '{pedido.estado}'."
            )
        return self.repository.cambiar_estado(pedido, EstadoPedido.ENVIADO)

    def entregar_pedido(self, pedido_id: str) -> CabeceraPedido:

        pedido = self._obtener_o_error(pedido_id)
        if pedido.estado != EstadoPedido.ENVIADO:
            raise ValueError(
                f"Solo se puede entregar un pedido en estado 'Enviado'. "
                f"Estado actual: '{pedido.estado}'."
            )
        return self.repository.cambiar_estado(pedido, EstadoPedido.ENTREGADO)


    # Guía de Despacho


    @transaction.atomic
    def generar_guia_despacho(self, pedido_id: str) -> GuiaDespacho:

        pedido = self._obtener_o_error(pedido_id)

        if pedido.estado != EstadoPedido.APROBADO:
            raise ValueError(
                "La guía de despacho solo se puede generar para pedidos en estado 'Aprobado'."
            )

        guia_existente = self.guia_repo.obtener_por_pedido(pedido.id)
        if guia_existente:
            raise ValueError(
                f"Ya existe una guía de despacho para este pedido: {guia_existente.numero_guia}."
            )

        numero_guia = self._generar_numero_guia()
        return self.guia_repo.crear(pedido=pedido, numero_guia=numero_guia)

    def obtener_guia(self, pedido_id: str) -> GuiaDespacho:
        guia = self.guia_repo.obtener_por_pedido(uuid.UUID(pedido_id))
        if not guia:
            raise ValueError(f"No existe guía de despacho para el pedido '{pedido_id}'.")
        return guia


    # Consultas

    def obtener_pedido(self, pedido_id: str) -> CabeceraPedido:
        return self._obtener_o_error(pedido_id)

    def listar_pedidos(self, cliente_id: str = None) -> list:
        if cliente_id:
            return self.repository.listar_por_cliente(uuid.UUID(cliente_id))
        return self.repository.listar_todos()

    def listar_bodegas(self) -> list:
        return self.bodega_repo.listar_activas()

    # Helpers privados

    def _obtener_o_error(self, pedido_id: str) -> CabeceraPedido:
        pedido = self.repository.obtener_por_id(uuid.UUID(pedido_id))
        if not pedido:
            raise ValueError(f"Pedido con ID '{pedido_id}' no encontrado.")
        return pedido

    def _generar_numero_guia(self) -> str:

        from django.db.models import Max
        from pedidos.models import GuiaDespacho

        anio = datetime.now().year
        max_num = GuiaDespacho.objects.filter(
            numero_guia__startswith=f"GD-{anio}-"
        ).aggregate(max=Max('numero_guia'))['max']

        if max_num:
            ultimo_num = int(max_num.split('-')[-1])
        else:
            ultimo_num = 0

        nuevo_num = ultimo_num + 1
        return f"GD-{anio}-{nuevo_num:05d}"
    
URL_MS_INVENTARIO = "http://127.0.0.1:8002/api/productos/"  # Ajusta el puerto de tu MS de Inventario

def consultar_producto_en_inventario(sku: str):
    """
    Va al MS de Inventario a verificar si el SKU existe y traer sus datos (nombre, precio, bodega)
    """
    try:
        # Hacemos la petición filtrando por el SKU
        response = httpx.get(f"{URL_MS_INVENTARIO}?sku={sku}", timeout=3.0)
        
        if response.status_code == 200:
            datos = response.json()
            # Si tu API de inventario devuelve una lista, sacamos el primer elemento
            if isinstance(datos, list) and len(datos) > 0:
                return datos[0]
            return datos
    except httpx.RequestError:
        return None
    return None