import time
import logging
import requests
from enum import Enum

logger = logging.getLogger(__name__)


class EstadoCircuito(Enum):
    CLOSED    = "CLOSED"
    OPEN      = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerAbierto(Exception):

    pass


class CircuitBreakerFallo(Exception):
    pass


class CircuitBreaker:
    def __init__(
        self,
        nombre: str,
        umbral_fallos: int = 3,
        timeout_segundos: int = 30,
        timeout_request: int = 5,
    ):
        self.nombre           = nombre
        self.umbral_fallos    = umbral_fallos
        self.timeout_segundos = timeout_segundos
        self.timeout_request  = timeout_request

        self._estado             = EstadoCircuito.CLOSED
        self._contador_fallos    = 0
        self._tiempo_ultimo_fallo: float | None = None

    @property
    def estado(self) -> EstadoCircuito:
        if self._estado == EstadoCircuito.OPEN and self._tiempo_ultimo_fallo:
            if (time.time() - self._tiempo_ultimo_fallo) >= self.timeout_segundos:
                logger.info(f"[CB:{self.nombre}] Timeout expirado → HALF_OPEN")
                self._estado = EstadoCircuito.HALF_OPEN
        return self._estado

    def _registrar_exito(self):
        self._contador_fallos = 0
        self._estado = EstadoCircuito.CLOSED
        logger.info(f"[CB:{self.nombre}] Éxito → CLOSED")

    def _registrar_fallo(self):
        self._contador_fallos    += 1
        self._tiempo_ultimo_fallo = time.time()
        if self._contador_fallos >= self.umbral_fallos:
            self._estado = EstadoCircuito.OPEN
            logger.error(f"[CB:{self.nombre}] {self._contador_fallos} fallos → OPEN")
        else:
            logger.warning(f"[CB:{self.nombre}] Fallo {self._contador_fallos}/{self.umbral_fallos}")

    def llamar(self, url: str, metodo: str = 'GET', **kwargs) -> dict:
        if self.estado == EstadoCircuito.OPEN:
            raise CircuitBreakerAbierto(
                f"Servicio '{self.nombre}' no disponible. Intente más tarde."
            )
        try:
            response = requests.request(
                method=metodo, url=url,
                timeout=self.timeout_request, **kwargs
            )
            response.raise_for_status()
            self._registrar_exito()
            return response.json()
        except requests.exceptions.Timeout:
            self._registrar_fallo()
            raise CircuitBreakerFallo(f"Timeout al contactar '{self.nombre}'.")
        except requests.exceptions.ConnectionError:
            self._registrar_fallo()
            raise CircuitBreakerFallo(f"No se pudo conectar con '{self.nombre}'.")
        except requests.exceptions.HTTPError as e:
            self._registrar_fallo()
            raise CircuitBreakerFallo(f"Error HTTP de '{self.nombre}': {e}")
        except Exception as e:
            self._registrar_fallo()
            raise CircuitBreakerFallo(f"Error inesperado en '{self.nombre}': {e}")


# Instancia global reutilizable
inventario_cb = CircuitBreaker(
    nombre="MS-Inventario",
    umbral_fallos=3,
    timeout_segundos=30,
    timeout_request=5,
)