from __future__ import annotations

import html
import tempfile
import tkinter as tk
import webbrowser

from datetime import date
from decimal import Decimal
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from db.reporte_precios_repository import (
    listar_precios,
)

from ui.pedido import formato_decimal
from ui.ventana_util import maximizar_ventana


def numero(valor: Any) -> Decimal:
    if valor is None:
        return Decimal("0")

    return Decimal(str(valor))


class VentanaReportePrecios(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        navegador=None,
    ) -> None:
        super().__init__(parent)

        self.navegador = navegador
        self._filas: list[dict[str, Any]] = []

        self.title("Listado de precios")
        self.resizable(True, True)

        maximizar_ventana(self)

        self._crear_interfaz()
        self._actualizar()

    # =====================================================
    # Interfaz
    # =====================================================

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

        contenedor.rowconfigure(
            2,
            weight=1,
        )

        ttk.Label(
            contenedor,
            text="Listado de precios",
            font=(
                "Segoe UI",
                18,
                "bold",
            ),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 8),
        )

        self._crear_filtros(
            contenedor
        )

        self._crear_grilla(
            contenedor
        )

        self._crear_pie(
            contenedor
        )

    # =====================================================
    # Filtros
    # =====================================================

    def _crear_filtros(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Consulta",
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

        ttk.Label(
            marco,
            text="Buscar producto",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.txt_buscar = ttk.Entry(
            marco
        )
        self.txt_buscar.grid(
            row=1,
            column=0,
            padx=(0, 12),
            sticky="ew",
        )

        self.txt_buscar.bind(
            "<Return>",
            lambda _evento:
                self._actualizar(),
        )

        acciones = ttk.Frame(
            marco
        )
        acciones.grid(
            row=2,
            column=0,
            sticky="e",
            pady=(8, 0),
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

    # =====================================================
    # Grilla
    # =====================================================

    def _crear_grilla(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Productos",
            padding=8,
        )
        marco.grid(
            row=2,
            column=0,
            sticky="nsew",
            pady=(0, 8),
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
            "id",
            "producto",
            "mayor",
            "menor",
        )

        self.grilla = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
        )

        self.grilla.heading(
            "id",
            text="ID",
        )

        self.grilla.heading(
            "producto",
            text="Producto",
        )

        self.grilla.heading(
            "mayor",
            text="Precio mayor",
        )

        self.grilla.heading(
            "menor",
            text="Precio menor",
        )

        self.grilla.column(
            "id",
            width=70,
            minwidth=60,
            anchor="center",
            stretch=False,
        )

        self.grilla.column(
            "producto",
            width=500,
            minwidth=250,
            anchor="w",
            stretch=True,
        )

        self.grilla.column(
            "mayor",
            width=150,
            minwidth=120,
            anchor="e",
            stretch=False,
        )

        self.grilla.column(
            "menor",
            width=150,
            minwidth=120,
            anchor="e",
            stretch=False,
        )

        barra_vertical = ttk.Scrollbar(
            marco,
            orient="vertical",
            command=self.grilla.yview,
        )

        self.grilla.configure(
            yscrollcommand=
                barra_vertical.set
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

    # =====================================================
    # Pie
    # =====================================================

    def _crear_pie(
        self,
        parent: ttk.Frame,
    ) -> None:
        self.estado = tk.StringVar(
            value=""
        )

        ttk.Label(
            parent,
            textvariable=self.estado,
            font=(
                "Segoe UI",
                10,
                "bold",
            ),
        ).grid(
            row=3,
            column=0,
            sticky="w",
        )

    # =====================================================
    # Consulta
    # =====================================================

    def _actualizar(self) -> None:
        buscar = (
            self.txt_buscar
            .get()
            .strip()
            or None
        )

        try:
            filas = listar_precios(
                buscar=buscar
            )

        except Exception as error:
            messagebox.showerror(
                "Listado de precios",
                (
                    "No se pudieron recuperar "
                    "los precios."
                    f"\n\n{error}"
                ),
                parent=self,
            )
            return

        self._filas = filas

        for item in (
            self.grilla.get_children()
        ):
            self.grilla.delete(
                item
            )

        sin_precio = 0

        for indice, fila in enumerate(
            filas
        ):
            mayor = numero(
                fila["precio_mayor"]
            )

            menor = numero(
                fila["precio_menor"]
            )

            if mayor <= 0 or menor <= 0:
                sin_precio += 1

            self.grilla.insert(
                "",
                "end",
                iid=f"producto-{indice}",
                values=(
                    fila["id_producto"],
                    fila["descripcion"],
                    "$ "
                    + formato_decimal(
                        mayor
                    ),
                    "$ "
                    + formato_decimal(
                        menor
                    ),
                ),
            )

        self.estado.set(
            f"Productos: {len(filas)}"
            "  ·  "
            f"Con precio incompleto: "
            f"{sin_precio}"
        )

    # =====================================================
    # Impresión
    # =====================================================

    def _imprimir(self) -> None:
        if not self._filas:
            messagebox.showinfo(
                "Listado de precios",
                (
                    "No hay información "
                    "para imprimir."
                ),
                parent=self,
            )
            return

        filas_html: list[str] = []

        for fila in self._filas:
            mayor = numero(
                fila["precio_mayor"]
            )

            menor = numero(
                fila["precio_menor"]
            )

            filas_html.append(
                f"""
                <tr>
                    <td>
                        {
                            html.escape(
                                str(
                                    fila[
                                        "descripcion"
                                    ]
                                )
                            )
                        }
                    </td>

                    <td class="numero">
                        $
                        {
                            formato_decimal(
                                mayor
                            )
                        }
                    </td>

                    <td class="numero">
                        $
                        {
                            formato_decimal(
                                menor
                            )
                        }
                    </td>
                </tr>
                """
            )

        hoy = date.today()

        contenido = f"""
        <!DOCTYPE html>

        <html lang="es">

        <head>
            <meta charset="utf-8">

            <title>
                Lista de precios
            </title>

            <style>

                @page {{
                    size: A4 portrait;
                    margin: 14mm;
                }}

                body {{
                    font-family:
                        Arial,
                        sans-serif;

                    color: #222;
                    margin: 0;
                }}

                h1 {{
                    font-size: 22px;
                    margin-bottom: 4px;
                }}

                .fecha {{
                    color: #555;
                    margin-bottom: 16px;
                }}

                table {{
                    width: 100%;
                    border-collapse:
                        collapse;

                    font-size: 11px;
                }}

                th,
                td {{
                    border:
                        1px solid #999;

                    padding: 6px;
                }}

                th {{
                    background: #eeeeee;
                    text-align: left;
                }}

                .numero {{
                    text-align: right;
                    white-space: nowrap;
                    width: 120px;
                }}

            </style>

        </head>

        <body>

            <h1>
                Lista de precios
            </h1>

            <div class="fecha">
                Vigente al
                {
                    hoy.strftime(
                        "%d/%m/%Y"
                    )
                }
            </div>

            <table>

                <thead>
                    <tr>
                        <th>
                            Producto
                        </th>

                        <th class="numero">
                            Precio mayor
                        </th>

                        <th class="numero">
                            Precio menor
                        </th>
                    </tr>
                </thead>

                <tbody>
                    {''.join(filas_html)}
                </tbody>

            </table>

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

        archivo = (
            Path(
                tempfile.gettempdir()
            )
            / "lista_precios.html"
        )

        archivo.write_text(
            contenido,
            encoding="utf-8",
        )

        webbrowser.open(
            archivo.as_uri()
        )