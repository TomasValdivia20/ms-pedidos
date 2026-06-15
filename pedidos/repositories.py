import uuid
from typing import Optional, List

from gestion.models import (
    Bodega,
    CabeceraPedido,
    DetallePedido,
    GuiaDespacho,
    EstadoPedido,
)


class BodegaRepository:

    def listar_activas(self) -> List[Bodega]:
        return list(Bodega.objects.filter(activa=True))

    def obtener_por_id(self, bodega_id: uuid.UUID) -> Optional[Bodega]:
        try:
            return Bodega.objects.get(id=bodega_id, activa=True)
        except Bodega.DoesNotExist:
            return None


class PedidoRepository:

    # Escritura — CabeceraPedido

    def crear_cabecera(
        self,
        cliente_id: uuid.UUID,
        destinatario_nombre: str,
        destinatario_rut: str,
        destinatario_telefono: str,
        destinatario_correo: str,
        destinatario_direccion: str,
        destinatario_codigo_postal: str,
        notas: str = None,
    ) -> CabeceraPedido:
        return CabeceraPedido.objects.create(
            cliente_id=cliente_id,
            destinatario_nombre=destinatario_nombre,
            destinatario_rut=destinatario_rut,
            destinatario_telefono=destinatario_telefono,
            destinatario_correo=destinatario_correo,
            destinatario_direccion=destinatario_direccion,
            destinatario_codigo_postal=destinatario_codigo_postal,
            notas=notas,
        )

    def agregar_detalle(
        self,
        pedido: CabeceraPedido,
        nombre_producto: str,
        sku: str,
        tipo_carga: str,
        cantidad: int,
        precio_unitario: float,
        bodega_origen: Bodega,
        hora_retiro,
        hora_despacho,
        direccion_entrega: str,
        codigo_postal_entrega: str,
    ) -> DetallePedido:
        subtotal = round(cantidad * precio_unitario, 2)
        return DetallePedido.objects.create(
            pedido=pedido,
            nombre_producto=nombre_producto,
            sku=sku,
            tipo_carga=tipo_carga,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            subtotal=subtotal,
            bodega_origen=bodega_origen,
            hora_retiro=hora_retiro,
            hora_despacho=hora_despacho,
            direccion_entrega=direccion_entrega,
            codigo_postal_entrega=codigo_postal_entrega,
        )

    def recalcular_total(self, pedido: CabeceraPedido) -> CabeceraPedido:
        total = sum(d.subtotal for d in pedido.detalles.all())
        pedido.total = total
        pedido.save(update_fields=['total'])
        return pedido

    def cambiar_estado(self, pedido: CabeceraPedido, nuevo_estado: EstadoPedido) -> CabeceraPedido:
        pedido.estado = nuevo_estado
        pedido.save(update_fields=['estado', 'fecha_actualizacion'])
        return pedido


    # Lectura — CabeceraPedido


    def obtener_por_id(self, pedido_id: uuid.UUID) -> Optional[CabeceraPedido]:
        try:
            return (
                CabeceraPedido.objects
                .prefetch_related('detalles__bodega_origen')
                .get(id=pedido_id)
            )
        except CabeceraPedido.DoesNotExist:
            return None

    def listar_por_cliente(self, cliente_id: uuid.UUID) -> List[CabeceraPedido]:
        return list(
            CabeceraPedido.objects
            .filter(cliente_id=cliente_id)
            .prefetch_related('detalles__bodega_origen')
        )

    def listar_todos(self) -> List[CabeceraPedido]:
        return list(
            CabeceraPedido.objects.all()
            .prefetch_related('detalles__bodega_origen')
        )


class GuiaDespachoRepository:

    def crear(self, pedido: CabeceraPedido, numero_guia: str) -> GuiaDespacho:
        return GuiaDespacho.objects.create(
            pedido=pedido,
            numero_guia=numero_guia,
        )

    def obtener_por_pedido(self, pedido_id: uuid.UUID) -> Optional[GuiaDespacho]:
        try:
            return GuiaDespacho.objects.select_related(
                'pedido'
            ).get(pedido_id=pedido_id)
        except GuiaDespacho.DoesNotExist:
            return None

    def registrar_firma_despacho(
        self,
        guia: GuiaDespacho,
        firma: str,
        fecha
    ) -> GuiaDespacho:
        guia.firma_responsable_despacho = firma
        guia.fecha_firma_despacho = fecha
        guia.save(update_fields=['firma_responsable_despacho', 'fecha_firma_despacho'])
        return guia

    def registrar_firma_receptor(
        self,
        guia: GuiaDespacho,
        firma: str,
        fecha
    ) -> GuiaDespacho:
        guia.firma_receptor = firma
        guia.fecha_firma_receptor = fecha
        guia.save(update_fields=['firma_receptor', 'fecha_firma_receptor'])
        return guia

    def numero_guia_existe(self, numero_guia: str) -> bool:
        return GuiaDespacho.objects.filter(numero_guia=numero_guia).exists()