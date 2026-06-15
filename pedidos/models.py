import uuid
from django.db import models


# ENUMERACIONES de opciones


class EstadoPedido(models.TextChoices):
    PENDIENTE = 'Pendiente', 'Pendiente'
    APROBADO  = 'Aprobado',  'Aprobado'
    ENVIADO   = 'Enviado',   'Enviado'
    ENTREGADO = 'Entregado', 'Entregado'


class TipoCarga(models.TextChoices):
    FRAGIL     = 'Fragil',     'Frágil'
    DURO       = 'Duro',       'Duro/Resistente'
    PELIGROSA  = 'Peligrosa',  'Carga Peligrosa'
    PERECEDERA = 'Perecedera', 'Carga Perecedera'
    GENERAL    = 'General',    'Carga General'
    VOLUMINOSA = 'Voluminosa', 'Carga Voluminosa'



# BODEGA


class Bodega(models.Model):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre    = models.CharField(max_length=200)
    direccion = models.CharField(max_length=300)
    ciudad    = models.CharField(max_length=100)
    region    = models.CharField(max_length=100, blank=True, null=True)
    telefono  = models.CharField(max_length=20, blank=True, null=True)
    activa    = models.BooleanField(default=True)

    class Meta:
        db_table = 'bodega'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} — {self.ciudad}"



# CABECERA DE PEDIDO


class CabeceraPedido(models.Model):
    #  Identificación 
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente_id = models.UUIDField(
                    help_text="UUID del cliente en MS-Clientes. "
                            "Sin FK directa: comunicación vía HTTP.")

    # Estado y financiero 
    estado = models.CharField(
                max_length=20,
                choices=EstadoPedido.choices,
                default=EstadoPedido.PENDIENTE)
    total  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notas  = models.TextField(blank=True, null=True)

    #  Datos del destinatario (embebidos) 
    destinatario_nombre         = models.CharField(max_length=200)
    destinatario_rut            = models.CharField(
                                    max_length=12,
                                    help_text="Formato: 12.345.678-9")
    destinatario_telefono       = models.CharField(max_length=20)
    destinatario_correo         = models.EmailField()
    destinatario_direccion      = models.TextField()
    destinatario_codigo_postal  = models.CharField(
                                    max_length=10,
                                    help_text="Código postal de la dirección del destinatario.")

    # Timestamps 
    fecha_creacion      = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cabecera_pedido'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return (
            f"Pedido {self.id} | "
            f"Destinatario: {self.destinatario_nombre} | "
            f"Estado: {self.estado}"
        )



# DETALLE DE PEDIDO


class DetallePedido(models.Model):
    # Relación con cabecera 
    id     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedido = models.ForeignKey(
                CabeceraPedido,
                on_delete=models.CASCADE,
                related_name='detalles'
            )

    # Producto 
    nombre_producto = models.CharField(max_length=300)
    sku             = models.CharField(
                        max_length=100,
                        help_text="Referencia lógica al MS-Inventario. Sin FK directa.")
    tipo_carga      = models.CharField(
                        max_length=20,
                        choices=TipoCarga.choices,
                        default=TipoCarga.GENERAL
                    )

    # Cantidades y precios 
    cantidad        = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal        = models.DecimalField(max_digits=12, decimal_places=2)

    #  Logística de despacho
    bodega_origen          = models.ForeignKey(
                                Bodega,
                                on_delete=models.PROTECT,
                                related_name='detalles_pedido',
                                help_text="PROTECT sirve para que no se pueda eliminar una bodega con despachos activos.")
    hora_retiro            = models.DateTimeField(
                                help_text="Fecha y hora en que el producto se retira de bodega."
                            )
    hora_despacho          = models.DateTimeField(
                                help_text="Fecha y hora programada de salida hacia la dirección de entrega."
                            )
    direccion_entrega      = models.TextField(
                                help_text="Dirección de entrega específica para este ítem del pedido."
                            )
    codigo_postal_entrega  = models.CharField(
                                max_length=10,
                                help_text="Código postal de la dirección de entrega de este ítem."
                            )

    class Meta:
        db_table = 'detalle_pedido'

    def __str__(self):
        return (
            f"{self.nombre_producto} (SKU:{self.sku}) | "
            f"x{self.cantidad} | {self.get_tipo_carga_display()} | "
            f"Bodega: {self.bodega_origen.nombre}"
        )

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.hora_retiro and self.hora_despacho:
            if self.hora_retiro >= self.hora_despacho:
                raise ValidationError(
                    "La hora de retiro debe ser anterior a la hora de despacho.")



# GUÍA DE DESPACHO


class GuiaDespacho(models.Model):

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedido      = models.OneToOneField(
                    CabeceraPedido,
                    on_delete=models.PROTECT,
                    related_name='guia_despacho')
    numero_guia = models.CharField(
                    max_length=20,
                    unique=True,
                    help_text="Número correlativo legible Ej: GD-2025-00042")
    fecha_emision = models.DateTimeField(auto_now_add=True)

    #  Firma del responsable en bodega 
    firma_responsable_despacho = models.TextField(
        blank=True,
        null=True,
        help_text="Nombre o firma digital del responsable de autorizar el despacho."
    )
    fecha_firma_despacho = models.DateTimeField(blank=True, null=True)

    #  Firma del receptor final 
    firma_receptor = models.TextField(
        blank=True,
        null=True,
        help_text="Nombre o firma digital del receptor en la dirección de entrega."
    )
    fecha_firma_receptor = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'guia_despacho'
        ordering = ['-fecha_emision']

    def __str__(self):
        return f"Guía {self.numero_guia} → Pedido {self.pedido_id}"

    def generar_resumen_texto(self) -> str:

        pedido   = self.pedido
        detalles = pedido.detalles.select_related('bodega_origen').all()

        def fmt_dt(dt):
            return dt.strftime('%d/%m/%Y %H:%M') if dt else '_' * 20

        lineas = [
            "=" * 60,
            f"  GUÍA DE DESPACHO N° {self.numero_guia}",
            f"  Fecha emisión: {fmt_dt(self.fecha_emision)}",
            "=" * 60,
            "",
            "── ÍTEMS DEL PEDIDO ──────────────────────────────────────",
        ]

        for i, det in enumerate(detalles, start=1):
            lineas += [
                "",
                f"  Ítem {i}:",
                f"  PRODUCTO          : {det.nombre_producto}",
                f"  SKU               : {det.sku}",
                f"  Tipo de Carga     : {det.get_tipo_carga_display()}",
                f"  Cantidad          : {det.cantidad}",
                f"  Bodega de Origen  : {det.bodega_origen.nombre} — {det.bodega_origen.ciudad}",
                f"  Hora de Retiro    : {fmt_dt(det.hora_retiro)}",
                f"  Hora de Despacho  : {fmt_dt(det.hora_despacho)}",
                f"  Dirección Entrega  : {det.direccion_entrega}",
                f"  Código Postal      : {det.codigo_postal_entrega}",
            ]

        lineas += [
            "",
            "── DATOS DEL DESTINATARIO ────────────────────────────────",
            f"  Nombre    : {pedido.destinatario_nombre}",
            f"  RUT       : {pedido.destinatario_rut}",
            f"  Teléfono  : {pedido.destinatario_telefono}",
            f"  Correo    : {pedido.destinatario_correo}",
            f"  Dirección : {pedido.destinatario_direccion}",
            f"  C. Postal : {pedido.destinatario_codigo_postal}",
            "",
            "── FIRMAS ────────────────────────────────────────────────",
            f"  Firma Responsable Despacho : {self.firma_responsable_despacho or '_' * 30}",
            f"  Fecha                      : {fmt_dt(self.fecha_firma_despacho)}",
            "",
            f"  Firma Receptor             : {self.firma_receptor or '_' * 30}",
            f"  Fecha                      : {fmt_dt(self.fecha_firma_receptor)}",
            "",
            "=" * 60,
        ]

        return "\n".join(lineas)