from __future__ import annotations

import json

from decimal import Decimal
from typing import Any

from db.conexion import abrir_conexion


def _fila_a_diccionario(cursor, fila) -> dict[str, Any]:
    columnas = [
        descripcion[0].lower()
        for descripcion in cursor.description
    ]

    return dict(zip(columnas, fila))


def _obtener_primer_resultado(cursor) -> dict[str, Any] | None:
    """
    Busca el primer conjunto de resultados que contenga una fila.

    Es útil porque un procedimiento almacenado puede devolver varios
    resultados intermedios antes del SELECT final.
    """

    while True:
        if cursor.description is not None:
            fila = cursor.fetchone()

            if fila is not None:
                return _fila_a_diccionario(cursor, fila)

        if not cursor.nextset():
            return None

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


def listar_cajas_activas() -> list[dict[str, Any]]:
    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            SELECT
                id_caja,
                descripcion
            FROM pos.Caja
            WHERE activa = 1
            ORDER BY descripcion;
            """
        ).fetchall()

        columnas = [
            descripcion[0].lower()
            for descripcion in cursor.description
        ]

        return [
            dict(zip(columnas, fila))
            for fila in filas
        ]

    finally:
        conexion.close()


def obtener_sesion_abierta() -> dict[str, Any] | None:
    """
    Devuelve la sesión abierta correspondiente al usuario conectado.

    Si la vista no contiene un campo de usuario, devuelve la primera
    sesión abierta disponible.
    """

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            SELECT
                sesion.*,
                SUSER_SNAME() AS usuario_conexion
            FROM pos.vw_CajaSesionAbierta AS sesion;
            """
        ).fetchall()

        if not filas:
            return None

        columnas = [
            descripcion[0].lower()
            for descripcion in cursor.description
        ]

        sesiones = [
            dict(zip(columnas, fila))
            for fila in filas
        ]

        usuario_conexion = str(
            sesiones[0].get("usuario_conexion", "")
        ).strip().lower()

        posibles_campos_usuario = (
            "usuario_apertura",
            "usuario",
            "usuario_alta",
        )

        for sesion in sesiones:
            for campo in posibles_campos_usuario:
                usuario_sesion = sesion.get(campo)

                if usuario_sesion is None:
                    continue

                if str(usuario_sesion).strip().lower() == usuario_conexion:
                    return sesion

        return sesiones[0]

    finally:
        conexion.close()


def _obtener_parametros_abrir_caja(cursor) -> dict[str, bool]:
    filas = cursor.execute(
        """
        SELECT
            LOWER(parametro.name) AS nombre,
            parametro.is_output
        FROM sys.parameters AS parametro
        WHERE parametro.object_id =
            OBJECT_ID(N'pos.AbrirCaja')
        ORDER BY parametro.parameter_id;
        """
    ).fetchall()

    if not filas:
        raise RuntimeError(
            "No se encontró el procedimiento pos.AbrirCaja "
            "o no contiene parámetros."
        )

    return {
        str(fila[0]).lower(): bool(fila[1])
        for fila in filas
    }


def _buscar_parametro(
    parametros: dict[str, bool],
    opciones: tuple[str, ...],
    *,
    requerido: bool = False,
) -> str | None:
    for opcion in opciones:
        if opcion.lower() in parametros:
            return opcion.lower()

    if requerido:
        raise RuntimeError(
            "No se encontró ninguno de estos parámetros en "
            f"pos.AbrirCaja: {', '.join(opciones)}.\n\n"
            "Parámetros encontrados: "
            + ", ".join(parametros.keys())
        )

    return None


def abrir_caja(
    *,
    id_caja: int,
    saldo_inicial: Decimal,
    observaciones: str | None,
) -> int:
    if id_caja <= 0:
        raise ValueError(
            "Debe seleccionar una caja válida."
        )

    if saldo_inicial < 0:
        raise ValueError(
            "El saldo inicial no puede ser negativo."
        )

    observaciones_limpias = (
        observaciones.strip()
        if observaciones
        else None
    )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        parametros = _obtener_parametros_abrir_caja(cursor)

        parametro_id_caja = _buscar_parametro(
            parametros,
            ("@id_caja",),
            requerido=True,
        )

        parametro_saldo = _buscar_parametro(
            parametros,
            (
                "@saldo_inicial",
                "@importe_inicial",
            ),
            requerido=True,
        )

        parametro_observaciones = _buscar_parametro(
            parametros,
            (
                "@observaciones",
                "@observacion",
            ),
        )

        parametro_usuario = _buscar_parametro(
            parametros,
            (
                "@usuario",
                "@usuario_apertura",
            ),
        )

        parametro_salida = _buscar_parametro(
            parametros,
            (
                "@id_caja_sesion",
                "@id_sesion",
            ),
        )

        asignaciones: list[str] = [
            f"{parametro_id_caja} = ?",
            f"{parametro_saldo} = ?",
        ]

        valores: list[Any] = [
            id_caja,
            saldo_inicial,
        ]

        if parametro_observaciones:
            asignaciones.append(
                f"{parametro_observaciones} = ?"
            )
            valores.append(observaciones_limpias)

        if parametro_usuario:
            declaraciones = (
                "DECLARE @usuario_actual SYSNAME;\n"
                "SET @usuario_actual = SUSER_SNAME();\n"
            )

            asignaciones.append(
                f"{parametro_usuario} = @usuario_actual"
            )
        else:
            declaraciones = ""

        
        seleccion_final = ""

        if parametro_salida:
            declaraciones += (
                f"DECLARE {parametro_salida} BIGINT;\n"
    )
            asignaciones.append(
                f"{parametro_salida} = "
                f"{parametro_salida} OUTPUT"
            )

            seleccion_final = (
                f"\nSELECT {parametro_salida} "
                "AS id_caja_sesion;"
            )

        sentencia = (
            declaraciones
            + "EXEC pos.AbrirCaja\n    "
            + ",\n    ".join(asignaciones)
            + ";"
            + seleccion_final
        )

        cursor.execute(sentencia, valores)

        resultado = _obtener_primer_resultado(cursor)

        conexion.commit()

        if resultado is None:
            raise RuntimeError(
                "La caja fue procesada, pero SQL Server no "
                "devolvió el identificador de la sesión."
            )

        id_sesion = resultado.get("id_caja_sesion")

        if id_sesion is None:
            raise RuntimeError(
                "SQL Server no devolvió el campo "
                "id_caja_sesion."
            )

        return int(id_sesion)

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

def listar_tipos_movimiento_caja(
) -> list[dict[str, Any]]:
    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            SELECT
                id_tipo_movimiento_caja,
                codigo,
                descripcion,
                factor
            FROM pos.TipoMovimientoCaja
            WHERE activo = 1
            ORDER BY
                CASE
                    WHEN factor = -1 THEN 0
                    ELSE 1
                END,
                descripcion;
            """
        ).fetchall()

        columnas = [
            descripcion[0].lower()
            for descripcion in cursor.description
        ]

        return [
            dict(zip(columnas, fila))
            for fila in filas
        ]

    finally:
        conexion.close()

def listar_medios_pago(
) -> list[dict[str, Any]]:
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
            ORDER BY id_medio_pago;
            """
        ).fetchall()

        columnas = [
            descripcion[0].lower()
            for descripcion in cursor.description
        ]

        return [
            dict(zip(columnas, fila))
            for fila in filas
        ]

    finally:
        conexion.close()

def listar_movimientos_caja(
    id_caja_sesion: int,
) -> list[dict[str, Any]]:
    if id_caja_sesion <= 0:
        raise ValueError(
            "Debe indicar una sesión de caja válida."
        )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        filas = cursor.execute(
            """
            SELECT
                cm.id_caja_movimiento,
                cm.id_caja_sesion,
                cm.fecha_hora,

                tmc.id_tipo_movimiento_caja,
                tmc.codigo
                    AS tipo_codigo,
                tmc.descripcion
                    AS tipo_movimiento,
                tmc.factor,

                mp.id_medio_pago,
                mp.codigo
                    AS medio_codigo,
                mp.descripcion
                    AS medio_pago,

                cm.importe,
                cm.concepto,
                cm.observaciones,
                cm.estado,
                cm.usuario_alta,

                cm.fecha_anulacion,
                cm.usuario_anulacion,
                cm.motivo_anulacion

            FROM pos.CajaMovimiento cm

            INNER JOIN pos.TipoMovimientoCaja tmc
                ON tmc.id_tipo_movimiento_caja =
                   cm.id_tipo_movimiento_caja

            INNER JOIN pos.MedioPago mp
                ON mp.id_medio_pago =
                   cm.id_medio_pago

            WHERE cm.id_caja_sesion = ?

            ORDER BY
                cm.fecha_hora DESC,
                cm.id_caja_movimiento DESC;
            """,
            id_caja_sesion,
        ).fetchall()

        columnas = [
            descripcion[0].lower()
            for descripcion in cursor.description
        ]

        return [
            dict(zip(columnas, fila))
            for fila in filas
        ]

    finally:
        conexion.close()

def registrar_movimiento_caja(
    *,
    id_caja_sesion: int,
    id_tipo_movimiento_caja: int,
    id_medio_pago: int,
    importe: Decimal,
    concepto: str,
    observaciones: str | None = None,
) -> dict[str, Any]:
    if id_caja_sesion <= 0:
        raise ValueError(
            "Debe indicar una sesión de caja válida."
        )

    if id_tipo_movimiento_caja <= 0:
        raise ValueError(
            "Debe seleccionar un tipo de movimiento."
        )

    if id_medio_pago <= 0:
        raise ValueError(
            "Debe seleccionar un medio de pago."
        )

    if importe <= 0:
        raise ValueError(
            "El importe debe ser mayor que cero."
        )

    concepto = concepto.strip()

    if not concepto:
        raise ValueError(
            "Debe indicar el concepto del movimiento."
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

            DECLARE @id_caja_movimiento BIGINT;
            DECLARE @usuario SYSNAME;

            SET @usuario = SUSER_SNAME();

            EXEC pos.RegistrarMovimientoCaja
                @id_caja_sesion = ?,
                @id_tipo_movimiento_caja = ?,
                @id_medio_pago = ?,
                @importe = ?,
                @concepto = ?,
                @observaciones = ?,
                @usuario = @usuario,

                @id_caja_movimiento =
                    @id_caja_movimiento OUTPUT;
            """,
            (
                id_caja_sesion,
                id_tipo_movimiento_caja,
                id_medio_pago,
                importe,
                concepto,
                observaciones,
            ),
        )

        resultado = _obtener_resultado_esperado(
            cursor,
            {
                "id_caja_movimiento",
                "id_caja_sesion",
                "fecha_hora",
                "tipo_codigo",
                "tipo_movimiento",
                "factor",
                "medio_codigo",
                "medio_pago",
                "importe",
                "concepto",
                "saldo_anterior",
                "saldo_resultante",
                "estado",
            },
        )

        if resultado is None:
            raise RuntimeError(
                "SQL Server no devolvió el resultado "
                "del movimiento de caja."
            )

        conexion.commit()

        return resultado

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

def anular_movimiento_caja(
    *,
    id_caja_movimiento: int,
    motivo: str,
) -> dict[str, Any]:
    if id_caja_movimiento <= 0:
        raise ValueError(
            "Debe seleccionar un movimiento válido."
        )

    motivo = motivo.strip()

    if not motivo:
        raise ValueError(
            "Debe indicar el motivo de la anulación."
        )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SET NOCOUNT ON;

            DECLARE @usuario SYSNAME;

            SET @usuario = SUSER_SNAME();

            EXEC pos.AnularMovimientoCaja
                @id_caja_movimiento = ?,
                @motivo = ?,
                @usuario = @usuario;
            """,
            (
                id_caja_movimiento,
                motivo,
            ),
        )

        resultado = _obtener_resultado_esperado(
            cursor,
            {
                "id_caja_movimiento",
                "id_caja_sesion",
                "estado",
                "fecha_anulacion",
                "usuario_anulacion",
                "motivo_anulacion",
            },
        )

        if resultado is None:
            raise RuntimeError(
                "SQL Server no devolvió el resultado "
                "de la anulación del movimiento."
            )

        conexion.commit()

        return resultado

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

def obtener_datos_cierre_caja(
    id_caja_sesion: int,
) -> dict[str, Any]:
    if id_caja_sesion <= 0:
        raise ValueError(
            "Debe indicar una sesión de caja válida."
        )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        # =====================================================
        # Cabecera de la sesión
        # =====================================================

        fila_sesion = cursor.execute(
            """
            SELECT
                cs.id_caja_sesion,
                cs.id_caja,
                c.descripcion AS caja_descripcion,
                cs.fecha_apertura,
                cs.usuario_apertura,
                cs.saldo_inicial,
                cs.fecha_cierre
            FROM pos.CajaSesion cs

            INNER JOIN pos.Caja c
                ON c.id_caja = cs.id_caja

            WHERE cs.id_caja_sesion = ?;
            """,
            id_caja_sesion,
        ).fetchone()

        if fila_sesion is None:
            raise ValueError(
                "La sesión de caja indicada no existe."
            )

        sesion = _fila_a_diccionario(
            cursor,
            fila_sesion,
        )

        if sesion.get("fecha_cierre") is not None:
            raise ValueError(
                "La sesión de caja ya se encuentra cerrada."
            )

        # =====================================================
        # Medios que deben conciliarse
        #
        # Misma lógica utilizada por pos.CerrarCaja:
        #   saldo inicial
        # + cobros confirmados
        # + movimientos de caja confirmados * factor
        # =====================================================

        filas = cursor.execute(
            """
            DECLARE @id_medio_efectivo TINYINT;

            SELECT
                @id_medio_efectivo =
                    mp.id_medio_pago
            FROM pos.MedioPago mp
            WHERE mp.codigo = 'EFECTIVO';


            IF @id_medio_efectivo IS NULL
            BEGIN
                THROW 50208,
                    'No existe el medio de pago EFECTIVO.',
                    1;
            END;


            WITH Medios AS
            (
                SELECT
                    @id_medio_efectivo
                        AS id_medio_pago

                UNION

                SELECT
                    cmp.id_medio_pago

                FROM pos.Cobro c

                INNER JOIN pos.CobroMedioPago cmp
                    ON cmp.id_cobro =
                       c.id_cobro

                WHERE c.id_caja_sesion = ?
                  AND c.estado = 'CONFIRMADO'

                UNION

                SELECT
                    cm.id_medio_pago

                FROM pos.CajaMovimiento cm

                WHERE cm.id_caja_sesion = ?
                  AND cm.estado = 'CONFIRMADO'
            )

            SELECT
                mp.id_medio_pago,
                mp.codigo,
                mp.descripcion,

                CONVERT(
                    DECIMAL(18,2),

                    CASE
                        WHEN mp.id_medio_pago =
                             @id_medio_efectivo
                        THEN cs.saldo_inicial
                        ELSE 0
                    END
                ) AS saldo_inicial,

                CONVERT(
                    DECIMAL(18,2),
                    ISNULL(cobros.importe, 0)
                ) AS cobros,

                CONVERT(
                    DECIMAL(18,2),
                    ISNULL(movimientos.importe, 0)
                ) AS movimientos_caja,

                CONVERT(
                    DECIMAL(18,2),

                    CASE
                        WHEN mp.id_medio_pago =
                             @id_medio_efectivo
                        THEN cs.saldo_inicial
                        ELSE 0
                    END

                    + ISNULL(cobros.importe, 0)
                    + ISNULL(movimientos.importe, 0)
                ) AS importe_sistema

            FROM Medios m

            INNER JOIN pos.MedioPago mp
                ON mp.id_medio_pago =
                   m.id_medio_pago

            INNER JOIN pos.CajaSesion cs
                ON cs.id_caja_sesion = ?

            OUTER APPLY
            (
                SELECT
                    SUM(cmp.importe) AS importe

                FROM pos.Cobro c

                INNER JOIN pos.CobroMedioPago cmp
                    ON cmp.id_cobro =
                       c.id_cobro

                WHERE c.id_caja_sesion =
                      cs.id_caja_sesion

                  AND c.estado = 'CONFIRMADO'

                  AND cmp.id_medio_pago =
                      mp.id_medio_pago
            ) cobros

            OUTER APPLY
            (
                SELECT
                    SUM(
                        cm.importe
                        * tmc.factor
                    ) AS importe

                FROM pos.CajaMovimiento cm

                INNER JOIN pos.TipoMovimientoCaja tmc
                    ON tmc.id_tipo_movimiento_caja =
                       cm.id_tipo_movimiento_caja

                WHERE cm.id_caja_sesion =
                      cs.id_caja_sesion

                  AND cm.estado = 'CONFIRMADO'

                  AND cm.id_medio_pago =
                      mp.id_medio_pago
            ) movimientos

            ORDER BY
                mp.id_medio_pago;
            """,
            (
                id_caja_sesion,
                id_caja_sesion,
                id_caja_sesion,
            ),
        ).fetchall()

        columnas = [
            descripcion[0].lower()
            for descripcion in cursor.description
        ]

        medios = [
            dict(zip(columnas, fila))
            for fila in filas
        ]

        return {
            "sesion": sesion,
            "medios": medios,
        }

    finally:
        conexion.close()

def cerrar_caja(
    *,
    id_caja_sesion: int,
    declaraciones: list[dict[str, Any]],
    permitir_diferencia: bool = False,
    observaciones: str | None = None,
) -> dict[str, Any]:
    if id_caja_sesion <= 0:
        raise ValueError(
            "Debe indicar una sesión de caja válida."
        )

    if not declaraciones:
        raise ValueError(
            "Debe informar los importes declarados."
        )

    declaraciones_json = []

    for declaracion in declaraciones:
        id_medio_pago = int(
            declaracion["id_medio_pago"]
        )

        importe = Decimal(
            str(
                declaracion[
                    "importe_declarado"
                ]
            )
        )

        if id_medio_pago <= 0:
            raise ValueError(
                "Existe un medio de pago inválido."
            )

        if importe < 0:
            raise ValueError(
                "Los importes declarados "
                "no pueden ser negativos."
            )

        declaraciones_json.append(
            {
                "id_medio_pago":
                    id_medio_pago,

                "importe_declarado":
                    format(
                        importe,
                        ".2f",
                    ),
            }
        )

    observaciones = (
        observaciones.strip()
        if observaciones
        else None
    )

    texto_json = json.dumps(
        declaraciones_json,
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

            EXEC pos.CerrarCaja
                @id_caja_sesion = ?,
                @declaraciones_json = ?,
                @permitir_diferencia = ?,
                @observaciones = ?,
                @usuario = @usuario;
            """,
            (
                id_caja_sesion,
                texto_json,
                int(permitir_diferencia),
                observaciones,
            ),
        )

        resultado = _obtener_resultado_esperado(
            cursor,
            {
                "id_caja_sesion",
                "id_caja",
                "fecha_cierre",
                "saldo_inicial",
                "efectivo_sistema",
                "efectivo_declarado",
                "diferencia_efectivo",
                "total_sistema",
                "total_declarado",
                "diferencia_neta",
                "diferencia_absoluta",
                "estado_cierre",
                "detalle_medios_json",
            },
        )

        if resultado is None:
            raise RuntimeError(
                "SQL Server no devolvió "
                "el resultado del cierre de caja."
            )

        conexion.commit()

        detalle_json = resultado.get(
            "detalle_medios_json"
        )

        if detalle_json:
            resultado["detalle_medios"] = (
                json.loads(
                    detalle_json
                )
            )
        else:
            resultado["detalle_medios"] = []

        return resultado

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

def obtener_rendicion_caja(
    id_caja_sesion: int,
) -> dict[str, Any]:
    if id_caja_sesion <= 0:
        raise ValueError(
            "Debe indicar una sesión de caja válida."
        )

    conexion = abrir_conexion()

    try:
        cursor = conexion.cursor()

        # =====================================================
        # Cabecera del cierre
        # =====================================================

        fila = cursor.execute(
            """
            SELECT
                cs.id_caja_sesion,
                cs.id_caja,
                c.descripcion
                    AS caja_descripcion,

                cs.fecha_apertura,
                cs.usuario_apertura,
                cs.saldo_inicial,

                cs.fecha_cierre,
                cs.usuario_cierre,

                cs.efectivo_sistema,
                cs.efectivo_declarado,
                cs.diferencia,

                cs.observaciones

            FROM pos.CajaSesion cs

            INNER JOIN pos.Caja c
                ON c.id_caja =
                   cs.id_caja

            WHERE cs.id_caja_sesion = ?;
            """,
            id_caja_sesion,
        ).fetchone()

        if fila is None:
            raise ValueError(
                "La sesión de caja indicada no existe."
            )

        sesion = _fila_a_diccionario(
            cursor,
            fila,
        )

        if sesion.get("fecha_cierre") is None:
            raise ValueError(
                "La sesión de caja todavía está abierta."
            )

        # =====================================================
        # Fotografía por medio de pago
        # =====================================================

        filas = cursor.execute(
            """
            SELECT
                mp.id_medio_pago,
                mp.codigo,
                mp.descripcion,

                ccmp.importe_sistema,
                ccmp.importe_declarado,
                ccmp.diferencia

            FROM pos.CajaCierreMedioPago ccmp

            INNER JOIN pos.MedioPago mp
                ON mp.id_medio_pago =
                   ccmp.id_medio_pago

            WHERE ccmp.id_caja_sesion = ?

            ORDER BY
                mp.id_medio_pago;
            """,
            id_caja_sesion,
        ).fetchall()

        columnas = [
            descripcion[0].lower()
            for descripcion in cursor.description
        ]

        medios = [
            dict(zip(columnas, fila))
            for fila in filas
        ]

        if not medios:
            raise RuntimeError(
                "La sesión está cerrada, pero no posee "
                "detalle de cierre por medio de pago."
            )

        # =====================================================
        # Movimientos de caja que participaron del cierre
        # =====================================================

        filas = cursor.execute(
            """
            SELECT
                cm.id_caja_movimiento,
                cm.fecha_hora,

                tmc.codigo
                    AS tipo_codigo,

                tmc.descripcion
                    AS tipo_movimiento,

                tmc.factor,

                mp.codigo
                    AS medio_codigo,

                mp.descripcion
                    AS medio_pago,

                cm.importe,
                cm.concepto,
                cm.observaciones,
                cm.usuario_alta

            FROM pos.CajaMovimiento cm

            INNER JOIN pos.TipoMovimientoCaja tmc
                ON tmc.id_tipo_movimiento_caja =
                   cm.id_tipo_movimiento_caja

            INNER JOIN pos.MedioPago mp
                ON mp.id_medio_pago =
                   cm.id_medio_pago

            WHERE cm.id_caja_sesion = ?
              AND cm.estado = 'CONFIRMADO'

            ORDER BY
                cm.fecha_hora,
                cm.id_caja_movimiento;
            """,
            id_caja_sesion,
        ).fetchall()

        columnas = [
            descripcion[0].lower()
            for descripcion in cursor.description
        ]

        movimientos = [
            dict(zip(columnas, fila))
            for fila in filas
        ]

        return {
            "sesion": sesion,
            "medios": medios,
            "movimientos": movimientos,
        }

    finally:
        conexion.close()