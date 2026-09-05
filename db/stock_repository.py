from __future__ import annotations

from datetime import date
from typing import Any
from decimal import Decimal

from db.conexion import abrir_conexion


class ErrorStock(Exception):
    """Error al consultar o modificar stock."""


def _filas_a_diccionarios(
    cursor,
    filas,
) -> list[dict[str, Any]]:
    columnas = [
        descripcion[0].lower()
        for descripcion in cursor.description
    ]

    return [
        dict(zip(columnas, fila))
        for fila in filas
    ]


def obtener_control_stock_necesidad(
    *,
    fecha_desde: date,
    fecha_hasta: date,
) -> list[dict[str, Any]]:
    if fecha_desde > fecha_hasta:
        raise ErrorStock(
            "La fecha desde no puede ser "
            "posterior a la fecha hasta."
        )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            EXEC pos.ObtenerControlStockNecesidad
                @fecha_desde = ?,
                @fecha_hasta = ?;
            """,
            (
                fecha_desde,
                fecha_hasta,
            ),
        ).fetchall()

        return _filas_a_diccionarios(
            cursor,
            filas,
        )

    except Exception:
        raise

    finally:
        conexion.close()

def ajustar_stock_producto(
    *,
    id_producto: int,
    stock_contado: Decimal,
    motivo: str,
) -> dict[str, Any]:
    if id_producto <= 0:
        raise ErrorStock(
            "Debe seleccionar un producto."
        )

    if stock_contado < 0:
        raise ErrorStock(
            "El stock contado no puede ser negativo."
        )

    motivo = motivo.strip()

    if not motivo:
        raise ErrorStock(
            "Debe indicar el motivo del ajuste."
        )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            EXEC pos.AjustarStockProducto
                @id_producto = ?,
                @stock_contado = ?,
                @motivo = ?;
            """,
            (
                id_producto,
                stock_contado,
                motivo,
            ),
        )

        fila = None

        while True:
            if cursor.description is not None:
                posible_fila = cursor.fetchone()

                if posible_fila is not None:
                    columnas = [
                        columna[0].lower()
                        for columna in cursor.description
                    ]

                    if "id_movimiento_stock" in columnas:
                        fila = dict(
                            zip(
                                columnas,
                                posible_fila,
                            )
                        )
                        break

            if not cursor.nextset():
                break

        if fila is None:
            raise ErrorStock(
                "SQL Server no devolvió "
                "el resultado del ajuste."
            )

        conexion.commit()

        return fila

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()