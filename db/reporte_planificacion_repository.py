from __future__ import annotations
from typing import Any
from db.conexion import abrir_conexion
from datetime import date

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


def listar_necesidad_elaboracion(
    *,
    fecha_desde: date,
    fecha_hasta: date,
) -> list[dict[str, Any]]:
    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            SELECT
                id_producto,
                descripcion_producto,

                MIN(fecha_entrega)
                    AS primera_entrega,

                MAX(fecha_entrega)
                    AS ultima_entrega,

                COUNT(DISTINCT id_pedido)
                    AS cantidad_pedidos,

                MAX(stock_actual)
                    AS stock_actual,

                MAX(stock_asignado_total)
                    AS stock_ya_asignado,

                MAX(stock_disponible_no_asignado)
                    AS stock_disponible,

                SUM(cantidad_pendiente)
                    AS cantidad_pendiente,

                SUM(cantidad_sugerida_stock)
                    AS cantidad_sugerida_desde_stock,

                SUM(cantidad_sugerida_elaborar)
                    AS cantidad_sugerida_elaborar

            FROM pos.vw_ReportePlanificacionElaboracionDetalle

            WHERE fecha_entrega
                BETWEEN ? AND ?

            GROUP BY
                id_producto,
                descripcion_producto

            ORDER BY
                MIN(fecha_entrega),
                descripcion_producto;
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

    finally:
        conexion.close()


def listar_produccion_por_fecha(
    *,
    fecha_desde: date,
    fecha_hasta: date,
) -> list[dict[str, Any]]:
    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            SELECT
                fecha_elaboracion,
                id_producto,
                descripcion_producto,
                cantidad_planificada,
                cantidad_adicional_sugerida,
                cantidad_total_elaborar

            FROM pos.vw_ReporteProduccionPorFecha

            WHERE fecha_elaboracion
                BETWEEN ? AND ?

            ORDER BY
                fecha_elaboracion,
                descripcion_producto;
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

    finally:
        conexion.close()


def listar_detalle_planificacion(
    *,
    fecha_desde: date,
    fecha_hasta: date,
) -> list[dict[str, Any]]:
    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            SELECT
                id_pedido,
                fecha_entrega,
                modalidad_entrega,
                cliente,
                id_pedido_detalle,
                id_producto,
                descripcion_producto,
                cantidad_pendiente,
                stock_actual,
                stock_asignado_total,
                stock_disponible_no_asignado,
                cantidad_sugerida_stock,
                cantidad_sugerida_elaborar,
                fecha_sugerida_elaboracion

            FROM pos.vw_ReportePlanificacionElaboracionDetalle

            WHERE fecha_entrega
                BETWEEN ? AND ?

            ORDER BY
                fecha_entrega,
                id_pedido,
                descripcion_producto;
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

    finally:
        conexion.close()