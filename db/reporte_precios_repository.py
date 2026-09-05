from __future__ import annotations

from typing import Any

from db.conexion import abrir_conexion


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


def listar_precios(
    *,
    buscar: str | None = None,
) -> list[dict[str, Any]]:
    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        buscar = (
            buscar.strip()
            if buscar
            else None
        )

        filas = cursor.execute(
            """
            SELECT
                id_producto,
                descripcion,
                precio_mayor,
                precio_menor
            FROM pos.vw_ProductoPedido
            WHERE
                ? IS NULL
                OR descripcion LIKE '%' + ? + '%'
            ORDER BY
                descripcion;
            """,
            buscar,
            buscar,
        ).fetchall()

        return _filas_a_diccionarios(
            cursor,
            filas,
        )

    finally:
        conexion.close()