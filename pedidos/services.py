import uuid
import logging
from datetime import datetime
from django.db import transaction
from django.conf import settings

from gestion.models import CabeceraPedido, GuiaDespacho, EstadoPedido
from gestion.repositories.pedidos_repositories import PedidoRepository, BodegaRepository, GuiaDespachoRepository
from gestion.factories import PedidoFactoryProvider
from gestion.circuit_breaker.pedidos_circuitbreaker import inventario_cb, CircuitBreakerAbierto, CircuitBreakerFallo

logger = logging.getLogger(__name__)


class PedidoService:

    def __init__(self):
        self.repository       = PedidoRepository()
        self.bodega_repo      = BodegaRepository()
        self.guia_repo        = GuiaDespachoRepository()


    # Verificación de stock (Circuit Breaker)

    def _verificar_stock(self, sku: str, cantidad: int) -> None:
        
        url = f"{settings.MS_INVENTARIO_URL}/api/inventario/stock/{sku}/"
        try:
            data = inventario_cb.llamar(url)
            stock_disponible = data.get('cantidad', 0)
            if stock_disponible < cantidad:
                raise ValueError(
                    f"Stock insuficiente para SKU '{sku}'. "
                    f"Disponible: {stock_disponible}, Solicitado: {cantidad}."
                )
        except CircuitBreakerAbierto:
            raise ValueError(
                "El servicio de inventario no está disponible. Intente más tarde."
            )
        except CircuitBreakerFallo as e:
            raise ValueError(f"No se pudo verificar inventario del SKU '{sku}': {e}")

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

        cliente_uuid = uuid.UUID(cliente_id)

        for item in items:
            self._verificar_stock(item['sku'], item['cantidad'])

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
        from models import GuiaDespacho

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