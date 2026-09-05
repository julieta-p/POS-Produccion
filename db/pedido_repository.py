from __future__ import annotations

import json
from datetime import date, time
from decimal import Decimal
from typing import Any

from db.conexion import abrir_conexion


class ErrorPedido(Exception):
    """Error al consultar o guardar pedidos."""


def _filas_a_diccionarios(cursor, filas) -> list[dict[str, Any]]:
    columnas = [
        descripcion[0].lower()
        for descripcion in cursor.description
    ]

    return [
        dict(zip(columnas, fila))
        for fila in filas
    ]


def listar_clientes() -> list[dict[str, Any]]:
    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            SELECT
                id_cliente,
                nombre,
                direccion
            FROM pos.vw_ClienteActivo
            ORDER BY id_cliente;
            """
        ).fetchall()

        return _filas_a_diccionarios(cursor, filas)

    finally:
        conexion.close()

def agregar_cliente(
    *,
    nombre: str,
    direccion: str | None = None,
    localidad: str | None = None,
    telefono: str | None = None,
    celular: str | None = None,
) -> int:
    nombre = nombre.strip()

    if not nombre:
        raise ErrorPedido(
            "Debe indicar el nombre del cliente."
        )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SET NOCOUNT ON;

            DECLARE @id_cliente INT;

            EXEC pos.AgregarCliente
                @nombre = ?,
                @direccion = ?,
                @localidad = ?,
                @telefono = ?,
                @celular = ?,
                @id_cliente = @id_cliente OUTPUT;

            SELECT
                @id_cliente AS id_cliente;
            """,
            (
                nombre,
                direccion,
                localidad,
                telefono,
                celular,
            ),
        )

        fila = cursor.fetchone()

        if (
            fila is None
            or fila.id_cliente is None
        ):
            raise ErrorPedido(
                "SQL Server no devolvió "
                "el número del cliente."
            )

        id_cliente = int(
            fila.id_cliente
        )

        conexion.commit()

        return id_cliente

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()


def listar_modalidades() -> list[str]:
    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            SELECT *
            FROM pos.vw_ModalidadEntregaActiva;
            """
        ).fetchall()

        datos = _filas_a_diccionarios(cursor, filas)

        candidatos = (
            "modalidad_entrega",
            "codigo",
            "modalidad",
            "descripcion",
        )

        modalidades: list[str] = []

        for fila in datos:
            valor = None

            for campo in candidatos:
                if fila.get(campo) is not None:
                    valor = str(fila[campo]).strip()
                    break

            if valor:
                modalidades.append(valor)

        return sorted(set(modalidades))

    finally:
        conexion.close()


def listar_productos() -> list[dict[str, Any]]:
    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            SELECT
                id_producto,
                descripcion,
                precio_menor,
                precio_mayor,
                stock_actual
            FROM pos.vw_ProductoPedido
            ORDER BY id_producto;
            """
        ).fetchall()

        return _filas_a_diccionarios(cursor, filas)

    finally:
        conexion.close()


def _numero_json(valor: Decimal) -> int | float:
    if valor == valor.to_integral_value():
        return int(valor)

    return float(valor)


def guardar_pedido(
    *,
    id_cliente: int,
    modalidad_entrega: str,
    fecha_entrega: date,
    hora_entrega: time | None,
    fecha_elaboracion: date | None,
    requiere_confirmacion: bool,
    direccion_entrega: str | None,
    importe_envio: Decimal,
    observaciones: str | None,
    detalle: list[dict[str, Any]],
) -> int:
    if id_cliente <= 0:
        raise ErrorPedido("Debe seleccionar un cliente.")

    modalidad_entrega = modalidad_entrega.strip().upper()

    if not modalidad_entrega:
        raise ErrorPedido(
            "Debe seleccionar una modalidad de entrega."
        )

    if importe_envio < 0:
        raise ErrorPedido(
            "El importe de envío no puede ser negativo."
        )

    if not detalle:
        raise ErrorPedido(
            "El pedido debe contener al menos un producto."
        )

    if (
        fecha_elaboracion is not None
        and fecha_elaboracion > fecha_entrega
    ):
        raise ErrorPedido(
            "La fecha de elaboración no puede ser posterior "
            "a la fecha de entrega."
        )

    detalle_json = json.dumps(
        [
            {
                "id_producto": int(item["id_producto"]),
                "cantidad": _numero_json(
                    Decimal(str(item["cantidad"]))
                ),
                "tipo_precio": str(
                    item["tipo_precio"]
                ).upper(),
                "precio_unitario": _numero_json(
                    Decimal(str(item["precio_unitario"]))
                ),
                "descuento": _numero_json(
                    Decimal(str(item.get("descuento", 0)))
                ),
                "observaciones": (
                    str(item["observaciones"]).strip()
                    if item.get("observaciones")
                    else None
                ),
            }
            for item in detalle
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        hora_sql = (
            hora_entrega.strftime("%H:%M:%S")
            if hora_entrega is not None
            else None
        )

        cursor.execute(
            """
            SET NOCOUNT ON;

            DECLARE @id_pedido BIGINT;
            DECLARE @usuario SYSNAME;

            EXEC pos.GuardarPedido
                @id_cliente = ?,
                @modalidad_entrega = ?,
                @fecha_entrega = ?,
                @hora_entrega = ?,
                @fecha_elaboracion = ?,
                @requiere_confirmacion = ?,
                @direccion_entrega = ?,
                @importe_envio = ?,
                @observaciones = ?,
                @detalle_json = ?,
                @usuario = @usuario,
                @id_pedido = @id_pedido OUTPUT;

            SELECT @id_pedido AS id_pedido;
            """,
            (
                id_cliente,
                modalidad_entrega,
                fecha_entrega,
                hora_sql,
                fecha_elaboracion,
                int(requiere_confirmacion),
                direccion_entrega,
                importe_envio,
                observaciones,
                detalle_json,
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

                    if "id_pedido" in columnas:
                        fila = posible_fila
                        break

            if not cursor.nextset():
                break

        if fila is None or fila.id_pedido is None:
            raise ErrorPedido(
                "SQL Server no devolvió el número del pedido."
            )

        id_pedido = int(fila.id_pedido)

        conexion.commit()
        
        return id_pedido

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()