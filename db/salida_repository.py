from __future__ import annotations

import json
from datetime import date, time
from decimal import Decimal
from typing import Any

from db.conexion import abrir_conexion


class ErrorSalidaPedido(Exception):
    """Error del circuito de salidas de pedidos."""


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


def listar_pedidos_pendientes(
    *,
    fecha_desde: date,
    fecha_hasta: date,
    modalidad: str | None = None,
    cliente: str | None = None,
) -> list[dict[str, Any]]:
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

    sentencia = f"""
        SELECT
            v.id_pedido,
            v.fecha_entrega,
            v.hora_entrega,
            v.id_cliente,
            v.cliente,
            v.modalidad_entrega,
            v.estado_pedido,
            v.direccion_entrega,
            v.observaciones_pedido,

            COUNT(*) AS cantidad_productos,

            SUM(v.cantidad_pendiente)
                AS cantidad_total_pendiente

        FROM pos.vw_PedidoSalidaPendienteDetalle v

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
            v.observaciones_pedido

        ORDER BY
            v.fecha_entrega,
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


def listar_detalle_pendiente(
    id_pedido: int,
) -> list[dict[str, Any]]:
    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            SELECT
                id_pedido_detalle,
                renglon,
                id_producto,
                descripcion_producto,
                cantidad_pedida,
                cantidad_cancelada,
                cantidad_reprogramada,
                cantidad_entregada,
                cantidad_pendiente,
                precio_unitario,
                tipo_precio,
                descuento

            FROM pos.vw_PedidoSalidaPendienteDetalle

            WHERE id_pedido = ?

            ORDER BY
                renglon,
                descripcion_producto;
            """,
            id_pedido,
        ).fetchall()

        return _filas_a_diccionarios(
            cursor,
            filas,
        )

    finally:
        conexion.close()


def confirmar_salida(
    *,
    id_pedido: int,
    tipo_salida: str,
    detalle: list[dict[str, Any]],
    observaciones: str | None = None,
    destino_saldo: str = "PENDIENTE",
    motivo_saldo: str | None = None,
) -> dict[str, Any]:
    if id_pedido <= 0:
        raise ErrorSalidaPedido(
            "Debe seleccionar un pedido."
        )

    tipo_salida = tipo_salida.strip().upper()

    if tipo_salida not in (
        "ENTREGADO",
        "LLEVAR",
    ):
        raise ErrorSalidaPedido(
            "El tipo de salida no es válido."
        )

    destino_saldo = (
        destino_saldo.strip().upper()
        if destino_saldo
        else "PENDIENTE"
    )

    if destino_saldo not in (
        "PENDIENTE",
        "CANCELAR",
    ):
        raise ErrorSalidaPedido(
            "El destino indicado para el saldo "
            "no es válido."
        )

    motivo_saldo = (
        motivo_saldo.strip()
        if motivo_saldo
        else None
    )

    if (
        destino_saldo == "CANCELAR"
        and not motivo_saldo
    ):
        raise ErrorSalidaPedido(
            "Debe indicar el motivo de la "
            "cancelación del saldo."
        )

    detalle_json: list[dict[str, Any]] = []

    for renglon in detalle:
        id_pedido_detalle = int(
            renglon["id_pedido_detalle"]
        )

        cantidad = Decimal(
            str(renglon["cantidad"])
        )

        if cantidad <= 0:
            continue

        detalle_json.append(
            {
                "id_pedido_detalle":
                    id_pedido_detalle,

                # Se envía como texto para conservar
                # exactamente los tres decimales.
                "cantidad":
                    format(cantidad, "f"),
            }
        )

    if not detalle_json:
        raise ErrorSalidaPedido(
            "No se indicó ninguna cantidad "
            "para entregar."
        )

    texto_json = json.dumps(
        detalle_json,
        ensure_ascii=False,
    )

    observaciones = (
        observaciones.strip()
        if observaciones
        else None
    )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SET NOCOUNT ON;

            DECLARE @id_pedido_salida BIGINT;
            DECLARE @id_venta BIGINT;
            DECLARE @usuario SYSNAME;

            SET @usuario = SUSER_SNAME();

            EXEC pos.ConfirmarSalidaPedido
                @id_pedido = ?,
                @tipo_salida = ?,
                @detalle_json = ?,
                @observaciones = ?,
                @usuario = @usuario,

                @id_pedido_salida =
                    @id_pedido_salida OUTPUT,

                @id_venta =
                    @id_venta OUTPUT,

                @destino_saldo = ?,
                @motivo_saldo = ?;
            """,
            (
                id_pedido,
                tipo_salida,
                texto_json,
                observaciones,
                destino_saldo,
                motivo_saldo,
            ),
        )

        resultado = None

        while True:
            if cursor.description is not None:
                columnas = [
                    columna[0].lower()
                    for columna in cursor.description
                ]

                if (
                    "id_pedido_salida" in columnas
                    and "id_venta" in columnas
                ):
                    fila = cursor.fetchone()

                    if fila is not None:
                        resultado = dict(
                            zip(columnas, fila)
                        )

                    break

            if not cursor.nextset():
                break

        if resultado is None:
            raise ErrorSalidaPedido(
                "SQL Server no devolvió el "
                "resultado de la salida."
            )

        conexion.commit()

        return resultado

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

def confirmar_salida_multiple(
    *,
    id_pedido: int,
    tipo_salida: str,
    detalle: list[dict[str, Any]],
    pedidos_adicionales: list[int],
    observaciones: str | None = None,
    destino_saldo: str = "PENDIENTE",
    motivo_saldo: str | None = None,
) -> dict[str, Any]:
    if id_pedido <= 0:
        raise ErrorSalidaPedido(
            "Debe seleccionar un pedido."
        )

    tipo_salida = tipo_salida.strip().upper()

    if tipo_salida not in (
        "ENTREGADO",
        "LLEVAR",
    ):
        raise ErrorSalidaPedido(
            "El tipo de salida no es válido."
        )

    destino_saldo = (
        destino_saldo.strip().upper()
        if destino_saldo
        else "PENDIENTE"
    )

    detalle_json: list[dict[str, Any]] = []

    for renglon in detalle:
        cantidad = Decimal(
            str(renglon["cantidad"])
        )

        if cantidad <= 0:
            continue

        detalle_json.append(
            {
                "id_pedido_detalle":
                    int(renglon["id_pedido_detalle"]),

                "cantidad":
                    format(cantidad, "f"),
            }
        )

    if not detalle_json:
        raise ErrorSalidaPedido(
            "No se indicó ninguna cantidad "
            "para entregar."
        )

    texto_detalle = json.dumps(
        detalle_json,
        ensure_ascii=False,
    )

    ids_adicionales = [
        int(id_adicional)
        for id_adicional
        in pedidos_adicionales
    ]

    texto_adicionales = json.dumps(
        ids_adicionales,
        ensure_ascii=False,
    )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SET NOCOUNT ON;

            DECLARE @usuario SYSNAME;
            SET @usuario = SUSER_SNAME();

            EXEC pos.ConfirmarSalidaPedidoConAdicionales
                @id_pedido = ?,
                @tipo_salida = ?,
                @detalle_json = ?,
                @observaciones = ?,
                @usuario = @usuario,
                @destino_saldo = ?,
                @motivo_saldo = ?,
                @pedidos_adicionales_json = ?;
            """,
            (
                id_pedido,
                tipo_salida,
                texto_detalle,
                observaciones,
                destino_saldo,
                motivo_saldo,
                texto_adicionales,
            ),
        )

        salidas: list[dict[str, Any]] = []
        resumen: dict[str, Any] | None = None

        while True:
            if cursor.description is not None:
                columnas = [
                    columna[0].lower()
                    for columna in cursor.description
                ]

                if (
                    "id_pedido" in columnas
                    and "id_venta" in columnas
                    and "es_adicional" in columnas
                ):
                    filas = cursor.fetchall()

                    salidas = [
                        dict(zip(columnas, fila))
                        for fila in filas
                    ]

                elif (
                    "cantidad_pedidos" in columnas
                    and "cantidad_ventas" in columnas
                    and "total_ventas" in columnas
                ):
                    fila = cursor.fetchone()

                    if fila is not None:
                        resumen = dict(
                            zip(columnas, fila)
                        )

            if not cursor.nextset():
                break

        if not salidas:
            raise ErrorSalidaPedido(
                "SQL Server no devolvió las salidas "
                "confirmadas."
            )

        conexion.commit()

        return {
            "salidas": salidas,
            "resumen": resumen or {},
        }

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

def cancelar_pedido(
    *,
    id_pedido: int,
    motivo: str,
) -> dict[str, Any]:
    if id_pedido <= 0:
        raise ErrorSalidaPedido(
            "Debe seleccionar un pedido."
        )

    motivo = motivo.strip()

    if not motivo:
        raise ErrorSalidaPedido(
            "Debe indicar el motivo de la cancelación."
        )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SET NOCOUNT ON;

            DECLARE @usuario SYSNAME;

            SET @usuario = SUSER_SNAME();

            EXEC pos.CancelarPedido
                @id_pedido = ?,
                @motivo = ?,
                @usuario = @usuario;
            """,
            (
                id_pedido,
                motivo,
            ),
        )

        resultado = None

        columnas_esperadas = {
            "id_pedido",
            "estado_pedido",
            "cantidad_cancelada",
            "detalles_cancelados",
            "planes_cancelados",
            "motivo",
        }

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
                        resultado = dict(
                            zip(columnas, fila)
                        )

                    break

            if not cursor.nextset():
                break

        if resultado is None:
            raise ErrorSalidaPedido(
                "SQL Server no devolvió el resultado "
                "de la cancelación."
            )

        conexion.commit()

        return resultado

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

def cancelar_saldo_pedido(
    *,
    id_pedido: int,
    motivo: str,
) -> dict[str, Any]:
    if id_pedido <= 0:
        raise ErrorSalidaPedido(
            "Debe seleccionar un pedido."
        )

    motivo = motivo.strip()

    if not motivo:
        raise ErrorSalidaPedido(
            "Debe indicar el motivo de la "
            "cancelación del saldo."
        )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SET NOCOUNT ON;

            DECLARE @usuario SYSNAME;

            SET @usuario = SUSER_SNAME();

            EXEC pos.CancelarSaldoPedido
                @id_pedido = ?,
                @motivo = ?,
                @usuario = @usuario;
            """,
            (
                id_pedido,
                motivo,
            ),
        )

        resultado = None

        columnas_esperadas = {
            "id_pedido",
            "estado_anterior",
            "estado_pedido",
            "cantidad_entregada",
            "cantidad_cancelada",
            "detalles_cancelados",
            "planes_cancelados",
            "motivo",
        }

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
                        resultado = dict(
                            zip(columnas, fila)
                        )

                    break

            if not cursor.nextset():
                break

        if resultado is None:
            raise ErrorSalidaPedido(
                "SQL Server no devolvió el resultado "
                "de la cancelación del saldo."
            )

        conexion.commit()

        return resultado

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

def reprogramar_saldo_pedido(
    *,
    id_pedido_origen: int,
    fecha_entrega_nueva: date,
    motivo: str,
    hora_entrega_nueva: time | None = None,
    fecha_elaboracion_nueva: date | None = None,
    importe_envio_nuevo: Decimal | int | float | str = Decimal("0"),
    observaciones_nuevo: str | None = None,
) -> dict[str, Any]:
    if id_pedido_origen <= 0:
        raise ErrorSalidaPedido(
            "Debe seleccionar un pedido."
        )

    if not isinstance(fecha_entrega_nueva, date):
        raise ErrorSalidaPedido(
            "Debe indicar una nueva fecha de entrega válida."
        )

    motivo = motivo.strip()

    if not motivo:
        raise ErrorSalidaPedido(
            "Debe indicar el motivo de la reprogramación."
        )

    if (
        fecha_elaboracion_nueva is not None
        and not isinstance(
            fecha_elaboracion_nueva,
            date,
        )
    ):
        raise ErrorSalidaPedido(
            "La fecha de elaboración no es válida."
        )

    if (
        hora_entrega_nueva is not None
        and not isinstance(
            hora_entrega_nueva,
            time,
        )
    ):
        raise ErrorSalidaPedido(
            "La hora de entrega no es válida."
        )

    if hora_entrega_nueva is not None:
        hora_entrega_nueva = (
            hora_entrega_nueva.replace(
                microsecond=0
            )
        )

    try:
        importe_envio = Decimal(
            str(importe_envio_nuevo)
        )
    except Exception as exc:
        raise ErrorSalidaPedido(
            "El importe de envío no es válido."
        ) from exc

    if importe_envio < 0:
        raise ErrorSalidaPedido(
            "El importe de envío no puede ser negativo."
        )

    observaciones_nuevo = (
        observaciones_nuevo.strip()
        if observaciones_nuevo
        else None
    )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SET NOCOUNT ON;

            DECLARE @id_pedido_destino BIGINT;
            DECLARE @id_reprogramacion BIGINT;
            DECLARE @usuario SYSNAME;

            SET @usuario = SUSER_SNAME();

            EXEC pos.ReprogramarSaldoPedido
                @id_pedido_origen = ?,
                @fecha_entrega_nueva = ?,
                @motivo = ?,
                @hora_entrega_nueva = ?,
                @fecha_elaboracion_nueva = ?,
                @importe_envio_nuevo = ?,
                @observaciones_nuevo = ?,
                @usuario = @usuario,

                @id_pedido_destino =
                    @id_pedido_destino OUTPUT,

                @id_reprogramacion =
                    @id_reprogramacion OUTPUT;
            """,
            (
                id_pedido_origen,
                fecha_entrega_nueva,
                motivo,
                hora_entrega_nueva,
                fecha_elaboracion_nueva,
                importe_envio,
                observaciones_nuevo,
            ),
        )

        resultado = None

        columnas_esperadas = {
            "id_reprogramacion",
            "id_pedido_origen",
            "estado_pedido_origen",
            "id_pedido_destino",
            "estado_pedido_destino",
            "fecha_elaboracion_nueva",
            "fecha_entrega_nueva",
            "cantidad_reprogramada",
            "descuento_reprogramado",
            "detalles_reprogramados",
            "planes_cancelados",
            "importe_envio_nuevo",
            "total_pedido_nuevo",
            "motivo",
        }

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
                        resultado = dict(
                            zip(columnas, fila)
                        )

                    break

            if not cursor.nextset():
                break

        if resultado is None:
            raise ErrorSalidaPedido(
                "SQL Server no devolvió el resultado "
                "de la reprogramación del saldo."
            )

        conexion.commit()

        return resultado

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

def crear_pedido_adicional(
    *,
    id_pedido_origen: int,
    id_pedido_detalle_origen: int,
    cantidad_adicional: Decimal,
    observaciones: str | None = None,
) -> dict[str, Any]:
    if id_pedido_origen <= 0:
        raise ErrorSalidaPedido(
            "Debe indicar un pedido de origen válido."
        )

    if id_pedido_detalle_origen <= 0:
        raise ErrorSalidaPedido(
            "Debe indicar un detalle de pedido válido."
        )

    if cantidad_adicional <= 0:
        raise ErrorSalidaPedido(
            "La cantidad adicional debe ser mayor que cero."
        )

    observaciones = (
        observaciones.strip()
        if observaciones
        else None
    )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SET NOCOUNT ON;

            DECLARE @id_pedido_destino BIGINT;
            DECLARE @id_pedido_detalle_destino BIGINT;
            DECLARE @id_pedido_adicional BIGINT;

            EXEC pos.CrearPedidoAdicional
                @id_pedido_origen = ?,
                @id_pedido_detalle_origen = ?,
                @cantidad_adicional = ?,
                @observaciones = ?,
                @usuario = NULL,

                @id_pedido_destino =
                    @id_pedido_destino OUTPUT,

                @id_pedido_detalle_destino =
                    @id_pedido_detalle_destino OUTPUT,

                @id_pedido_adicional =
                    @id_pedido_adicional OUTPUT;
            """,
            (
                id_pedido_origen,
                id_pedido_detalle_origen,
                cantidad_adicional,
                observaciones,
            ),
        )

        resultado = None

        columnas_esperadas = {
            "id_pedido_adicional",
            "id_pedido_origen",
            "id_pedido_detalle_origen",
            "id_pedido_destino",
            "id_pedido_detalle_destino",
            "id_producto",
            "descripcion_producto",
            "cantidad_pendiente_origen",
            "cantidad_adicional",
            "precio_unitario",
            "descuento_adicional",
            "total_adicional",
            "fecha_elaboracion",
            "fecha_entrega",
            "modalidad_entrega",
        }

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
                        resultado = dict(
                            zip(columnas, fila)
                        )

                    break

            if not cursor.nextset():
                break

        if resultado is None:
            raise ErrorSalidaPedido(
                "SQL Server no devolvió el resultado "
                "del pedido adicional."
            )

        conexion.commit()

        return resultado

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()