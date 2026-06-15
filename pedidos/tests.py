import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from gestion.models import Bodega, CabeceraPedido, DetallePedido, EstadoPedido, TipoCarga
from gestion.repositories.pedidos_repositories import PedidoRepository, BodegaRepository, GuiaDespachoRepository
from gestion.services.services import PedidoService
from gestion.factories import PedidoFactoryProvider, PedidoEstandarFactory, PedidoPrioritarioFactory
from gestion.circuit_breaker.pedidos_circuitbreaker import CircuitBreaker, EstadoCircuito, CircuitBreakerAbierto


# FIXTURES comunes


def crear_bodega() -> Bodega:
    return Bodega.objects.create(
        nombre="Bodega Central Santiago",
        direccion="Av. Industrial 123",
        ciudad="Santiago",
        region="Metropolitana",
    )

def datos_destinatario() -> dict:
    return {
        'destinatario_nombre':         'Juan Pérez',
        'destinatario_rut':            '12.345.678-9',
        'destinatario_telefono':       '+56912345678',
        'destinatario_correo':         'juan@example.com',
        'destinatario_direccion':      'Calle Falsa 123, Santiago',
        'destinatario_codigo_postal':  '8320000',
    }

def datos_item(bodega: Bodega) -> dict:
    ahora = timezone.now()
    return {
        'nombre_producto':      'Silla Ergonómica',
        'sku':                  'SKU-SILLA-001',
        'tipo_carga':           TipoCarga.VOLUMINOSA,
        'cantidad':             2,
        'precio_unitario':      150000.0,
        'bodega_origen_id':     str(bodega.id),
        'hora_retiro':          ahora + timedelta(hours=1),
        'hora_despacho':        ahora + timedelta(hours=3),
        'direccion_entrega':    'Av. Providencia 456, Santiago',
        'codigo_postal_entrega': '7500000',
    }



# TESTS: Modelo Bodega

class TestBodega(TestCase):

    def test_crear_bodega_activa_por_defecto(self):
        bodega = crear_bodega()
        self.assertTrue(bodega.activa)
        self.assertEqual(bodega.ciudad, 'Santiago')

    def test_str_bodega(self):
        bodega = crear_bodega()
        self.assertIn('Santiago', str(bodega))


# TESTS: Repository Pattern

class TestPedidoRepository(TestCase):

    def setUp(self):
        self.repo       = PedidoRepository()
        self.bodega_repo = BodegaRepository()
        self.cliente_id  = uuid.uuid4()
        self.bodega      = crear_bodega()

    def test_crear_cabecera_con_destinatario(self):
        pedido = self.repo.crear_cabecera(
            cliente_id=self.cliente_id,
            **datos_destinatario()
        )
        self.assertEqual(pedido.estado, EstadoPedido.PENDIENTE)
        self.assertEqual(pedido.destinatario_rut, '12.345.678-9')
        self.assertEqual(pedido.total, 0)

    def test_agregar_detalle_calcula_subtotal(self):
        pedido = self.repo.crear_cabecera(cliente_id=self.cliente_id, **datos_destinatario())
        ahora  = timezone.now()
        detalle = self.repo.agregar_detalle(
            pedido=pedido,
            nombre_producto='Monitor 4K',
            sku='MON-4K',
            tipo_carga=TipoCarga.FRAGIL,
            cantidad=3,
            precio_unitario=200000.0,
            bodega_origen=self.bodega,
            hora_retiro=ahora + timedelta(hours=1),
            hora_despacho=ahora + timedelta(hours=4),
            direccion_entrega='Las Condes 789',
            codigo_postal_entrega='7550000',
        )
        self.assertEqual(detalle.subtotal, Decimal('600000.00'))
        self.assertEqual(detalle.tipo_carga, TipoCarga.FRAGIL)

    def test_recalcular_total_suma_detalles(self):
        pedido = self.repo.crear_cabecera(cliente_id=self.cliente_id, **datos_destinatario())
        ahora  = timezone.now()
        for precio in [50000.0, 30000.0]:
            self.repo.agregar_detalle(
                pedido=pedido, nombre_producto='Prod', sku=f'SKU-{precio}',
                tipo_carga=TipoCarga.GENERAL, cantidad=1, precio_unitario=precio,
                bodega_origen=self.bodega,
                hora_retiro=ahora + timedelta(hours=1),
                hora_despacho=ahora + timedelta(hours=3),
                direccion_entrega='Calle 1',
                codigo_postal_entrega='8000000',
            )
        pedido = self.repo.recalcular_total(pedido)
        self.assertEqual(pedido.total, Decimal('80000.00'))

    def test_secuencia_estados_completa(self):
        pedido = self.repo.crear_cabecera(cliente_id=self.cliente_id, **datos_destinatario())

        pedido = self.repo.cambiar_estado(pedido, EstadoPedido.APROBADO)
        self.assertEqual(pedido.estado, EstadoPedido.APROBADO)

        pedido = self.repo.cambiar_estado(pedido, EstadoPedido.ENVIADO)
        self.assertEqual(pedido.estado, EstadoPedido.ENVIADO)

        pedido = self.repo.cambiar_estado(pedido, EstadoPedido.ENTREGADO)
        self.assertEqual(pedido.estado, EstadoPedido.ENTREGADO)



# TESTS: Factory Method


class TestPedidoFactory(TestCase):

    def setUp(self):
        self.repo        = PedidoRepository()
        self.bodega_repo = BodegaRepository()
        self.bodega      = crear_bodega()
        self.cliente_id  = uuid.uuid4()

    def test_factory_estandar_no_modifica_notas(self):
        factory = PedidoEstandarFactory(self.repo, self.bodega_repo)
        items   = [datos_item(self.bodega)]
        pedido  = factory.crear_pedido(self.cliente_id, datos_destinatario(), items, notas='Urgente')
        self.assertEqual(pedido.notas, 'Urgente')

    def test_factory_prioritario_agrega_etiqueta(self):
        factory = PedidoPrioritarioFactory(self.repo, self.bodega_repo)
        items   = [datos_item(self.bodega)]
        pedido  = factory.crear_pedido(self.cliente_id, datos_destinatario(), items, notas='Frágil')
        self.assertIn('[PRIORITARIO]', pedido.notas)
        self.assertIn('Frágil', pedido.notas)

    def test_provider_tipo_invalido_lanza_error(self):
        with self.assertRaises(ValueError) as ctx:
            PedidoFactoryProvider.obtener_factory('inexistente', self.repo, self.bodega_repo)
        self.assertIn('inexistente', str(ctx.exception))

    def test_bodega_inexistente_lanza_error(self):
        factory = PedidoEstandarFactory(self.repo, self.bodega_repo)
        item_con_bodega_falsa = datos_item(self.bodega)
        item_con_bodega_falsa['bodega_origen_id'] = str(uuid.uuid4())  # UUID que no existe

        with self.assertRaises(ValueError) as ctx:
            factory.crear_pedido(self.cliente_id, datos_destinatario(), [item_con_bodega_falsa])
        self.assertIn('bodega', str(ctx.exception).lower())

# TESTS: Circuit Breaker


class TestCircuitBreaker(TestCase):

    def setUp(self):
        self.cb = CircuitBreaker('TestSvc', umbral_fallos=2, timeout_segundos=999)

    def test_estado_inicial_closed(self):
        self.assertEqual(self.cb.estado, EstadoCircuito.CLOSED)

    @patch('ms_pedidos.circuit_breaker.requests.request')
    def test_fallos_abren_circuito(self, mock_req):
        import requests as req
        mock_req.side_effect = req.exceptions.ConnectionError()

        for _ in range(2):
            try:
                self.cb.llamar('http://fake/')
            except Exception:
                pass

        self.assertEqual(self.cb.estado, EstadoCircuito.OPEN)

    @patch('ms_pedidos.circuit_breaker.requests.request')
    def test_circuito_abierto_no_llama_http(self, mock_req):
        import requests as req
        mock_req.side_effect = req.exceptions.ConnectionError()

        for _ in range(2):
            try:
                self.cb.llamar('http://fake/')
            except Exception:
                pass

        with self.assertRaises(CircuitBreakerAbierto):
            self.cb.llamar('http://fake/')

        self.assertEqual(mock_req.call_count, 2)  # La 3ra llamada no llegó a requests


# TESTS: Service Layer (mocks)

class TestPedidoService(TestCase):

    def test_aprobar_desde_pendiente(self):
        repo_mock  = MagicMock()
        pedido_m   = MagicMock(estado=EstadoPedido.PENDIENTE)
        repo_mock.obtener_por_id.return_value = pedido_m

        svc = PedidoService()
        svc.repository = repo_mock
        svc.aprobar_pedido(str(uuid.uuid4()))

        repo_mock.cambiar_estado.assert_called_once_with(pedido_m, EstadoPedido.APROBADO)

    def test_aprobar_no_pendiente_lanza_error(self):
        repo_mock = MagicMock()
        repo_mock.obtener_por_id.return_value = MagicMock(estado=EstadoPedido.APROBADO)

        svc = PedidoService()
        svc.repository = repo_mock
        with self.assertRaises(ValueError) as ctx:
            svc.aprobar_pedido(str(uuid.uuid4()))
        self.assertIn('Pendiente', str(ctx.exception))

    def test_entregar_desde_enviado(self):
        repo_mock = MagicMock()
        pedido_m  = MagicMock(estado=EstadoPedido.ENVIADO)
        repo_mock.obtener_por_id.return_value = pedido_m

        svc = PedidoService()
        svc.repository = repo_mock
        svc.entregar_pedido(str(uuid.uuid4()))

        repo_mock.cambiar_estado.assert_called_once_with(pedido_m, EstadoPedido.ENTREGADO)

    def test_entregar_no_enviado_lanza_error(self):
        repo_mock = MagicMock()
        repo_mock.obtener_por_id.return_value = MagicMock(estado=EstadoPedido.PENDIENTE)

        svc = PedidoService()
        svc.repository = repo_mock
        with self.assertRaises(ValueError) as ctx:
            svc.entregar_pedido(str(uuid.uuid4()))
        self.assertIn('Enviado', str(ctx.exception))

    @patch('ms_pedidos.services.inventario_cb')
    def test_stock_insuficiente_lanza_error(self, cb_mock):
        cb_mock.llamar.return_value = {'cantidad': 0}
        svc = PedidoService()
        with self.assertRaises(ValueError) as ctx:
            svc.crear_pedido(
                cliente_id=str(uuid.uuid4()),
                destinatario=datos_destinatario(),
                items=[{
                    'sku': 'X1', 'cantidad': 5, 'precio_unitario': 10.0,
                    'nombre_producto': 'Prod', 'tipo_carga': TipoCarga.GENERAL,
                    'bodega_origen_id': str(uuid.uuid4()),
                    'hora_retiro': timezone.now(), 'hora_despacho': timezone.now(),
                    'direccion_entrega': 'Calle 1', 'codigo_postal_entrega': '8000000',
                }]
            )
        self.assertIn('Stock insuficiente', str(ctx.exception))

    def test_guia_no_aprobado_lanza_error(self):
        repo_mock = MagicMock()
        repo_mock.obtener_por_id.return_value = MagicMock(estado=EstadoPedido.PENDIENTE)

        svc = PedidoService()
        svc.repository = repo_mock
        with self.assertRaises(ValueError) as ctx:
            svc.generar_guia_despacho(str(uuid.uuid4()))
        self.assertIn('Aprobado', str(ctx.exception))