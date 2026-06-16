# gestion/services/inventario_client.py
import requests
import logging

logger = logging.getLogger(__name__)

# URL del Microservicio de Inventario (Puerto 8002)
URL_MS_INVENTARIO = "http://127.0.0.1:8002/api/inventario/productos/"

def consultar_producto_por_sku(sku: str):
    """
    Se conecta al MS Inventario para validar si el SKU existe.
    """
    # Si tu inventario filtra por parámetro en la URL tipo ?sku=VALOR
    url = f"{URL_MS_INVENTARIO}?sku={sku}"
    
    try:
        response = requests.get(url, timeout=3.0)
        if response.status_code == 200:
            productos = response.json()
            # Si el inventario devuelve una lista con el producto, lo retornamos
            if isinstance(productos, list) and len(productos) > 0:
                return productos[0]
            elif isinstance(productos, dict) and "sku" in productos:
                return productos
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"No se pudo conectar con el MS Inventario: {e}")
        return None