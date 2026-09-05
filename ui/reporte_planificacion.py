from __future__ import annotations

import tkinter as tk
from datetime import date, timedelta
from decimal import Decimal
from tkinter import messagebox, ttk
from typing import Any
from ui.ventana_util import maximizar_ventana

from tkcalendar import DateEntry

from db.reporte_planificacion_repository import (
    listar_produccion_por_fecha,
)
from ui.pedido import formato_cantidad
import html
import tempfile
import webbrowser
from pathlib import Path

def numero(valor: Any) -> Decimal:
    if valor is None:
        return Decimal("0")

    return Decimal(str(valor))


def fecha_texto(valor: Any) -> str:
    if valor is None:
        return ""

    return valor.strftime("%d/%m/%Y")


class VentanaReportePlanificacion(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        navegador=None,
    ) -> None:
        super().__init__(parent)

        self.navegador = navegador

        self._filas_reporte: list[
            dict[str, Any]
        ] = []

        self._ancho_pantalla = (
            self.winfo_screenwidth()
        )

        self._alto_pantalla = (
            self.winfo_screenheight()
        )

        self.title(
            "Planificación de elaboración"
        )

        self.transient(parent)
        self.resizable(True, True)
        
        maximizar_ventana(self)
        # self._ajustar_tamano_inicial()
        self._crear_interfaz()

        self._seleccionar_semana_actual(
            actualizar=False
        )

        self._actualizar()
    def _ajustar_tamano_inicial(self) -> None:
        ancho = int(
            self._ancho_pantalla * 0.88
        )

        alto_disponible = max(
            self._alto_pantalla - 70,
            500,
        )

        alto = int(
            alto_disponible * 0.90
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
            680,
            ancho,
        )

        alto_minimo = min(
            480,
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

        # La grilla ocupa todo el espacio sobrante.
        contenedor.rowconfigure(
            2,
            weight=1,
        )

        ttk.Label(
            contenedor,
            text="Planificación de elaboración",
            font=("Segoe UI", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 8),
        )

        self._crear_filtros(contenedor)
        self._crear_grilla(contenedor)
        self._crear_pie(contenedor)

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
            row=1,
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
            padx=(0, 0),
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
            text="Semana actual",
            command=self._seleccionar_semana_actual,
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
            text="🖨 Imprimir",
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

    def _crear_grilla(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Producción programada",
            padding=8,
        )
        marco.grid(
            row=2,
            column=0,
            sticky="nsew",
            pady=(0, 8),
        )

        marco.rowconfigure(
            0,
            weight=1,
        )

        marco.columnconfigure(
            0,
            weight=1,
        )

        columnas = (
            "fecha_elaboracion",
            "producto",
            "cantidad",
        )

        self.grilla = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
        )

        self.grilla.heading(
            "fecha_elaboracion",
            text="Fecha de elaboración",
        )

        self.grilla.heading(
            "producto",
            text="Producto",
        )

        self.grilla.heading(
            "cantidad",
            text="Cantidad a elaborar",
        )

        self.grilla.column(
            "fecha_elaboracion",
            width=160,
            minwidth=120,
            anchor="center",
            stretch=False,
        )

        self.grilla.column(
            "producto",
            width=420,
            minwidth=220,
            anchor="w",
            stretch=True,
        )

        self.grilla.column(
            "cantidad",
            width=170,
            minwidth=130,
            anchor="e",
            stretch=False,
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

    def _seleccionar_semana_actual(
        self,
        *,
        actualizar: bool = True,
    ) -> None:
        hoy = date.today()

        lunes = hoy - timedelta(
            days=hoy.weekday()
        )

        domingo = lunes + timedelta(days=6)

        self.fecha_desde.set_date(lunes)
        self.fecha_hasta.set_date(domingo)

        if actualizar:
            self._actualizar()

    def _actualizar(self) -> None:
        fecha_desde = self.fecha_desde.get_date()
        fecha_hasta = self.fecha_hasta.get_date()

        if fecha_desde > fecha_hasta:
            messagebox.showwarning(
                "Planificación de elaboración",
                "La fecha desde no puede ser posterior "
                "a la fecha hasta.",
                parent=self,
            )
            return

        try:
            filas = listar_produccion_por_fecha(
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
            )

        except Exception as error:
            messagebox.showerror(
                "Planificación de elaboración",
                "No se pudo recuperar el reporte."
                f"\n\n{error}",
                parent=self,
            )
            return

        self._limpiar_grilla()

        total_elaborar = Decimal("0")

        for indice, fila in enumerate(filas):
            cantidad = numero(
                fila["cantidad_total_elaborar"]
            )

            total_elaborar += cantidad

            self.grilla.insert(
                "",
                "end",
                iid=f"produccion-{indice}",
                values=(
                    fecha_texto(
                        fila["fecha_elaboracion"]
                    ),
                    fila["descripcion_producto"],
                    formato_cantidad(cantidad),
                ),
            )

        self.estado.set(
            f"Productos programados: {len(filas)}  ·  "
            f"Cantidad total: "
            f"{formato_cantidad(total_elaborar)}"
        )

        self._filas_reporte = filas

    def _limpiar_grilla(self) -> None:
        for item in self.grilla.get_children():
            self.grilla.delete(item)
    
    def _imprimir(self) -> None:
        if not self._filas_reporte:
            messagebox.showinfo(
                "Planificación de elaboración",
                "No hay información para imprimir.",
                parent=self,
            )
            return

        fecha_desde = self.fecha_desde.get_date()
        fecha_hasta = self.fecha_hasta.get_date()

        filas_html: list[str] = []

        total_elaborar = Decimal("0")

        for fila in self._filas_reporte:
            cantidad = numero(
                fila["cantidad_total_elaborar"]
            )

            total_elaborar += cantidad

            fecha = fecha_texto(
                fila["fecha_elaboracion"]
            )

            producto = html.escape(
                str(fila["descripcion_producto"])
            )

            cantidad_texto = formato_cantidad(cantidad)

            filas_html.append(
                f"""
                <tr>
                    <td>{fecha}</td>
                    <td>{producto}</td>
                    <td class="numero">{cantidad_texto}</td>
                </tr>
                """
            )

        contenido = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="utf-8">

            <title>Planificación de elaboración</title>

            <style>
                @page {{
                    size: A4;
                    margin: 18mm;
                }}

                body {{
                    font-family: Arial, sans-serif;
                    color: #222;
                    margin: 0;
                }}

                h1 {{
                    font-size: 22px;
                    margin-bottom: 4px;
                }}

                .periodo {{
                    margin-bottom: 20px;
                    color: #555;
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}

                th,
                td {{
                    border: 1px solid #999;
                    padding: 8px;
                }}

                th {{
                    background: #eeeeee;
                    text-align: left;
                }}

                .numero {{
                    text-align: right;
                }}

                tfoot td {{
                    font-weight: bold;
                    background: #f4f4f4;
                }}

                .pie {{
                    margin-top: 14px;
                    font-size: 11px;
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
            <h1>Planificación de elaboración</h1>

            <div class="periodo">
                Período:
                {fecha_desde.strftime("%d/%m/%Y")}
                al
                {fecha_hasta.strftime("%d/%m/%Y")}
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Fecha de elaboración</th>
                        <th>Producto</th>
                        <th>Cantidad a elaborar</th>
                    </tr>
                </thead>

                <tbody>
                    {''.join(filas_html)}
                </tbody>

                <tfoot>
                    <tr>
                        <td colspan="2">
                            Cantidad total
                        </td>

                        <td class="numero">
                            {
                                formato_cantidad(
                                    total_elaborar
                                )
                            }
                        </td>
                    </tr>
                </tfoot>
            </table>

            <div class="pie">
                Reporte generado desde el Punto de Venta.
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
            / "planificacion_elaboracion.html"
        )

        archivo.write_text(
            contenido,
            encoding="utf-8",
        )

        webbrowser.open(
            archivo.as_uri()
        )

    def _crear_pie(
        self,
        parent: ttk.Frame,
    ) -> None:
        pie = ttk.Frame(parent)
        pie.grid(
            row=3,
            column=0,
            sticky="ew",
        )

        pie.columnconfigure(
            0,
            weight=1,
        )

        self.estado = tk.StringVar(
            value=""
        )

        ttk.Label(
            pie,
            textvariable=self.estado,
            font=("Segoe UI", 10, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )