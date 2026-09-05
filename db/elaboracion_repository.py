from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from db.conexion import abrir_conexion


class ErrorElaboracion(Exception):
    """Error al confirmar una elaboración."""


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


def listar_elaboraciones_pendientes(
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
                cantidad_producida,
                cantidad_pendiente
            FROM pos.vw_ElaboracionPendiente
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


def confirmar_elaboracion(
    *,
    fecha_elaboracion: date,
    id_producto: int,
    cantidad_obtenida: Decimal,
    observaciones: str | None = None,
) -> dict[str, Any]:
    if cantidad_obtenida <= 0:
        raise ErrorElaboracion(
            "La cantidad obtenida debe ser mayor que cero."
        )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SET NOCOUNT ON;

            DECLARE @id_elaboracion BIGINT;
            DECLARE @usuario SYSNAME;

            SET @usuario = SUSER_SNAME();

            EXEC pos.ConfirmarElaboracion
                @fecha_elaboracion = ?,
                @id_producto = ?,
                @cantidad_obtenida = ?,
                @observaciones = ?,
                @usuario = @usuario,
                @id_elaboracion =
                    @id_elaboracion OUTPUT;
            """,
            (
                fecha_elaboracion,
                id_producto,
                cantidad_obtenida,
                observaciones,
            ),
        )

        resultado = None

        while True:
            if cursor.description is not None:
                columnas = [
                    columna[0].lower()
                    for columna in cursor.description
                ]

                if "id_elaboracion" in columnas:
                    fila = cursor.fetchone()

                    if fila is not None:
                        resultado = dict(
                            zip(columnas, fila)
                        )

                    break

            if not cursor.nextset():
                break

        if resultado is None:
            raise ErrorElaboracion(
                "SQL Server no devolvió el resultado "
                "de la elaboración."
            )

        conexion.commit()

        return resultado

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()