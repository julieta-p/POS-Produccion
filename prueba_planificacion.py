from datetime import date
from decimal import Decimal

from db.planificacion_repository import (
    listar_detalles_grupo,
    listar_planificacion_productos,
)


def main() -> None:
    grupos = listar_planificacion_productos(
        fecha_desde=date(2026, 8, 1),
        fecha_hasta=date(2026, 8, 31),
        modalidad=None,
        solo_pendientes=True,
    )

    if not grupos:
        print("No hay productos pendientes.")
        return

    grupo = grupos[0]

    print(
        f"\nProducto agrupado: "
        f"{grupo['descripcion_producto']}"
    )
    print(
        f"Fecha del grupo: "
        f"{grupo['fecha_elaboracion_sugerida']}"
    )
    print(
        f"Pendiente agrupado: "
        f"{grupo['cantidad_sin_planificar']}"
    )

    detalles = listar_detalles_grupo(
        id_producto=int(
            grupo["id_producto"]
        ),
        fecha_grupo=(
            grupo[
                "fecha_elaboracion_sugerida"
            ]
        ),
        modalidad=None,
    )

    total_detalle = Decimal("0")

    print("\nPedidos que forman el grupo:")

    for detalle in detalles:
        pendiente = Decimal(
            str(
                detalle[
                    "cantidad_sin_planificar"
                ]
            )
        )

        total_detalle += pendiente

        print(
            f"Pedido {detalle['id_pedido']} · "
            f"{detalle['cliente']} · "
            f"Entrega {detalle['fecha_entrega']} · "
            f"Pendiente {pendiente}"
        )

    print(
        f"\nTotal de los detalles: "
        f"{total_detalle}"
    )

    print(
        "Coincide con el grupo:",
        total_detalle
        == Decimal(
            str(
                grupo[
                    "cantidad_sin_planificar"
                ]
            )
        ),
    )


if __name__ == "__main__":
    main()