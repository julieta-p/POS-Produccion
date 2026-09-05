from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from db.conexion import abrir_conexion


class ErrorPlanificacion(Exception):
    """Error al consultar o modificar la planificación."""


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
def _obtener_resultado(
    cursor,
    columnas_requeridas: set[str],
) -> dict[str, Any] | None:
    """
    Busca el resultset del procedimiento que contiene
    todas las columnas solicitadas.
    """

    while True:
        if cursor.description is not None:
            columnas = [
                columna[0].lower()
                for columna in cursor.description
            ]

            fila = cursor.fetchone()

            if (
                fila is not None
                and columnas_requeridas.issubset(
                    set(columnas)
                )
            ):
                return dict(
                    zip(columnas, fila)
                )

        if not cursor.nextset():
            return None

def listar_planificacion_productos(
    *,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    modalidad: str | None = None,
    solo_pendientes: bool = True,
) -> list[dict[str, Any]]:
    condiciones = ["1 = 1"]
    parametros: list[Any] = []

    if fecha_desde is not None:
        condiciones.append(
            "fecha_elaboracion_sugerida >= ?"
        )
        parametros.append(fecha_desde)

    if fecha_hasta is not None:
        condiciones.append(
            "fecha_elaboracion_sugerida <= ?"
        )
        parametros.append(fecha_hasta)

    if modalidad:
        condiciones.append(
            "modalidad_entrega = ?"
        )
        parametros.append(
            modalidad.strip().upper()
        )

    having_pendiente = (
        """
        HAVING
            SUM(cantidad_sin_planificar) > 0
        """
        if solo_pendientes
        else ""
    )

    sentencia = f"""
        WITH base AS
        (
            SELECT
                v.id_pedido,
                v.id_pedido_detalle,
                v.id_producto,
                v.descripcion_producto,

                p.fecha_entrega,
                p.hora_entrega,
                UPPER(p.modalidad_entrega)
                    AS modalidad_entrega,

                COALESCE(
                    p.fecha_elaboracion,
                    CASE
                        WHEN UPPER(
                            p.modalidad_entrega
                        ) = 'REPARTO'
                        THEN DATEADD(
                            DAY,
                            -1,
                            p.fecha_entrega
                        )
                        ELSE p.fecha_entrega
                    END
                ) AS fecha_elaboracion_sugerida,

                v.cantidad
                    - ISNULL(
                        v.cantidad_cancelada,
                        0
                    )
                    AS cantidad_neta,

                ISNULL(
                    v.cantidad_desde_stock,
                    0
                ) AS cantidad_desde_stock,

                ISNULL(
                    v.cantidad_planificada,
                    0
                ) AS cantidad_planificada,

                ISNULL(
                    v.cantidad_sin_planificar,
                    0
                ) AS cantidad_sin_planificar,

                ISNULL(
                    v.stock_actual,
                    0
                ) AS stock_actual

            FROM pos.vw_PedidoPlanificacion v

            INNER JOIN pos.Pedido p
                ON p.id_pedido = v.id_pedido
        )

        SELECT
            id_producto,
            descripcion_producto,
            fecha_elaboracion_sugerida,

            COUNT(DISTINCT id_pedido)
                AS cantidad_pedidos,

            COUNT(*)
                AS cantidad_detalles,

            SUM(cantidad_neta)
                AS cantidad,

            SUM(cantidad_desde_stock)
                AS cantidad_desde_stock,

            SUM(cantidad_planificada)
                AS cantidad_planificada,

            SUM(cantidad_sin_planificar)
                AS cantidad_sin_planificar,

            MAX(stock_actual)
                AS stock_actual,

            MIN(fecha_entrega)
                AS primera_entrega,

            MAX(fecha_entrega)
                AS ultima_entrega

        FROM base

        WHERE {' AND '.join(condiciones)}

        GROUP BY
            id_producto,
            descripcion_producto,
            fecha_elaboracion_sugerida

        {having_pendiente}

        ORDER BY
            fecha_elaboracion_sugerida,
            descripcion_producto,
            id_producto;
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

def listar_detalles_grupo(
    *,
    id_producto: int,
    fecha_grupo: date,
    modalidad: str | None = None,
) -> list[dict[str, Any]]:
    if id_producto <= 0:
        raise ErrorPlanificacion(
            "Debe seleccionar un producto."
        )

    condiciones = [
        "id_producto = ?",
        "fecha_elaboracion_sugerida = ?",
        "cantidad_sin_planificar > 0",
    ]

    parametros: list[Any] = [
        id_producto,
        fecha_grupo,
    ]

    if modalidad:
        condiciones.append(
            "modalidad_entrega = ?"
        )
        parametros.append(
            modalidad.strip().upper()
        )

    sentencia = f"""
        WITH base AS
        (
            SELECT
                v.id_pedido,
                v.id_pedido_detalle,
                v.id_producto,
                v.descripcion_producto,
                v.cliente,

                p.fecha_entrega,
                p.hora_entrega,

                UPPER(p.modalidad_entrega)
                    AS modalidad_entrega,

                COALESCE(
                    p.fecha_elaboracion,
                    CASE
                        WHEN UPPER(
                            p.modalidad_entrega
                        ) = 'REPARTO'
                        THEN DATEADD(
                            DAY,
                            -1,
                            p.fecha_entrega
                        )
                        ELSE p.fecha_entrega
                    END
                ) AS fecha_elaboracion_sugerida,

                v.cantidad
                    - ISNULL(
                        v.cantidad_cancelada,
                        0
                    )
                    AS cantidad_neta,

                ISNULL(
                    v.cantidad_desde_stock,
                    0
                ) AS cantidad_desde_stock,

                ISNULL(
                    v.cantidad_planificada,
                    0
                ) AS cantidad_planificada,

                ISNULL(
                    v.cantidad_sin_planificar,
                    0
                ) AS cantidad_sin_planificar

            FROM pos.vw_PedidoPlanificacion v

            INNER JOIN pos.Pedido p
                ON p.id_pedido = v.id_pedido
        )

        SELECT
            id_pedido,
            id_pedido_detalle,
            id_producto,
            descripcion_producto,
            cliente,
            fecha_entrega,
            hora_entrega,
            modalidad_entrega,
            cantidad_neta AS cantidad,
            cantidad_desde_stock,
            cantidad_planificada,
            cantidad_sin_planificar

        FROM base

        WHERE {' AND '.join(condiciones)}

        ORDER BY
            fecha_entrega,
            CASE
                WHEN hora_entrega IS NULL
                    THEN CAST(
                        '23:59:59'
                        AS TIME
                    )
                ELSE hora_entrega
            END,
            id_pedido,
            id_pedido_detalle;
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

def listar_planes_grupo(
    *,
    id_producto: int,
    fecha_grupo: date,
    modalidad: str | None = None,
) -> list[dict[str, Any]]:
    if id_producto <= 0:
        raise ErrorPlanificacion(
            "Debe seleccionar un producto."
        )

    condiciones = [
        "base.id_producto = ?",
        "base.fecha_elaboracion_sugerida = ?",
    ]

    parametros: list[Any] = [
        id_producto,
        fecha_grupo,
    ]

    if modalidad:
        condiciones.append(
            "base.modalidad_entrega = ?"
        )
        parametros.append(
            modalidad.strip().upper()
        )

    sentencia = f"""
        WITH base AS
        (
            SELECT DISTINCT
                v.id_pedido_detalle,
                v.id_producto,

                UPPER(p.modalidad_entrega)
                    AS modalidad_entrega,

                COALESCE(
                    p.fecha_elaboracion,
                    CASE
                        WHEN UPPER(
                            p.modalidad_entrega
                        ) = 'REPARTO'
                        THEN DATEADD(
                            DAY,
                            -1,
                            p.fecha_entrega
                        )
                        ELSE p.fecha_entrega
                    END
                ) AS fecha_elaboracion_sugerida

            FROM pos.vw_PedidoPlanificacion v

            INNER JOIN pos.Pedido p
                ON p.id_pedido = v.id_pedido
        )

        SELECT
            pe.fecha_elaboracion,

            SUM(pe.cantidad)
                AS cantidad,

            pe.estado,

            COUNT(DISTINCT pe.id_pedido_detalle)
                AS cantidad_detalles,

            CASE
                WHEN COUNT(
                    DISTINCT ISNULL(
                        pe.observaciones,
                        N''
                    )
                ) <= 1
                THEN MAX(pe.observaciones)
                ELSE N'Varias observaciones'
            END AS observaciones

        FROM base

        INNER JOIN pos.PedidoPlanElaboracion pe
            ON pe.id_pedido_detalle =
                base.id_pedido_detalle

        WHERE {' AND '.join(condiciones)}

        GROUP BY
            pe.fecha_elaboracion,
            pe.estado

        ORDER BY
            pe.fecha_elaboracion,
            pe.estado;
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

def buscar_contexto_pedido(
    id_pedido: int,
) -> dict[str, Any] | None:
    if id_pedido <= 0:
        raise ErrorPlanificacion(
            "El pedido indicado no es válido."
        )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        fila = cursor.execute(
            """
            SELECT TOP (1)
                v.id_pedido,
                v.id_pedido_detalle,
                v.id_producto,
                v.descripcion_producto,

                COALESCE(
                    p.fecha_elaboracion,
                    CASE
                        WHEN UPPER(
                            p.modalidad_entrega
                        ) = 'REPARTO'
                        THEN DATEADD(
                            DAY,
                            -1,
                            p.fecha_entrega
                        )
                        ELSE p.fecha_entrega
                    END
                ) AS fecha_elaboracion_sugerida,

                p.fecha_entrega,
                UPPER(
                    p.modalidad_entrega
                ) AS modalidad_entrega,

                ISNULL(
                    v.cantidad_sin_planificar,
                    0
                ) AS cantidad_sin_planificar

            FROM pos.vw_PedidoPlanificacion v

            INNER JOIN pos.Pedido p
                ON p.id_pedido = v.id_pedido

            WHERE v.id_pedido = ?
              AND ISNULL(
                    v.cantidad_sin_planificar,
                    0
                  ) > 0

            ORDER BY
                v.id_pedido_detalle;
            """,
            id_pedido,
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

def guardar_plan_producto(
    *,
    id_producto: int,
    fecha_grupo: date,
    fecha_elaboracion: date,
    cantidad: Decimal,
    observaciones: str | None,
    modalidad: str | None = None,
) -> dict[str, Any]:
    if id_producto <= 0:
        raise ErrorPlanificacion(
            "Debe seleccionar un producto."
        )

    if cantidad <= 0:
        raise ErrorPlanificacion(
            "La cantidad a elaborar debe ser "
            "mayor que cero."
        )

    modalidad_sql = (
        modalidad.strip().upper()
        if modalidad
        else None
    )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            EXEC pos.GuardarPlanElaboracionProducto
                @id_producto = ?,
                @fecha_grupo = ?,
                @modalidad = ?,
                @fecha_elaboracion = ?,
                @cantidad = ?,
                @observaciones = ?,
                @usuario = NULL;
            """,
            (
                id_producto,
                fecha_grupo,
                modalidad_sql,
                fecha_elaboracion,
                cantidad,
                observaciones,
            ),
        )

        resultado = _obtener_resultado(
            cursor,
            {
                "id_producto",
                "fecha_grupo",
                "fecha_elaboracion",
                "cantidad_planificada",
                "detalles_afectados",
                "cantidad_grupo_sin_planificar",
            },
        )

        if resultado is None:
            raise ErrorPlanificacion(
                "SQL Server no devolvió el "
                "resultado de la planificación."
            )

        conexion.commit()

        return resultado

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()



def listar_planificacion(
    *,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    modalidad: str | None = None,
    solo_pendientes: bool = True,
) -> list[dict[str, Any]]:
    condiciones = ["1 = 1"]
    parametros: list[Any] = []

    if fecha_desde is not None:
        condiciones.append(
            "fecha_elaboracion_sugerida >= ?"
        )
        parametros.append(fecha_desde)

    if fecha_hasta is not None:
        condiciones.append(
            "fecha_elaboracion_sugerida <= ?"
        )
        parametros.append(fecha_hasta)

    if modalidad:
        condiciones.append(
            "modalidad_entrega = ?"
        )
        parametros.append(
            modalidad.strip().upper()
        )

    filtro_pendientes = (
        """
        HAVING
            SUM(cantidad_sin_planificar) > 0
        """
        if solo_pendientes
        else ""
    )

    sentencia = f"""
        WITH base AS
        (
            SELECT
                id_pedido,
                id_pedido_detalle,
                id_producto,
                descripcion_producto,
                fecha_entrega,
                modalidad_entrega,

                CASE
                    WHEN UPPER(modalidad_entrega)
                        = 'REPARTO'
                    THEN DATEADD(
                        DAY,
                        -1,
                        fecha_entrega
                    )
                    ELSE fecha_entrega
                END
                    AS fecha_elaboracion_sugerida,

                cantidad
                    - ISNULL(
                        cantidad_cancelada,
                        0
                    )
                    AS cantidad_neta,

                ISNULL(
                    cantidad_desde_stock,
                    0
                )
                    AS cantidad_desde_stock,

                ISNULL(
                    cantidad_planificada,
                    0
                )
                    AS cantidad_planificada,

                ISNULL(
                    cantidad_sin_planificar,
                    0
                )
                    AS cantidad_sin_planificar,

                ISNULL(
                    stock_actual,
                    0
                )
                    AS stock_actual

            FROM pos.vw_PedidoPlanificacion
        )

        SELECT
            id_producto,
            descripcion_producto,
            fecha_elaboracion_sugerida,

            COUNT(DISTINCT id_pedido)
                AS cantidad_pedidos,

            COUNT(*)
                AS cantidad_detalles,

            SUM(cantidad_neta)
                AS cantidad,

            SUM(cantidad_desde_stock)
                AS cantidad_desde_stock,

            SUM(cantidad_planificada)
                AS cantidad_planificada,

            SUM(cantidad_sin_planificar)
                AS cantidad_sin_planificar,

            MAX(stock_actual)
                AS stock_actual,

            MIN(fecha_entrega)
                AS primera_entrega,

            MAX(fecha_entrega)
                AS ultima_entrega

        FROM base

        WHERE {' AND '.join(condiciones)}

        GROUP BY
            id_producto,
            descripcion_producto,
            fecha_elaboracion_sugerida

        {filtro_pendientes}

        ORDER BY
            fecha_elaboracion_sugerida,
            descripcion_producto,
            id_producto;
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



def listar_planes_detalle(
    id_pedido_detalle: int,
) -> list[dict[str, Any]]:
    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            SELECT
                id_plan_elaboracion,
                fecha_elaboracion,
                cantidad,
                estado,
                observaciones
            FROM pos.PedidoPlanElaboracion
            WHERE id_pedido_detalle = ?
            ORDER BY fecha_elaboracion;
            """,
            id_pedido_detalle,
        ).fetchall()

        return _filas_a_diccionarios(
            cursor,
            filas,
        )

    finally:
        conexion.close()


def asignar_stock(
    *,
    id_pedido_detalle: int,
    cantidad_desde_stock: Decimal,
) -> None:
    if id_pedido_detalle <= 0:
        raise ErrorPlanificacion(
            "Debe seleccionar un detalle de pedido."
        )

    if cantidad_desde_stock < 0:
        raise ErrorPlanificacion(
            "La cantidad desde stock no puede ser negativa."
        )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            EXEC pos.AsignarStockPedidoDetalle
                @id_pedido_detalle = ?,
                @cantidad_desde_stock = ?,
                @usuario = NULL;
            """,
            (
                id_pedido_detalle,
                cantidad_desde_stock,
            ),
        )

        conexion.commit()

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()


def guardar_plan(
    *,
    id_pedido_detalle: int,
    fecha_elaboracion: date,
    cantidad: Decimal,
    observaciones: str | None,
) -> int:
    if id_pedido_detalle <= 0:
        raise ErrorPlanificacion(
            "Debe seleccionar un detalle de pedido."
        )

    if cantidad <= 0:
        raise ErrorPlanificacion(
            "La cantidad a elaborar debe ser mayor que cero."
        )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            EXEC pos.GuardarPlanElaboracion
                @id_pedido_detalle = ?,
                @fecha_elaboracion = ?,
                @cantidad = ?,
                @observaciones = ?,
                @usuario = NULL;
            """,
            (
                id_pedido_detalle,
                fecha_elaboracion,
                cantidad,
                observaciones,
            ),
        )

        fila_resultado = None

        while True:
            if cursor.description is not None:
                fila = cursor.fetchone()

                if fila is not None:
                    columnas = [
                        columna[0].lower()
                        for columna in cursor.description
                    ]

                    if "id_plan_elaboracion" in columnas:
                        fila_resultado = dict(
                            zip(columnas, fila)
                        )
                        break

            if not cursor.nextset():
                break

        if fila_resultado is None:
            raise ErrorPlanificacion(
                "SQL Server no devolvió el plan creado."
            )

        conexion.commit()

        return int(
            fila_resultado["id_plan_elaboracion"]
        )

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

