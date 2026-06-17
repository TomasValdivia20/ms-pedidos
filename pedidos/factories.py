import uuid
from abc import ABC, abstractmethod

from pedidos.models import CabeceraPedido
from pedidos.repositories import PedidoRepository, BodegaRepository


class PedidoFactory(ABC):

    def __init__(self, repository: PedidoRepository, bodega_repo: BodegaRepository):
        self.repository  = repository
        self.bodega_repo = bodega_repo

    @abstractmethod
    def crear_pedido(
        self,
        cliente_id: uuid.UUID,
        destinatario: dict,
        items: list,
        notas: str = None,
    ) -> CabeceraPedido:
        pass

    def _construir_detalles(self, pedido: CabeceraPedido, items: list) -> CabeceraPedido:
        for item in items:
            try:
                bodega = self.bodega_repo.obtener_por_id(uuid.UUID(item['bodega_origen_id']))
            except (ValueError, AttributeError):
                bodega = None
            if not bodega:
                disponibles = self.bodega_repo.listar_activas()
                bodega = disponibles[0] if disponibles else None
                if not bodega:
                    raise ValueError("No hay bodegas activas disponibles para asignar al detalle.")
            self.repository.agregar_detalle(
                pedido=pedido,
                nombre_producto=item['nombre_producto'],
                sku=item['sku'],
                tipo_carga=item['tipo_carga'],
                cantidad=item['cantidad'],
                precio_unitario=item['precio_unitario'],
                bodega_origen=bodega,
                hora_retiro=item['hora_retiro'],
                hora_despacho=item['hora_despacho'],
                direccion_entrega=item['direccion_entrega'],
                codigo_postal_entrega=item['codigo_postal_entrega'],
            )
        return self.repository.recalcular_total(pedido)



# Creadores de pedidos específicos

class PedidoEstandarFactory(PedidoFactory):

    def crear_pedido(self, cliente_id, destinatario, items, notas=None):
        pedido = self.repository.crear_cabecera(
            cliente_id=cliente_id,
            notas=notas,
            **destinatario,
        )
        return self._construir_detalles(pedido, items)

class PedidoPrioritarioFactory(PedidoFactory):

    def crear_pedido(self, cliente_id, destinatario, items, notas=None):
        notas_con_etiqueta = f"[PRIORITARIO] {notas or ''}".strip()
        pedido = self.repository.crear_cabecera(
            cliente_id=cliente_id,
            notas=notas_con_etiqueta,
            **destinatario,
        )
        return self._construir_detalles(pedido, items)



# Proveedor


class PedidoFactoryProvider:
    _registro: dict[str, type[PedidoFactory]] = {
        'estandar':    PedidoEstandarFactory,
        'prioritario': PedidoPrioritarioFactory,
    }

    @classmethod
    def obtener_factory(
        cls,
        tipo: str,
        repository: PedidoRepository,
        bodega_repo: BodegaRepository,
    ) -> PedidoFactory:
        factory_class = cls._registro.get(tipo)
        if not factory_class:
            raise ValueError(
                f"Tipo de pedido '{tipo}' no reconocido. "
                f"Disponibles: {list(cls._registro.keys())}"
            )
        return factory_class(repository, bodega_repo)