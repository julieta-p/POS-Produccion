from __future__ import annotations

from datetime import date
from typing import Any

from db.conexion import abrir_conexion


class ErrorReportePedidos(Exception):
    """Error al consultar pedidos por entregar."""


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


def listar_pedidos_por_entregar(
    *,
    fecha_desde: date,
    fecha_hasta: date,
    modalidad: str | None = None,
    cliente: str | None = None,
    solo_revisar: bool = False,
) -> list[dict[str, Any]]:
    if fecha_desde > fecha_hasta:
        raise ErrorReportePedidos(
            "La fecha desde no puede ser posterior "
            "a la fecha hasta."
        )

    condiciones = [
        "v.fecha_entrega BETWEEN ? AND ?"
    ]

    parametros: list[Any] = [
        fecha_desde,
        fecha_hasta,
    ]

    if modalidad:
        condiciones.append(
            "v.modalidad_entrega = ?"
        )
        parametros.append(
            modalidad.strip().upper()
        )

    if cliente:
        condiciones.append(
            "v.cliente LIKE ?"
        )
        parametros.append(
            f"%{cliente.strip()}%"
        )

    if solo_revisar:
        condiciones.append(
            """
            v.fecha_entrega <= DATEADD(
                DAY,
                -2,
                CAST(GETDATE() AS date)
            )
            """
        )

    sentencia = f"""
        SELECT
            v.id_pedido,
            v.fecha_entrega,
            v.hora_entrega,
            v.id_cliente,
            v.cliente,
            v.modalidad_entrega,
            v.estado_pedido,

            COALESCE(
                NULLIF(
                    LTRIM(RTRIM(v.direccion_entrega)),
                    ''
                ),
                c.direccion
            ) AS direccion_entrega,

            c.localidad,
            c.telefono,
            c.celular,

            v.observaciones_pedido,

            COUNT(*) AS cantidad_productos,

            SUM(v.cantidad_pendiente)
                AS cantidad_total_pendiente,

            CASE
                WHEN v.fecha_entrega <= DATEADD(
                    DAY,
                    -2,
                    CAST(GETDATE() AS date)
                )
                THEN 'REVISAR'
                ELSE ''
            END AS alerta

        FROM pos.vw_PedidoSalidaPendienteDetalle v

        INNER JOIN pos.Cliente c
            ON c.id_cliente = v.id_cliente

        WHERE {' AND '.join(condiciones)}

        GROUP BY
            v.id_pedido,
            v.fecha_entrega,
            v.hora_entrega,
            v.id_cliente,
            v.cliente,
            v.modalidad_entrega,
            v.estado_pedido,
            v.direccion_entrega,
            c.direccion,
            c.localidad,
            c.telefono,
            c.celular,
            v.observaciones_pedido

        ORDER BY
            v.fecha_entrega,
            CASE
                WHEN v.hora_entrega IS NULL
                THEN 1
                ELSE 0
            END,
            v.hora_entrega,
            v.id_pedido;
    """

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            sentencia,
            parametros,
        ).fetchall()

        return _filas_a_diccionarios(
            cursor,
            filas,
        )

    finally:
        conexion.close()


def listar_detalle_reparto(
    *,
    fecha_desde: date,
    fecha_hasta: date,
) -> list[dict[str, Any]]:
    if fecha_desde > fecha_hasta:
        raise ErrorReportePedidos(
            "La fecha desde no puede ser posterior "
            "a la fecha hasta."
        )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            SELECT
                v.id_pedido,
                v.fecha_entrega,
                v.hora_entrega,

                v.id_cliente,
                v.cliente,

                COALESCE(
                    NULLIF(
                        LTRIM(RTRIM(v.direccion_entrega)),
                        ''
                    ),
                    c.direccion
                ) AS direccion_entrega,

                c.localidad,
                c.telefono,
                c.celular,

                v.observaciones_pedido,

                v.renglon,
                v.id_producto,
                v.descripcion_producto,
                v.cantidad_pendiente,

                v.tipo_precio,
                v.precio_unitario,
                /*
                    Descuento que todavía corresponde
                    a la cantidad pendiente.
                */
                CONVERT(
                    decimal(18,2),
                    CASE
                        WHEN
                            dv.descuento_vigente
                            > ISNULL(da.descuento_aplicado, 0)
                        THEN
                            dv.descuento_vigente
                            - ISNULL(da.descuento_aplicado, 0)
                        ELSE 0
                    END
                ) AS descuento,

                CONVERT(
                    decimal(18,2),
                    (
                        v.cantidad_pendiente
                        * v.precio_unitario
                    )
                    -
                    CASE
                        WHEN
                            dv.descuento_vigente
                            > ISNULL(da.descuento_aplicado, 0)
                        THEN
                            dv.descuento_vigente
                            - ISNULL(da.descuento_aplicado, 0)
                        ELSE 0
                    END
                ) AS importe_linea,

                /*
                    El envío solamente corresponde
                    si este pedido todavía no tuvo
                    ninguna salida confirmada.
                */
                CONVERT(
                    decimal(18,2),
                    CASE
                        WHEN EXISTS
                        (
                            SELECT 1
                            FROM pos.PedidoSalida ps
                            WHERE ps.id_pedido =
                                v.id_pedido
                            AND ps.estado =
                                'CONFIRMADA'
                        )
                        THEN 0
                        ELSE ISNULL(
                            p.importe_envio,
                            0
                        )
                    END
                ) AS importe_envio

            FROM pos.vw_PedidoSalidaPendienteDetalle v

            INNER JOIN pos.Cliente c
                ON c.id_cliente = v.id_cliente

            INNER JOIN pos.Pedido p
                ON p.id_pedido = v.id_pedido

            OUTER APPLY
            (
                SELECT
                    SUM(vd.descuento)
                        AS descuento_aplicado
                FROM pos.VentaDetalle vd

                INNER JOIN pos.Venta ve
                    ON ve.id_venta =
                    vd.id_venta

                WHERE
                    vd.id_pedido_detalle =
                        v.id_pedido_detalle

                    AND ve.estado =
                        'CONFIRMADA'
            ) da

            OUTER APPLY
            (
                SELECT
                    CONVERT(
                        decimal(18,2),
                        ROUND(
                            v.descuento
                            * (
                                v.cantidad_pedida
                                - ISNULL(
                                    v.cantidad_cancelada,
                                    0
                                )
                                - ISNULL(
                                    v.cantidad_reprogramada,
                                    0
                                )
                            )
                            / NULLIF(
                                v.cantidad_pedida,
                                0
                            ),
                            2
                        )
                    ) AS descuento_vigente
            ) dv

            WHERE
                v.fecha_entrega BETWEEN ? AND ?
                AND v.modalidad_entrega = 'REPARTO'

            ORDER BY
                v.fecha_entrega,

                CASE
                    WHEN v.hora_entrega IS NULL
                    THEN 1
                    ELSE 0
                END,

                v.hora_entrega,
                v.id_pedido,
                v.renglon;
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