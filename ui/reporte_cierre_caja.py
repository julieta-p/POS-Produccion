from __future__ import annotations

import html
import tempfile
import webbrowser

from decimal import Decimal
from pathlib import Path
from typing import Any

from db.caja_repository import (
    obtener_rendicion_caja,
)


def numero(valor: Any) -> Decimal:
    if valor is None:
        return Decimal("0")

    return Decimal(str(valor))


def formato_moneda(valor: Any) -> str:
    valor_decimal = numero(valor)

    texto = f"{valor_decimal:,.2f}"

    texto = (
        texto
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return f"$ {texto}"


def fecha_hora_texto(valor: Any) -> str:
    if valor is None:
        return ""

    try:
        return valor.strftime(
            "%d/%m/%Y %H:%M:%S"
        )

    except AttributeError:
        return str(valor)


def emitir_rendicion_caja(
    id_caja_sesion: int,
) -> None:
    datos = obtener_rendicion_caja(
        id_caja_sesion
    )

    sesion = datos["sesion"]
    medios = datos["medios"]
    movimientos = datos["movimientos"]

    # =========================================================
    # Totales por medio
    # =========================================================

    total_sistema = sum(
        (
            numero(
                medio["importe_sistema"]
            )
            for medio in medios
        ),
        Decimal("0"),
    )

    total_declarado = sum(
        (
            numero(
                medio["importe_declarado"]
            )
            for medio in medios
        ),
        Decimal("0"),
    )

    total_diferencia = (
        total_declarado
        - total_sistema
    )

    diferencia_absoluta = sum(
        (
            abs(
                numero(
                    medio["diferencia"]
                )
            )
            for medio in medios
        ),
        Decimal("0"),
    )

    estado_cierre = (
        "CUADRADA"
        if diferencia_absoluta
        < Decimal("0.01")
        else "CON DIFERENCIA"
    )

    # =========================================================
    # Filas por medio
    # =========================================================

    filas_medios: list[str] = []

    for medio in medios:
        filas_medios.append(
            f"""
            <tr>
                <td>
                    {html.escape(str(medio["descripcion"]))}
                </td>

                <td class="numero">
                    {
                        formato_moneda(
                            medio["importe_sistema"]
                        )
                    }
                </td>

                <td class="numero">
                    {
                        formato_moneda(
                            medio["importe_declarado"]
                        )
                    }
                </td>

                <td class="numero">
                    {
                        formato_moneda(
                            medio["diferencia"]
                        )
                    }
                </td>
            </tr>
            """
        )

    # =========================================================
    # Movimientos de caja chica
    # =========================================================

    filas_movimientos: list[str] = []

    for movimiento in movimientos:
        importe = numero(
            movimiento["importe"]
        )

        factor = int(
            movimiento["factor"]
        )

        importe_firmado = (
            importe
            if factor > 0
            else -importe
        )

        filas_movimientos.append(
            f"""
            <tr>
                <td>
                    {
                        fecha_hora_texto(
                            movimiento["fecha_hora"]
                        )
                    }
                </td>

                <td>
                    {
                        html.escape(
                            str(
                                movimiento[
                                    "tipo_movimiento"
                                ]
                            )
                        )
                    }
                </td>

                <td>
                    {
                        html.escape(
                            str(
                                movimiento[
                                    "concepto"
                                ]
                            )
                        )
                    }
                </td>

                <td>
                    {
                        html.escape(
                            str(
                                movimiento[
                                    "medio_pago"
                                ]
                            )
                        )
                    }
                </td>

                <td class="numero">
                    {
                        formato_moneda(
                            importe_firmado
                        )
                    }
                </td>
            </tr>
            """
        )

    if not filas_movimientos:
        filas_movimientos.append(
            """
            <tr>
                <td colspan="5"
                    class="sin-datos">
                    Sin movimientos de caja chica
                </td>
            </tr>
            """
        )

    observaciones = (
        sesion.get("observaciones")
        or "Sin observaciones"
    )

    contenido = f"""
    <!DOCTYPE html>
    <html lang="es">

    <head>
        <meta charset="utf-8">

        <title>
            Rendición de caja
            - Sesión {sesion["id_caja_sesion"]}
        </title>

        <style>
            @page {{
                size: A4;
                margin: 16mm;
            }}

            body {{
                font-family: Arial, sans-serif;
                color: #222;
                margin: 0;
                font-size: 13px;
            }}

            h1 {{
                font-size: 22px;
                margin: 0 0 4px 0;
            }}

            h2 {{
                font-size: 15px;
                margin-top: 22px;
                margin-bottom: 8px;
            }}

            .subtitulo {{
                color: #555;
                margin-bottom: 18px;
            }}

            .datos {{
                width: 100%;
                margin-bottom: 18px;
                border-collapse: collapse;
            }}

            .datos td {{
                padding: 3px 8px 3px 0;
                border: 0;
            }}

            table.detalle {{
                width: 100%;
                border-collapse: collapse;
            }}

            table.detalle th,
            table.detalle td {{
                border: 1px solid #999;
                padding: 7px;
            }}

            table.detalle th {{
                background: #eeeeee;
                text-align: left;
            }}

            .numero {{
                text-align: right;
                white-space: nowrap;
            }}

            tfoot td {{
                font-weight: bold;
                background: #f4f4f4;
            }}

            .estado {{
                margin-top: 16px;
                font-size: 14px;
                font-weight: bold;
            }}

            .observaciones {{
                margin-top: 10px;
                padding: 9px;
                border: 1px solid #bbb;
                min-height: 35px;
            }}

            .sin-datos {{
                text-align: center;
                color: #666;
            }}

            .firmas {{
                margin-top: 50px;
                width: 100%;
            }}

            .firma {{
                display: inline-block;
                width: 45%;
                text-align: center;
                vertical-align: top;
            }}

            .linea-firma {{
                border-top: 1px solid #555;
                margin: 0 auto 5px auto;
                width: 80%;
            }}

            .pie {{
                margin-top: 25px;
                font-size: 10px;
                color: #666;
            }}

            @media print {{
                .no-imprimir {{
                    display: none;
                }}
            }}
        </style>
    </head>

    <body>

        <h1>Rendición de caja</h1>

        <div class="subtitulo">
            Fábrica Doña Elina · Punto de Venta
        </div>


        <table class="datos">
            <tr>
                <td>
                    <strong>Caja:</strong>
                    {
                        html.escape(
                            str(
                                sesion[
                                    "caja_descripcion"
                                ]
                            )
                        )
                    }
                </td>

                <td>
                    <strong>Sesión:</strong>
                    {sesion["id_caja_sesion"]}
                </td>
            </tr>

            <tr>
                <td>
                    <strong>Apertura:</strong>
                    {
                        fecha_hora_texto(
                            sesion["fecha_apertura"]
                        )
                    }
                </td>

                <td>
                    <strong>Cierre:</strong>
                    {
                        fecha_hora_texto(
                            sesion["fecha_cierre"]
                        )
                    }
                </td>
            </tr>

            <tr>
                <td>
                    <strong>Usuario apertura:</strong>
                    {
                        html.escape(
                            str(
                                sesion[
                                    "usuario_apertura"
                                ]
                            )
                        )
                    }
                </td>

                <td>
                    <strong>Usuario cierre:</strong>
                    {
                        html.escape(
                            str(
                                sesion[
                                    "usuario_cierre"
                                ]
                            )
                        )
                    }
                </td>
            </tr>

            <tr>
                <td colspan="2">
                    <strong>Saldo inicial:</strong>
                    {
                        formato_moneda(
                            sesion["saldo_inicial"]
                        )
                    }
                </td>
            </tr>
        </table>


        <h2>Conciliación por medio de pago</h2>

        <table class="detalle">
            <thead>
                <tr>
                    <th>Medio</th>
                    <th class="numero">
                        Sistema
                    </th>
                    <th class="numero">
                        Declarado
                    </th>
                    <th class="numero">
                        Diferencia
                    </th>
                </tr>
            </thead>

            <tbody>
                {''.join(filas_medios)}
            </tbody>

            <tfoot>
                <tr>
                    <td>TOTAL</td>

                    <td class="numero">
                        {
                            formato_moneda(
                                total_sistema
                            )
                        }
                    </td>

                    <td class="numero">
                        {
                            formato_moneda(
                                total_declarado
                            )
                        }
                    </td>

                    <td class="numero">
                        {
                            formato_moneda(
                                total_diferencia
                            )
                        }
                    </td>
                </tr>
            </tfoot>
        </table>


        <h2>Movimientos de caja chica</h2>

        <table class="detalle">
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>Tipo</th>
                    <th>Concepto</th>
                    <th>Medio</th>
                    <th class="numero">
                        Importe
                    </th>
                </tr>
            </thead>

            <tbody>
                {''.join(filas_movimientos)}
            </tbody>
        </table>


        <div class="estado">
            Estado del cierre:
            {estado_cierre}
        </div>


        <div>
            <strong>Observaciones</strong>
        </div>

        <div class="observaciones">
            {
                html.escape(
                    str(observaciones)
                )
            }
        </div>


        <div class="firmas">
            <div class="firma">
                <div class="linea-firma"></div>
                Entrega
            </div>

            <div class="firma">
                <div class="linea-firma"></div>
                Recibe
            </div>
        </div>


        <div class="pie">
            Rendición generada desde el Punto de Venta.
            Sesión {sesion["id_caja_sesion"]}.
        </div>


        <script>
            window.addEventListener(
                "load",
                function () {{
                    window.print();
                }}
            );
        </script>

    </body>
    </html>
    """

    carpeta_temporal = Path(
        tempfile.gettempdir()
    )

    archivo = (
        carpeta_temporal
        / (
            "rendicion_caja_"
            f"{id_caja_sesion}.html"
        )
    )

    archivo.write_text(
        contenido,
        encoding="utf-8",
    )

    webbrowser.open(
        archivo.as_uri()
    )