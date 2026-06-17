import uuid
from django.core.management.base import BaseCommand
from pedidos.models import Bodega

BODEGAS = [
    {
        "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "nombre": "Bodega Norte",
        "direccion": "Av. Los Libertadores 4500",
        "ciudad": "Antofagasta",
        "region": "Antofagasta",
        "telefono": "+56551234567",
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "nombre": "Bodega Sur",
        "direccion": "Ruta 5 Sur Km 678",
        "ciudad": "Puerto Montt",
        "region": "Los Lagos",
        "telefono": "+56651234567",
    },
    {
        "id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
        "nombre": "Bodega Este",
        "direccion": "Av. San Martín 1200",
        "ciudad": "Rancagua",
        "region": "O'Higgins",
        "telefono": "+56721234567",
    },
    {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444444"),
        "nombre": "Bodega Oeste",
        "direccion": "Av. Alessandri 890",
        "ciudad": "Valparaíso",
        "region": "Valparaíso",
        "telefono": "+56321234567",
    },
    {
        "id": uuid.UUID("de305d54-75b4-431b-adb2-eb6b9e546013"),
        "nombre": "Bodega Central",
        "direccion": "Av. del Valle 750",
        "ciudad": "Santiago",
        "region": "Metropolitana",
        "telefono": "+56221234567",
    },
    {
        "id": uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
        "nombre": "Bodega Logística Sur",
        "direccion": "Av. Pdte. Eduardo Frei 1500",
        "ciudad": "Concepción",
        "region": "Biobío",
        "telefono": "+56411234567",
    },
    {
        "id": uuid.UUID("c9a646d3-9c51-4412-8947-3260c6d5731f"),
        "nombre": "Bodega Zona Franca",
        "direccion": "Av. Punta Arenas 3200",
        "ciudad": "Punta Arenas",
        "region": "Magallanes",
        "telefono": "+56611234567",
    },
]


class Command(BaseCommand):
    help = "Siembra las 7 bodegas predefinidas (Norte, Sur, Este, Oeste, Central, Logística Sur, Zona Franca)"

    def handle(self, *args, **options):
        creadas = 0
        existentes = 0
        for data in BODEGAS:
            _, created = Bodega.objects.get_or_create(
                id=data["id"],
                defaults=data,
            )
            if created:
                creadas += 1
                self.stdout.write(self.style.SUCCESS(f"  Creada: {data['nombre']}"))
            else:
                existentes += 1
                self.stdout.write(f"  Ya existe: {data['nombre']}")

        self.stdout.write(self.style.SUCCESS(
            f"\nProceso completado. Creadas: {creadas}, Ya existentes: {existentes}"
        ))
