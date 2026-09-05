from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from db.conexion import abrir_conexion


class ErrorCobro(Exception):
    """Error del circuito de cobros."""


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


def _importe(valor: Any) -> Decimal:
    importe = Decimal(str(valor))

    return importe.quantize(
        Decimal("0.01")
    )


def obtener_caja_abierta() -> dict[str, Any] | None:
    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        fila = cursor.execute(
            """
            SELECT TOP (1)
                id_caja_sesion,
                id_caja,
                caja,
                fecha_apertura,
                usuario_apertura,
                saldo_inicial
            FROM pos.vw_CajaSesionAbierta
            ORDER BY
                fecha_apertura DESC,
                id_caja_sesion DESC;
            """
        ).fetchone()

        if fila is None:
            return None

        columnas = [
            columna[0].lower()
            for columna in cursor.description
        ]

        return dict(
            zip(columnas, fila)
        )

    finally:
        conexion.close()


def listar_clientes_con_saldo(
    busqueda: str | None = None,
) -> list[dict[str, Any]]:
    condiciones = [
        "saldo > 0"
    ]

    parametros: list[Any] = []

    if busqueda:
        condiciones.append(
            "nombre LIKE ?"
        )
        parametros.append(
            f"%{busqueda.strip()}%"
        )

    sentencia = f"""
        SELECT
            id_cliente,
            nombre,
            total_ventas,
            total_cobros,
            saldo
        FROM pos.vw_CuentaCorrienteSaldo
        WHERE {' AND '.join(condiciones)}
        ORDER BY
            nombre,
            id_cliente;
    """

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            sentencia,
            tuple(parametros),
        ).fetchall()

        return _filas_a_diccionarios(
            cursor,
            filas,
        )

    finally:
        conexion.close()


def listar_ventas_pendientes(
    id_cliente: int,
) -> list[dict[str, Any]]:
    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            SELECT
                id_venta,
                id_cliente,
                fecha_hora,
                total,
                importe_cobrado,
                saldo_pendiente
            FROM pos.vw_VentaSaldo
            WHERE id_cliente = ?
              AND saldo_pendiente > 0
            ORDER BY
                fecha_hora,
                id_venta;
            """,
            id_cliente,
        ).fetchall()

        return _filas_a_diccionarios(
            cursor,
            filas,
        )

    finally:
        conexion.close()


def listar_medios_pago() -> list[dict[str, Any]]:
    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            SELECT
                id_medio_pago,
                codigo,
                descripcion,
                requiere_referencia
            FROM pos.MedioPago
            WHERE activo = 1
            ORDER BY
                descripcion,
                id_medio_pago;
            """
        ).fetchall()

        return _filas_a_diccionarios(
            cursor,
            filas,
        )

    finally:
        conexion.close()


def registrar_cobro(
    *,
    id_cliente: int,
    id_caja_sesion: int,
    medios_pago: list[dict[str, Any]],
    aplicaciones: list[dict[str, Any]] | None,
    aplicar_automaticamente: bool,
    observaciones: str | None = None,
) -> dict[str, Any]:
    if id_cliente <= 0:
        raise ErrorCobro(
            "Debe seleccionar un cliente."
        )

    if id_caja_sesion <= 0:
        raise ErrorCobro(
            "No existe una sesión de caja válida."
        )

    if not medios_pago:
        raise ErrorCobro(
            "Debe informar al menos un medio de pago."
        )

    medios_json: list[dict[str, Any]] = []

    for medio in medios_pago:
        importe = _importe(
            medio["importe"]
        )

        if importe <= 0:
            raise ErrorCobro(
                "Los importes de los medios de pago "
                "deben ser mayores que cero."
            )

        referencia = (
            str(medio.get("referencia") or "").strip()
            or None
        )

        medios_json.append(
            {
                "id_medio_pago":
                    int(medio["id_medio_pago"]),

                "importe":
                    format(importe, ".2f"),

                "referencia":
                    referencia,
            }
        )

    aplicaciones_json: list[
        dict[str, Any]
    ] = []

    for aplicacion in aplicaciones or []:
        importe = _importe(
            aplicacion["importe"]
        )

        if importe <= 0:
            continue

        aplicaciones_json.append(
            {
                "id_venta":
                    int(aplicacion["id_venta"]),

                "importe":
                    format(importe, ".2f"),
            }
        )

    texto_medios = json.dumps(
        medios_json,
        ensure_ascii=False,
    )

    texto_aplicaciones = (
        json.dumps(
            aplicaciones_json,
            ensure_ascii=False,
        )
        if aplicaciones_json
        else None
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

            DECLARE @id_cobro BIGINT;

            EXEC pos.RegistrarCobro
                @id_cliente = ?,
                @id_caja_sesion = ?,
                @medios_pago_json = ?,
                @aplicaciones_json = ?,
                @aplicar_automaticamente = ?,
                @observaciones = ?,
                @usuario = NULL,
                @id_cobro = @id_cobro OUTPUT;
            """,
            (
                id_cliente,
                id_caja_sesion,
                texto_medios,
                texto_aplicaciones,
                int(aplicar_automaticamente),
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

                if "id_cobro" in columnas:
                    fila = cursor.fetchone()

                    if fila is not None:
                        resultado = dict(
                            zip(columnas, fila)
                        )

                    break

            if not cursor.nextset():
                break

        if resultado is None:
            raise ErrorCobro(
                "SQL Server no devolvió el resultado "
                "del cobro."
            )

        conexion.commit()

        return resultado

    except Exception as error:
        conexion.rollback()

        texto_error = str(error)

        if "(50121)" in texto_error:
            raise ErrorCobro(
                "El mismo comprobante fue ingresado "
                "más de una vez en este cobro."
            ) from error

        if "(50122)" in texto_error:
            raise ErrorCobro(
                "El comprobante informado ya fue utilizado "
                "en otro cobro confirmado."
            ) from error

        raise

    finally:
        conexion.close()