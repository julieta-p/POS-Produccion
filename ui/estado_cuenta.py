from __future__ import annotations

import html
import tempfile
import tkinter as tk
import webbrowser
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any
from ui.ventana_util import maximizar_ventana

from tkcalendar import DateEntry

from db.estado_cuenta_repository import (
    listar_estado_cuenta,
    obtener_resumen_cliente,
)
from ui.pedido import formato_decimal


def numero(valor: Any) -> Decimal:
    if valor is None:
        return Decimal("0")

    return Decimal(str(valor))


def fecha_hora_texto(valor: Any) -> str:
    if valor is None:
        return ""

    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")

    return str(valor)


def importe_texto(valor: Any) -> str:
    return (
        "$"
        + formato_decimal(
            numero(valor),
            decimales=2,
        )
    )


class VentanaEstadoCuenta(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        cliente: dict[str, Any],
        navegador=None,
    ) -> None:
        super().__init__(parent)

        self.navegador = (
            navegador
            or getattr(parent, "navegador", None)
        )

        self._id_cliente = int(
            cliente["id_cliente"]
        )

        self._nombre_cliente = str(
            cliente["nombre"]
        )

        self._resumen: dict[str, Any] = {}
        self._movimientos: list[
            dict[str, Any]
        ] = []

        self._ancho_pantalla = (
            self.winfo_screenwidth()
        )

        self._alto_pantalla = (
            self.winfo_screenheight()
        )

        self._pantalla_compacta = (
            self._ancho_pantalla < 1100
            or self._alto_pantalla < 700
        )

        self.title(
            f"Estado de cuenta - "
            f"{self._nombre_cliente}"
        )

        self.transient(parent)
        self.resizable(True, True)

        maximizar_ventana(self)
        # self._ajustar_tamano_inicial()
        self._crear_interfaz()
        self._seleccionar_periodo_inicial()
        self._actualizar()

    def _ajustar_tamano_inicial(self) -> None:
        ancho = int(
            self._ancho_pantalla * 0.94
        )

        alto_disponible = max(
            self._alto_pantalla - 70,
            500,
        )

        alto = int(
            alto_disponible * 0.94
        )

        ancho = min(
            ancho,
            self._ancho_pantalla - 20,
        )

        alto = min(
            alto,
            self._alto_pantalla - 50,
        )

        ancho_minimo = min(
            820,
            ancho,
        )

        alto_minimo = min(
            520,
            alto,
        )

        self.minsize(
            ancho_minimo,
            alto_minimo,
        )

        x = max(
            (
                self._ancho_pantalla
                - ancho
            ) // 2,
            0,
        )

        y = max(
            (
                self._alto_pantalla
                - alto
            ) // 2,
            0,
        )

        self.geometry(
            f"{ancho}x{alto}+{x}+{y}"
        )

    def _crear_interfaz(self) -> None:
        contenedor = ttk.Frame(
            self,
            padding=(12, 8),
        )
        contenedor.pack(
            fill="both",
            expand=True,
        )

        contenedor.columnconfigure(
            0,
            weight=1,
        )

        # La grilla ocupa todo el alto disponible.
        contenedor.rowconfigure(
            4,
            weight=1,
        )

        ttk.Label(
            contenedor,
            text="Estado de cuenta",
            font=("Segoe UI", 20, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.texto_cliente = tk.StringVar(
            value=self._nombre_cliente
        )

        ttk.Label(
            contenedor,
            textvariable=self.texto_cliente,
            font=("Segoe UI", 13, "bold"),
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(2, 8),
        )

        self._crear_filtros(contenedor)
        self._crear_resumen(contenedor)
        self._crear_grilla(contenedor)
    

    def _crear_filtros(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Período",
            padding=10,
        )
        marco.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        marco.columnconfigure(
            0,
            weight=1,
        )

        campos = ttk.Frame(marco)
        campos.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        campos.columnconfigure(
            0,
            weight=0,
        )

        campos.columnconfigure(
            1,
            weight=0,
        )

        campos.columnconfigure(
            2,
            weight=1,
        )

        ttk.Label(
            campos,
            text="Desde",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.fecha_desde = DateEntry(
            campos,
            date_pattern="dd/mm/yyyy",
            locale="es_AR",
            firstweekday="monday",
            width=12,
        )
        self.fecha_desde.grid(
            row=1,
            column=0,
            padx=(0, 8),
            sticky="w",
        )

        self.fecha_desde.bind(
            "<<DateEntrySelected>>",
            self._sincronizar_fecha_hasta,
        )

        ttk.Label(
            campos,
            text="Hasta",
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )

        self.fecha_hasta = DateEntry(
            campos,
            date_pattern="dd/mm/yyyy",
            locale="es_AR",
            firstweekday="monday",
            width=12,
        )
        self.fecha_hasta.grid(
            row=1,
            column=1,
            padx=(0, 8),
            sticky="w",
        )

        acciones = ttk.Frame(marco)
        acciones.grid(
            row=1,
            column=0,
            sticky="e",
            pady=(8, 0),
        )

        ttk.Button(
            acciones,
            text="Todo el historial",
            command=self._mostrar_todo,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            acciones,
            text="Actualizar",
            command=self._actualizar,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            acciones,
            text="Imprimir",
            command=self._imprimir,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            acciones,
            text="Cerrar",
            command=self.destroy,
        ).pack(
            side="left",
        )
    def _crear_resumen(
        self,
        parent: ttk.Frame,
    ) -> None:
        self.marco_resumen = ttk.LabelFrame(
            parent,
            text="Resumen actual",
            padding=10,
        )
        self.marco_resumen.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        self.texto_total_ventas = tk.StringVar(
            value="Ventas: $0,00"
        )

        self.texto_total_cobros = tk.StringVar(
            value="Cobros: $0,00"
        )

        self.texto_saldo = tk.StringVar(
            value="Saldo: $0,00"
        )

        textos = (
            self.texto_total_ventas,
            self.texto_total_cobros,
            self.texto_saldo,
        )

        for columna in range(3):
            self.marco_resumen.columnconfigure(
                columna,
                weight=1,
                uniform="resumen",
            )

        for columna, variable in enumerate(textos):
            ttk.Label(
                self.marco_resumen,
                textvariable=variable,
                font=(
                    "Segoe UI",
                    12 if columna == 2 else 11,
                    "bold",
                ),
            ).grid(
                row=0,
                column=columna,
                padx=(
                    (0, 8)
                    if columna < 2
                    else (0, 0)
                ),
                sticky="w",
            )
    def _crear_grilla(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Movimientos",
            padding=8,
        )
        marco.grid(
            row=4,
            column=0,
            sticky="nsew",
            pady=(0, 10),
        )

        parent.rowconfigure(
            4,
            weight=1,
        )

        marco.columnconfigure(
            0,
            weight=1,
        )
        marco.rowconfigure(
            0,
            weight=1,
        )

        columnas = (
            "numero",
            "fecha",
            "tipo",
            "referencia",
            "detalle",
            "debe",
            "haber",
            "saldo",
        )

        self.grilla = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
        )

        titulos = {
            "numero": "N.º",
            "fecha": "Fecha",
            "tipo": "Movimiento",
            "referencia": "Referencia",
            "detalle": "Detalle",
            "debe": "Debe",
            "haber": "Haber",
            "saldo": "Saldo",
        }

        anchos = {
            "numero": 55,
            "fecha": 145,
            "tipo": 105,
            "referencia": 95,
            "detalle": 320,
            "debe": 125,
            "haber": 125,
            "saldo": 135,
        }

        for columna in columnas:
            self.grilla.heading(
                columna,
                text=titulos[columna],
            )

            if columna == "detalle":
                minwidth = 180
                stretch = True

            elif columna in (
                "debe",
                "haber",
                "saldo",
            ):
                minwidth = 90
                stretch = False

            else:
                minwidth = 70
                stretch = False

            self.grilla.column(
                columna,
                width=anchos[columna],
                minwidth=minwidth,
                anchor=(
                    "w"
                    if columna == "detalle"
                    else "e"
                    if columna in (
                        "debe",
                        "haber",
                        "saldo",
                    )
                    else "center"
                ),
                stretch=stretch,
            )

        barra_vertical = ttk.Scrollbar(
            marco,
            orient="vertical",
            command=self.grilla.yview,
        )

        barra_horizontal = ttk.Scrollbar(
            marco,
            orient="horizontal",
            command=self.grilla.xview,
        )

        self.grilla.configure(
            yscrollcommand=barra_vertical.set,
            xscrollcommand=barra_horizontal.set,
        )

        self.grilla.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        barra_vertical.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        barra_horizontal.grid(
            row=1,
            column=0,
            sticky="ew",
        )

    
    def _sincronizar_fecha_hasta(
        self,
        _evento=None,
    ) -> None:
        self.fecha_hasta.set_date(
            self.fecha_desde.get_date()
        )

    def _seleccionar_periodo_inicial(
        self,
    ) -> None:
        hoy = date.today()

        self.fecha_desde.set_date(
            date(hoy.year, 1, 1)
        )

        self.fecha_hasta.set_date(hoy)

    def _mostrar_todo(self) -> None:
        self.fecha_desde.set_date(
            date(2000, 1, 1)
        )
        self.fecha_hasta.set_date(
            date.today()
        )

        self._actualizar()

    def _actualizar(self) -> None:
        fecha_desde = self.fecha_desde.get_date()
        fecha_hasta = self.fecha_hasta.get_date()

        if fecha_desde > fecha_hasta:
            messagebox.showwarning(
                "Estado de cuenta",
                "La fecha desde no puede ser "
                "posterior a la fecha hasta.",
                parent=self,
            )
            return

        try:
            resumen = obtener_resumen_cliente(
                self._id_cliente
            )

            movimientos = listar_estado_cuenta(
                id_cliente=self._id_cliente,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
            )

        except Exception as error:
            messagebox.showerror(
                "Estado de cuenta",
                "No se pudo obtener el estado "
                "de cuenta."
                f"\n\n{error}",
                parent=self,
            )
            return

        self._resumen = resumen or {
            "nombre": self._nombre_cliente,
            "total_ventas": Decimal("0"),
            "total_cobros": Decimal("0"),
            "saldo": Decimal("0"),
        }

        self._movimientos = movimientos

        self.texto_total_ventas.set(
            "Ventas: "
            + importe_texto(
                self._resumen["total_ventas"]
            )
        )

        self.texto_total_cobros.set(
            "Cobros: "
            + importe_texto(
                self._resumen["total_cobros"]
            )
        )

        self.texto_saldo.set(
            "Saldo: "
            + importe_texto(
                self._resumen["saldo"]
            )
        )

        for item in self.grilla.get_children():
            self.grilla.delete(item)

        for indice, movimiento in enumerate(
            movimientos
        ):
            self.grilla.insert(
                "",
                "end",
                iid=f"movimiento-{indice}",
                values=(
                    movimiento["nro_movimiento"],
                    fecha_hora_texto(
                        movimiento["fecha_hora"]
                    ),
                    movimiento["tipo_movimiento"],
                    movimiento["id_referencia"],
                    movimiento["detalle"] or "",
                    importe_texto(
                        movimiento["debe"]
                    ),
                    importe_texto(
                        movimiento["haber"]
                    ),
                    importe_texto(
                        movimiento["saldo_acumulado"]
                    ),
                ),
            )

    def _imprimir(self) -> None:
        if not self._movimientos:
            messagebox.showinfo(
                "Estado de cuenta",
                "No hay movimientos para imprimir.",
                parent=self,
            )
            return

        fecha_desde = (
            self.fecha_desde.get_date()
            .strftime("%d/%m/%Y")
        )

        fecha_hasta = (
            self.fecha_hasta.get_date()
            .strftime("%d/%m/%Y")
        )

        filas_html = []

        for movimiento in self._movimientos:
            filas_html.append(
                "<tr>"
                f"<td>{html.escape(fecha_hora_texto(movimiento['fecha_hora']))}</td>"
                f"<td>{html.escape(str(movimiento['tipo_movimiento']))}</td>"
                f"<td>{html.escape(str(movimiento['id_referencia']))}</td>"
                f"<td>{html.escape(str(movimiento['detalle'] or ''))}</td>"
                f"<td class='numero'>{html.escape(importe_texto(movimiento['debe']))}</td>"
                f"<td class='numero'>{html.escape(importe_texto(movimiento['haber']))}</td>"
                f"<td class='numero'>{html.escape(importe_texto(movimiento['saldo_acumulado']))}</td>"
                "</tr>"
            )

        documento = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="utf-8">
            <title>Estado de cuenta</title>

            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 30px;
                    color: #222;
                }}

                h1 {{
                    margin-bottom: 4px;
                }}

                h2 {{
                    margin-top: 0;
                    font-size: 18px;
                }}

                .resumen {{
                    margin: 18px 0;
                    padding: 12px;
                    border: 1px solid #aaa;
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 12px;
                }}

                th, td {{
                    border: 1px solid #aaa;
                    padding: 6px;
                }}

                th {{
                    background: #eee;
                }}

                .numero {{
                    text-align: right;
                    white-space: nowrap;
                }}

                @media print {{
                    button {{
                        display: none;
                    }}
                }}
            </style>
        </head>

        <body onload="window.print()">
            <h1>Estado de cuenta</h1>
            <h2>{html.escape(self._nombre_cliente)}</h2>

            <p>
                Período: {fecha_desde}
                al {fecha_hasta}
            </p>

            <div class="resumen">
                <strong>Ventas:</strong>
                {importe_texto(self._resumen['total_ventas'])}
                &nbsp;&nbsp;

                <strong>Cobros:</strong>
                {importe_texto(self._resumen['total_cobros'])}
                &nbsp;&nbsp;

                <strong>Saldo actual:</strong>
                {importe_texto(self._resumen['saldo'])}
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Movimiento</th>
                        <th>Referencia</th>
                        <th>Detalle</th>
                        <th>Debe</th>
                        <th>Haber</th>
                        <th>Saldo</th>
                    </tr>
                </thead>

                <tbody>
                    {''.join(filas_html)}
                </tbody>
            </table>
        </body>
        </html>
        """

        archivo = (
            Path(tempfile.gettempdir())
            / (
                "estado_cuenta_"
                f"{self._id_cliente}.html"
            )
        )

        archivo.write_text(
            documento,
            encoding="utf-8",
        )

        webbrowser.open(
            archivo.resolve().as_uri()
        )