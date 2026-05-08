from django.contrib import admin

# Register your models here.
# gestion/admin.py
from django.contrib import admin
from gestion.models import CabeceraPedido, DetallePedido, Bodega, GuiaDespacho

# Registramos los modelos para que aparezcan en el panel
admin.site.register(Bodega)
admin.site.register(CabeceraPedido)
admin.site.register(DetallePedido)
admin.site.register(GuiaDespacho)
