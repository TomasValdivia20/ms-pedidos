import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from gestion.services import PedidoService
from gestion.serializers import (
    CabeceraPedidoSerializer,
    CrearPedidoSerializer,
    GuiaDespachoSerializer,
    BodegaSerializer,
)

logger = logging.getLogger(__name__)


# Pedidos

class PedidoListCreateView(APIView):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PedidoService()

    def get(self, request):
        cliente_id = request.query_params.get('cliente_id')
        try:
            pedidos = self.service.listar_pedidos(cliente_id=cliente_id)
            return Response(CabeceraPedidoSerializer(pedidos, many=True).data)
        except Exception as e:
            logger.error(f"[PedidoListCreate.get] {e}")
            return Response({'error': 'Error al listar pedidos.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        serializer = CrearPedidoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            items_normalizados = [
                {
                    'nombre_producto':      item['nombre_producto'],
                    'sku':                  item['sku'],
                    'tipo_carga':           item['tipo_carga'],
                    'cantidad':             item['cantidad'],
                    'precio_unitario':      float(item['precio_unitario']),
                    'bodega_origen_id':     str(item['bodega_origen_id']),
                    'hora_retiro':          item['hora_retiro'],
                    'hora_despacho':        item['hora_despacho'],
                    'direccion_entrega':    item['direccion_entrega'],
                    'codigo_postal_entrega': item['codigo_postal_entrega'],
                }
                for item in data['items']
            ]
            pedido = self.service.crear_pedido(
                cliente_id=str(data['cliente_id']),
                destinatario=data['destinatario'],
                items=items_normalizados,
                tipo=data.get('tipo', 'estandar'),
                notas=data.get('notas'),
            )
            return Response(CabeceraPedidoSerializer(pedido).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"[PedidoListCreate.post] {e}")
            return Response({'error': 'Error interno al crear el pedido.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PedidoDetailView(APIView):
    """GET /api/pedidos/<pedido_id>/"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PedidoService()

    def get(self, request, pedido_id):
        try:
            pedido = self.service.obtener_pedido(str(pedido_id))
            return Response(CabeceraPedidoSerializer(pedido).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)



# Transiciones de estado


class AprobarPedidoView(APIView):
    """PATCH /api/pedidos/<pedido_id>/aprobar/"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PedidoService()

    def patch(self, request, pedido_id):
        try:
            pedido = self.service.aprobar_pedido(str(pedido_id))
            return Response(CabeceraPedidoSerializer(pedido).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EnviarPedidoView(APIView):
    """PATCH /api/pedidos/<pedido_id>/enviar/"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PedidoService()

    def patch(self, request, pedido_id):
        try:
            pedido = self.service.enviar_pedido(str(pedido_id))
            return Response(CabeceraPedidoSerializer(pedido).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EntregarPedidoView(APIView):
    """PATCH /api/pedidos/<pedido_id>/entregar/"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PedidoService()

    def patch(self, request, pedido_id):
        try:
            pedido = self.service.entregar_pedido(str(pedido_id))
            return Response(CabeceraPedidoSerializer(pedido).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Guía de Despacho

class GenerarGuiaDespachoView(APIView):
    """POST /api/pedidos/<pedido_id>/guia/  → Genera la guía de despacho."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PedidoService()

    def post(self, request, pedido_id):
        try:
            guia = self.service.generar_guia_despacho(str(pedido_id))
            return Response(GuiaDespachoSerializer(guia).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, pedido_id):
        """GET /api/pedidos/<pedido_id>/guia/  → Obtiene la guía existente."""
        try:
            guia = self.service.obtener_guia(str(pedido_id))
            return Response(GuiaDespachoSerializer(guia).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)


# Bodegas


class BodegaListView(APIView):
    """GET /api/bodegas/ → Lista todas las bodegas activas."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PedidoService()

    def get(self, request):
        bodegas = self.service.listar_bodegas()
        return Response(BodegaSerializer(bodegas, many=True).data)