from django.contrib import admin
from django.urls import path
from gestion.views import (
    PedidoListCreateView,
    PedidoDetailView,
    AprobarPedidoView,
    EnviarPedidoView,
    EntregarPedidoView,
    GenerarGuiaDespachoView,
    BodegaListView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
        #  Bodegas 
    path('bodegas/', BodegaListView.as_view(), name='bodega-list'),

    #  Pedidos 
    path('pedidos/', PedidoListCreateView.as_view(), name='pedido-list-create'),
    path('pedidos/<uuid:pedido_id>/', PedidoDetailView.as_view(), name='pedido-detail'),

    # Ciclo de vida 
    # Pendiente → Aprobado → Enviado → Entregado
    path('pedidos/<uuid:pedido_id>/aprobar/',   AprobarPedidoView.as_view(),  name='pedido-aprobar'),
    path('pedidos/<uuid:pedido_id>/enviar/',    EnviarPedidoView.as_view(),   name='pedido-enviar'),
    path('pedidos/<uuid:pedido_id>/entregar/',  EntregarPedidoView.as_view(), name='pedido-entregar'),

    #  Guía de Despacho 
    path('pedidos/<uuid:pedido_id>/guia/',      GenerarGuiaDespachoView.as_view(), name='pedido-guia'),
]



