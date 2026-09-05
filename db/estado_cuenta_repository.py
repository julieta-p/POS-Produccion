from __future__ import annotations

from datetime import date
from typing import Any

from db.conexion import abrir_conexion


def _fila_a_diccionario(
    cursor,
    fila,
) -> dict[str, Any] | None:
    if fila is None:
        return None

    columnas = [
        columna[0].lower()
        for columna in cursor.description
    ]

    return dict(zip(columnas, fila))


def _filas_a_diccionarios(
    cursor,
    filas,
) -> list[dict[str, Any]]:
    columnas = [
        columna[0].lower()
        for columna in cursor.description
    ]

    return [
        dict(zip(columnas, fila))
        for fila in filas
    ]


def obtener_resumen_cliente(
    id_cliente: int,
) -> dict[str, Any] | None:
    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        fila = cursor.execute(
            """
            SELECT
                id_cliente,
                nombre,
                total_ventas,
                total_cobros,
                saldo
            FROM pos.vw_CuentaCorrienteSaldo
            WHERE id_cliente = ?;
            """,
            id_cliente,
        ).fetchone()

        return _fila_a_diccionario(
            cursor,
            fila,
        )

    finally:
        conexion.close()


def listar_estado_cuenta(
    *,
    id_cliente: int,
    fecha_desde: date,
    fecha_hasta: date,
) -> list[dict[str, Any]]:
    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            SELECT
                id_cliente,
                nombre,
                nro_movimiento,
                fecha_hora,
                tipo_movimiento,
                id_referencia,
                debe,
                haber,
                detalle,
                saldo_acumulado
            FROM pos.vw_EstadoCuentaCliente
            WHERE id_cliente = ?
              AND fecha_hora >= ?
              AND fecha_hora < DATEADD(
                    DAY,
                    1,
                    ?
                  )
            ORDER BY
                nro_movimiento;
            """,
            (
                id_cliente,
                fecha_desde,
                fecha_hasta,
            ),
        ).fetchall()

        return _filas_a_diccionarios(
            cursor,
            filas,
        )

    finally:
        conexion.close()