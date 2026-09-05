from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from db.conexion import abrir_conexion


class ErrorProyeccion(Exception):
    """Error del circuito de pedidos proyectados."""


def _fila_a_diccionario(
    cursor,
    fila,
) -> dict[str, Any]:
    columnas = [
        columna[0].lower()
        for columna in cursor.description
    ]

    return dict(
        zip(columnas, fila)
    )


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


def _obtener_resultado_esperado(
    cursor,
    columnas_esperadas: set[str],
) -> dict[str, Any] | None:
    while True:

        if cursor.description is not None:
            columnas = [
                columna[0].lower()
                for columna in cursor.description
            ]

            if columnas_esperadas.issubset(
                set(columnas)
            ):
                fila = cursor.fetchone()

                if fila is not None:
                    return dict(
                        zip(columnas, fila)
                    )

        if not cursor.nextset():
            return None


def listar_pedidos_proyectados(
    *,
    fecha,
    criterio: str = "REVISION",
    modalidad: str | None = None,
) -> list[dict[str, Any]]:

    criterio = criterio.strip().upper()

    if criterio not in (
        "REVISION",
        "ENTREGA",
    ):
        raise ErrorProyeccion(
            "El criterio debe ser REVISION o ENTREGA."
        )

    modalidad = (
        modalidad.strip().upper()
        if modalidad
        else None
    )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            EXEC pos.ListarPedidosProyectados
                @fecha = ?,
                @criterio = ?,
                @modalidad = ?;
            """,
            (
                fecha,
                criterio,
                modalidad,
            ),
        ).fetchall()

        return _filas_a_diccionarios(
            cursor,
            filas,
        )

    finally:
        conexion.close()


def omitir_pedido_proyectado(
    *,
    id_ocurrencia: int,
    motivo: str | None = None,
) -> dict[str, Any]:

    if id_ocurrencia <= 0:
        raise ErrorProyeccion(
            "Debe indicar una ocurrencia válida."
        )

    motivo = (
        motivo.strip()
        if motivo
        else None
    )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            EXEC pos.OmitirPedidoProyectado
                @id_pedido_recurrente_ocurrencia = ?,
                @motivo = ?,
                @usuario = NULL;
            """,
            (
                id_ocurrencia,
                motivo,
            ),
        )

        resultado = _obtener_resultado_esperado(
            cursor,
            {
                "id_pedido_recurrente_ocurrencia",
                "id_pedido_recurrente",
                "fecha_programada",
                "estado",
            },
        )

        if resultado is None:
            raise ErrorProyeccion(
                "SQL Server no devolvió el resultado "
                "de la omisión."
            )

        conexion.commit()

        return resultado

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()


def generar_pedido_desde_proyeccion(
    *,
    id_ocurrencia: int,
    modalidad_entrega: str,
    fecha_entrega,
    hora_entrega,
    fecha_elaboracion,
    requiere_confirmacion: bool,
    direccion_entrega: str | None,
    importe_envio: Decimal,
    detalles: list[dict[str, Any]],
    observaciones: str | None = None,
) -> dict[str, Any]:

    if id_ocurrencia <= 0:
        raise ErrorProyeccion(
            "Debe indicar una ocurrencia válida."
        )

    if not detalles:
        raise ErrorProyeccion(
            "Debe indicar al menos un producto."
        )

    detalle_json = json.dumps(
        detalles,
        ensure_ascii=False,
        default=str,
    )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SET NOCOUNT ON;

            DECLARE @id_pedido BIGINT;

            EXEC pos.GenerarPedidoDesdeProyeccion
                @id_pedido_recurrente_ocurrencia = ?,
                @modalidad_entrega = ?,
                @fecha_entrega = ?,
                @hora_entrega = ?,
                @fecha_elaboracion = ?,
                @requiere_confirmacion = ?,
                @direccion_entrega = ?,
                @importe_envio = ?,
                @detalle_json = ?,
                @observaciones = ?,
                @usuario = NULL,
                @id_pedido = @id_pedido OUTPUT;
            """,
            (
                id_ocurrencia,
                modalidad_entrega,
                fecha_entrega,
                hora_entrega,
                fecha_elaboracion,
                int(requiere_confirmacion),
                direccion_entrega,
                importe_envio,
                detalle_json,
                observaciones,
            ),
        )

        resultado = _obtener_resultado_esperado(
            cursor,
            {
                "id_pedido_recurrente_ocurrencia",
                "id_pedido_recurrente",
                "id_pedido",
                "id_cliente",
                "fecha_programada",
                "fecha_entrega",
                "estado_ocurrencia",
            },
        )

        if resultado is None:
            raise ErrorProyeccion(
                "SQL Server no devolvió el pedido generado."
            )

        conexion.commit()

        return resultado

    except Exception as error:
        conexion.rollback()

        texto_error = str(error)

        if "(51034)" in texto_error:
            raise ErrorProyeccion(
                "Esta proyección ya generó un pedido."
            ) from error

        if "(51035)" in texto_error:
            raise ErrorProyeccion(
                "Esta proyección ya no se encuentra pendiente."
            ) from error

        raise

    finally:
        conexion.close()

def crear_pedido_recurrente(
    *,
    id_cliente: int,
    modalidad_entrega: str | None,
    hora_entrega,
    direccion_entrega: str | None,
    fecha_desde,
    cantidad_semanas: int,
    dias: list[int],
    detalles: list[dict[str, Any]],
    observaciones: str | None = None,
) -> dict[str, Any]:

    if id_cliente <= 0:
        raise ErrorProyeccion(
            "Debe seleccionar un cliente."
        )

    if cantidad_semanas <= 0:
        raise ErrorProyeccion(
            "La cantidad de semanas debe ser mayor que cero."
        )

    if not dias:
        raise ErrorProyeccion(
            "Debe seleccionar al menos un día."
        )

    if not detalles:
        raise ErrorProyeccion(
            "Debe agregar al menos un producto."
        )

    dias_json = json.dumps(
        dias,
        ensure_ascii=False,
    )

    detalles_json = json.dumps(
        detalles,
        ensure_ascii=False,
        default=str,
    )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SET NOCOUNT ON;

            DECLARE @id_pedido_recurrente BIGINT;

            EXEC pos.CrearPedidoRecurrente
                @id_cliente = ?,
                @modalidad_entrega = ?,
                @hora_entrega = ?,
                @direccion_entrega = ?,
                @fecha_desde = ?,
                @cantidad_semanas = ?,
                @dias_json = ?,
                @detalles_json = ?,
                @observaciones = ?,
                @usuario = NULL,
                @id_pedido_recurrente =
                    @id_pedido_recurrente OUTPUT;
            """,
            (
                id_cliente,
                modalidad_entrega,
                hora_entrega,
                direccion_entrega,
                fecha_desde,
                cantidad_semanas,
                dias_json,
                detalles_json,
                observaciones,
            ),
        )

        resultado = _obtener_resultado_esperado(
            cursor,
            {
                "id_pedido_recurrente",
                "id_cliente",
                "fecha_desde",
                "fecha_hasta",
                "cantidad_semanas",
                "cantidad_dias",
                "cantidad_productos",
                "cantidad_ocurrencias",
            },
        )

        if resultado is None:
            raise ErrorProyeccion(
                "SQL Server no devolvió "
                "la proyección creada."
            )

        conexion.commit()

        return resultado

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()