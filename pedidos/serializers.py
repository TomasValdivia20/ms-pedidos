from decimal import Decimal
from rest_framework import serializers
from pedidos.models import Bodega, CabeceraPedido, DetallePedido, GuiaDespacho, TipoCarga

from rest_framework import serializers
from .models import DetallePedido
from .services import consultar_producto_en_inventario  # Importamos la función del Paso 1

# SALIDA: Bodegas


class BodegaSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Bodega
        fields = ['id', 'nombre', 'direccion', 'ciudad', 'region', 'telefono']


# SALIDA: Detalles y Cabecera de Pedido


class DetallePedidoSerializer(serializers.ModelSerializer):
    bodega_origen     = BodegaSerializer(read_only=True)
    tipo_carga_display = serializers.CharField(
                            source='get_tipo_carga_display',
                            read_only=True)

    class Meta:
        model  = DetallePedido
        fields = [
            'id', 'nombre_producto', 'sku',
            'tipo_carga', 'tipo_carga_display',
            'cantidad', 'precio_unitario', 'subtotal',
            'bodega_origen', 'hora_retiro', 'hora_despacho',
            'direccion_entrega', 'codigo_postal_entrega',
        ]
        read_only_fields = ['id', 'subtotal', 'tipo_carga_display']


class CabeceraPedidoSerializer(serializers.ModelSerializer):
    detalles      = DetallePedidoSerializer(many=True, read_only=True)
    estado_display = serializers.CharField(
                        source='get_estado_display',
                        read_only=True)

    class Meta:
        model  = CabeceraPedido
        fields = [
            'id', 'cliente_id',
            'estado', 'estado_display', 'total', 'notas',
            # Destinatario
            'destinatario_nombre', 'destinatario_rut',
            'destinatario_telefono', 'destinatario_correo',
            'destinatario_direccion', 'destinatario_codigo_postal',
            # Timestamps
            'fecha_creacion', 'fecha_actualizacion',
            # Detalles anidados
            'detalles',
        ]
        read_only_fields = [
            'id', 'estado', 'estado_display', 'total',
            'fecha_creacion', 'fecha_actualizacion',
        ]



# SALIDA: Guía de Despacho


class GuiaDespachoSerializer(serializers.ModelSerializer):
    """Representación completa de la guía, incluyendo el resumen para impresión."""

    resumen_impresion = serializers.SerializerMethodField()
    pedido            = CabeceraPedidoSerializer(read_only=True)

    class Meta:
        model  = GuiaDespacho
        fields = [
            'id', 'numero_guia', 'fecha_emision',
            'firma_responsable_despacho', 'fecha_firma_despacho',
            'firma_receptor', 'fecha_firma_receptor',
            'pedido',
            'resumen_impresion',
        ]

    def get_resumen_impresion(self, obj) -> str:
        """Llama al método del modelo para generar el texto de impresión."""
        return obj.generar_resumen_texto()



# ENTRADA: Validación del body de creación de pedido


class ItemPedidoInputSerializer(serializers.Serializer):
    nombre_producto        = serializers.CharField(max_length=300)
    sku                    = serializers.CharField(max_length=100)
    tipo_carga             = serializers.ChoiceField(choices=TipoCarga.choices)
    cantidad               = serializers.IntegerField(min_value=1)
    precio_unitario        = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    bodega_origen_id       = serializers.UUIDField()
    hora_retiro            = serializers.DateTimeField()
    hora_despacho          = serializers.DateTimeField()
    direccion_entrega      = serializers.CharField()
    codigo_postal_entrega  = serializers.CharField(max_length=10)

    def validate(self, data):
        """Valida que la hora de retiro sea anterior a la hora de despacho."""
        if data.get('hora_retiro') and data.get('hora_despacho'):
            if data['hora_retiro'] >= data['hora_despacho']:
                raise serializers.ValidationError(
                    "La hora de retiro debe ser anterior a la hora de despacho."
                )
        return data


class DestinatarioInputSerializer(serializers.Serializer):
    destinatario_nombre         = serializers.CharField(max_length=200)
    destinatario_rut            = serializers.CharField(max_length=12)
    destinatario_telefono       = serializers.CharField(max_length=20)
    destinatario_correo         = serializers.EmailField()
    destinatario_direccion      = serializers.CharField()
    destinatario_codigo_postal  = serializers.CharField(max_length=10)


class CrearPedidoSerializer(serializers.Serializer):
    cliente_id   = serializers.UUIDField()
    tipo         = serializers.ChoiceField(choices=['estandar', 'prioritario'], default='estandar')
    notas        = serializers.CharField(required=False, allow_blank=True, default=None)
    destinatario = DestinatarioInputSerializer()
    items        = ItemPedidoInputSerializer(many=True, min_length=1)

    def validate_items(self, items):
        """No puede haber SKUs duplicados en un mismo pedido."""
        skus = [item['sku'] for item in items]
        if len(skus) != len(set(skus)):
            raise serializers.ValidationError(
                "No se puede incluir el mismo SKU más de una vez en un pedido."
            )
        return items
    

    class DetallePedidoSerializer(serializers.ModelSerializer):
        class Meta:
            model = DetallePedido
            fields = '__all__'

        def validate(self, data):
            sku = data.get('sku')
            
            # 1. Consultamos al Microservicio de Inventario en tiempo real
            producto_inventario = consultar_producto_en_inventario(sku)
            
            if not producto_inventario:
                raise serializers.ValidationError(
                    f"El producto con SKU '{sku}' no existe en el catálogo de Inventario."
                )
            
            # 2. (Opcional) Validar si hay stock suficiente
            cantidad_solicitada = data.get('cantidad')
            stock_disponible = producto_inventario.get('stock_actual', 0)
            
            if cantidad_solicitada > stock_disponible:
                raise serializers.ValidationError(
                    f"Stock insuficiente para {sku}. Solicitado: {cantidad_solicitada}, Disponible: {stock_disponible}."
                )

            # 3. Auto-rellenar campos que vienen de inventario para asegurar integridad
            data['precio_unitario'] = producto_inventario.get('precio_venta')
            data['bodega_origen_id'] = producto_inventario.get('bodega_id')
            
            return data