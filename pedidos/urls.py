from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from pedidos.views import (
    PedidoListCreateView,
    PedidoDetailView,
    AprobarPedidoView,
    EnviarPedidoView,
    EntregarPedidoView,
    GenerarGuiaDespachoView,
    BodegaListView,
)

urlpatterns = [
    path('bodegas/', BodegaListView.as_view(), name='bodega-list'),
    path('pedidos/', PedidoListCreateView.as_view(), name='pedido-list-create'),
    path('pedidos/<uuid:pedido_id>/', PedidoDetailView.as_view(), name='pedido-detail'),
    path('pedidos/<uuid:pedido_id>/aprobar/',   AprobarPedidoView.as_view(),  name='pedido-aprobar'),
    path('pedidos/<uuid:pedido_id>/enviar/',    EnviarPedidoView.as_view(),   name='pedido-enviar'),
    path('pedidos/<uuid:pedido_id>/entregar/',  EntregarPedidoView.as_view(), name='pedido-entregar'),
    path('pedidos/<uuid:pedido_id>/guia/',      GenerarGuiaDespachoView.as_view(), name='pedido-guia'),
    path('docs/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
