from __future__ import annotations

import html
import tempfile
import tkinter as tk
import webbrowser

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from tkcalendar import DateEntry

from db.stock_repository import (
    ajustar_stock_producto,
    obtener_control_stock_necesidad,
)
from ui.ventana_util import maximizar_ventana


def numero(valor: Any) -> Decimal:
    if valor is None:
        return Decimal("0")

    return Decimal(str(valor))


def formato_cantidad(valor: Any) -> str:
    numero_decimal = numero(valor)

    if numero_decimal == numero_decimal.to_integral_value():
        return str(int(numero_decimal))

    return (
        f"{numero_decimal:,.3f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

def convertir_stock(texto: str) -> Decimal:
    valor = (
        texto
        .strip()
        .replace(" ", "")
    )

    if not valor:
        raise ValueError(
            "Debe indicar el stock contado."
        )

    if "," in valor and "." in valor:
        valor = (
            valor
            .replace(".", "")
            .replace(",", ".")
        )

    elif "," in valor:
        valor = valor.replace(",", ".")

    try:
        cantidad = Decimal(valor)

    except InvalidOperation as error:
        raise ValueError(
            "El stock contado no es válido."
        ) from error

    cantidad = cantidad.quantize(
        Decimal("0.001")
    )

    if cantidad < 0:
        raise ValueError(
            "El stock contado no puede ser negativo."
        )

    return cantidad
class VentanaStock(tk.Toplevel):
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

        self._filas_por_item: dict[
            str,
            dict[str, Any],
        ] = {}

        self._id_producto_ajuste: int | None = None

        self._stock_actual_ajuste = Decimal("0")

        self.title(
            "Stock y necesidad"
        )

        # Igual que las otras pantallas grandes.
        # self.transient(parent)

        self.resizable(
            True,
            True,
        )

        maximizar_ventana(self)

        self._crear_interfaz()

        self._seleccionar_semana_actual(
            actualizar=False
        )

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
            text="Stock y necesidad",
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

        self._crear_ajuste(
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
            text="Control",
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

        campos = ttk.Frame(
            marco
        )
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
        campos.columnconfigure(
            3,
            weight=0,
        )
        campos.columnconfigure(
            4,
            weight=0,
        )

        # -----------------------------
        # Desde
        # -----------------------------

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

        # -----------------------------
        # Hasta
        # -----------------------------

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
            padx=(0, 12),
            sticky="w",
        )

        # -----------------------------
        # Buscar producto
        # -----------------------------

        ttk.Label(
            campos,
            text="Buscar producto",
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )

        self.txt_buscar = ttk.Entry(
            campos
        )
        self.txt_buscar.grid(
            row=1,
            column=2,
            padx=(0, 12),
            sticky="ew",
        )

        self.txt_buscar.bind(
            "<KeyRelease>",
            self._aplicar_filtros,
        )

        # -----------------------------
        # Checkboxes
        # -----------------------------

        self.solo_necesidad = (
            tk.BooleanVar(
                value=False
            )
        )

        ttk.Checkbutton(
            campos,
            text="Sólo con necesidad",
            variable=self.solo_necesidad,
            command=self._aplicar_filtros,
        ).grid(
            row=1,
            column=3,
            padx=(0, 12),
            sticky="w",
        )

        self.solo_reserva = (
            tk.BooleanVar(
                value=False
            )
        )

        ttk.Checkbutton(
            campos,
            text="Sólo con reserva",
            variable=self.solo_reserva,
            command=self._aplicar_filtros,
        ).grid(
            row=1,
            column=4,
            sticky="w",
        )

        # -----------------------------
        # Acciones
        # -----------------------------

        acciones = ttk.Frame(
            marco
        )
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

    # =====================================================
    # Grilla
    # =====================================================

    def _crear_grilla(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text=(
                "Stock físico, compromiso "
                "y necesidad"
            ),
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
            "producto",
            "stock",
            "comprometido",
            "libre",
            "pedidos",
            "necesidad",
            "desde_stock",
            "elaborar",
            "estado",
        )

        self.grilla = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
        )

        titulos = {
            "producto": "Producto",
            "stock": "Stock actual",
            "comprometido": "Comprometido",
            "libre": "Stock libre",
            "pedidos": "Pedidos",
            "necesidad": "Necesidad",
            "desde_stock": "Desde stock",
            "elaborar": "A elaborar",
            "estado": "Estado",
        }

        for columna, titulo in (
            titulos.items()
        ):
            self.grilla.heading(
                columna,
                text=titulo,
            )

        self.grilla.column(
            "producto",
            width=310,
            minwidth=200,
            anchor="w",
            stretch=True,
        )

        for columna in (
            "stock",
            "comprometido",
            "libre",
            "necesidad",
            "desde_stock",
            "elaborar",
        ):
            self.grilla.column(
                columna,
                width=105,
                minwidth=85,
                anchor="e",
                stretch=False,
            )

        self.grilla.column(
            "pedidos",
            width=80,
            minwidth=70,
            anchor="center",
            stretch=False,
        )

        self.grilla.column(
            "estado",
            width=120,
            minwidth=100,
            anchor="center",
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

        self.grilla.bind(
            "<<TreeviewSelect>>",
            self._seleccionar_producto_ajuste,
        )


    def _crear_ajuste(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Ajuste de inventario",
            padding=10,
        )
        marco.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        marco.columnconfigure(
            0,
            weight=1,
        )

        # ---------------------------------
        # Producto seleccionado
        # ---------------------------------

        self.producto_ajuste = tk.StringVar(
            value=(
                "Seleccione un producto "
                "en la grilla."
            )
        )

        ttk.Label(
            marco,
            textvariable=self.producto_ajuste,
            font=(
                "Segoe UI",
                10,
                "bold",
            ),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 8),
        )

        campos = ttk.Frame(
            marco
        )
        campos.grid(
            row=1,
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
            weight=0,
        )
        campos.columnconfigure(
            3,
            weight=1,
        )

        # ---------------------------------
        # Stock sistema
        # ---------------------------------

        ttk.Label(
            campos,
            text="Stock sistema",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.stock_sistema_texto = (
            tk.StringVar(
                value="-"
            )
        )

        ttk.Label(
            campos,
            textvariable=(
                self.stock_sistema_texto
            ),
            font=(
                "Segoe UI",
                11,
                "bold",
            ),
        ).grid(
            row=1,
            column=0,
            padx=(0, 18),
            sticky="w",
        )

        # ---------------------------------
        # Stock contado
        # ---------------------------------

        ttk.Label(
            campos,
            text="Stock contado",
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )

        self.txt_stock_contado = ttk.Entry(
            campos,
            width=14,
            justify="right",
        )
        self.txt_stock_contado.grid(
            row=1,
            column=1,
            padx=(0, 18),
            sticky="w",
        )

        self.txt_stock_contado.bind(
            "<KeyRelease>",
            self._actualizar_diferencia_ajuste,
        )

        # ---------------------------------
        # Diferencia
        # ---------------------------------

        ttk.Label(
            campos,
            text="Diferencia",
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )

        self.diferencia_texto = (
            tk.StringVar(
                value="-"
            )
        )

        ttk.Label(
            campos,
            textvariable=(
                self.diferencia_texto
            ),
            font=(
                "Segoe UI",
                11,
                "bold",
            ),
        ).grid(
            row=1,
            column=2,
            padx=(0, 18),
            sticky="w",
        )

        # ---------------------------------
        # Motivo
        # ---------------------------------

        ttk.Label(
            campos,
            text="Motivo del ajuste",
        ).grid(
            row=0,
            column=3,
            sticky="w",
        )

        self.txt_motivo_ajuste = ttk.Entry(
            campos
        )
        self.txt_motivo_ajuste.grid(
            row=1,
            column=3,
            padx=(0, 12),
            sticky="ew",
        )

        # ---------------------------------
        # Botón
        # ---------------------------------

        self.btn_ajustar_stock = ttk.Button(
            campos,
            text="Ajustar stock",
            command=self._ajustar_stock,
            state="disabled",
        )
        self.btn_ajustar_stock.grid(
            row=1,
            column=4,
            sticky="e",
        )
    # =====================================================
    # Pie
    # =====================================================

    def _crear_pie(
        self,
        parent: ttk.Frame,
    ) -> None:
        pie = ttk.Frame(
            parent
        )
        pie.grid(
            row=4,
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
            font=(
                "Segoe UI",
                10,
                "bold",
            ),
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

    # =====================================================
    # Fechas
    # =====================================================

    def _seleccionar_semana_actual(
        self,
        *,
        actualizar: bool = True,
    ) -> None:
        hoy = date.today()

        lunes = (
            hoy
            - timedelta(
                days=hoy.weekday()
            )
        )

        domingo = (
            lunes
            + timedelta(days=6)
        )

        self.fecha_desde.set_date(
            lunes
        )

        self.fecha_hasta.set_date(
            domingo
        )

        if actualizar:
            self._actualizar()

    # =====================================================
    # Datos
    # =====================================================

    def _actualizar(self) -> None:
        fecha_desde = (
            self.fecha_desde
            .get_date()
        )

        fecha_hasta = (
            self.fecha_hasta
            .get_date()
        )

        if fecha_desde > fecha_hasta:
            messagebox.showwarning(
                "Stock y necesidad",
                (
                    "La fecha desde no puede "
                    "ser posterior a la "
                    "fecha hasta."
                ),
                parent=self,
            )
            return

        try:
            filas = (
                obtener_control_stock_necesidad(
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                )
            )

        except Exception as error:
            messagebox.showerror(
                "Stock y necesidad",
                (
                    "No se pudo recuperar "
                    "la información."
                    f"\n\n{error}"
                ),
                parent=self,
            )
            return

        self._filas_reporte = filas

        self._aplicar_filtros()

    def _aplicar_filtros(
        self,
        _evento=None,
    ) -> None:
        texto = (
            self.txt_buscar
            .get()
            .strip()
            .casefold()
        )

        filas = []

        for fila in (
            self._filas_reporte
        ):
            descripcion = str(
                fila["descripcion"]
                or ""
            )

            if (
                texto
                and texto
                not in descripcion.casefold()
            ):
                continue

            if (
                self.solo_necesidad.get()
                and numero(
                    fila[
                        "necesidad_periodo"
                    ]
                ) <= 0
            ):
                continue

            if (
                self.solo_reserva.get()
                and numero(
                    fila[
                        "stock_comprometido"
                    ]
                ) <= 0
            ):
                continue

            filas.append(
                fila
            )

        self._mostrar_filas(
            filas
        )

    def _mostrar_filas(
        self,
        filas: list[dict[str, Any]],
    ) -> None:
        self._limpiar_grilla()

        self._filas_por_item.clear()
        self._limpiar_ajuste()

        total_stock = Decimal("0")
        total_comprometido = Decimal("0")
        total_libre = Decimal("0")
        total_necesidad = Decimal("0")
        total_elaborar = Decimal("0")

        for indice, fila in enumerate(
            filas
        ):
            stock = numero(
                fila["stock_actual"]
            )

            comprometido = numero(
                fila[
                    "stock_comprometido"
                ]
            )

            libre = numero(
                fila["stock_libre"]
            )

            necesidad = numero(
                fila[
                    "necesidad_periodo"
                ]
            )

            desde_stock = numero(
                fila[
                    "cubrir_desde_stock"
                ]
            )

            elaborar = numero(
                fila[
                    "cantidad_a_elaborar"
                ]
            )

            total_stock += stock
            total_comprometido += (
                comprometido
            )
            total_libre += libre
            total_necesidad += necesidad
            total_elaborar += elaborar

            iid = f"stock-{indice}"

            self._filas_por_item[
                iid
            ] = fila

            self.grilla.insert(
                "",
                "end",
                iid=iid,
                values=(
                    fila["descripcion"],
                    formato_cantidad(
                        stock
                    ),
                    formato_cantidad(
                        comprometido
                    ),
                    formato_cantidad(
                        libre
                    ),
                    fila[
                        "cantidad_pedidos"
                    ],
                    formato_cantidad(
                        necesidad
                    ),
                    formato_cantidad(
                        desde_stock
                    ),
                    formato_cantidad(
                        elaborar
                    ),
                    fila[
                        "estado_control"
                    ],
                ),
            )

        self.estado.set(
            f"Productos: {len(filas)}"
            "  ·  "
            f"Stock: "
            f"{formato_cantidad(total_stock)}"
            "  ·  "
            f"Comprometido: "
            f"{formato_cantidad(total_comprometido)}"
            "  ·  "
            f"Libre: "
            f"{formato_cantidad(total_libre)}"
            "  ·  "
            f"Necesidad: "
            f"{formato_cantidad(total_necesidad)}"
            "  ·  "
            f"A elaborar: "
            f"{formato_cantidad(total_elaborar)}"
        )

    def _limpiar_grilla(
        self,
    ) -> None:
        for item in (
            self.grilla.get_children()
        ):
            self.grilla.delete(
                item
            )

    # =====================================================
    # Impresión
    # =====================================================
    def _seleccionar_producto_ajuste(
        self,
        _evento=None,
    ) -> None:
        seleccion = (
            self.grilla.selection()
        )

        if not seleccion:
            self._limpiar_ajuste()
            return

        fila = self._filas_por_item.get(
            seleccion[0]
        )

        if fila is None:
            self._limpiar_ajuste()
            return

        self._id_producto_ajuste = int(
            fila["id_producto"]
        )

        self._stock_actual_ajuste = numero(
            fila["stock_actual"]
        )

        self.producto_ajuste.set(
            str(
                fila["descripcion"]
            )
        )

        self.stock_sistema_texto.set(
            formato_cantidad(
                self._stock_actual_ajuste
            )
        )

        self.txt_stock_contado.delete(
            0,
            "end",
        )

        self.txt_motivo_ajuste.delete(
            0,
            "end",
        )

        self.diferencia_texto.set(
            "-"
        )

        self.btn_ajustar_stock.configure(
            state="normal"
        )

        self.txt_stock_contado.focus_set()


    def _limpiar_ajuste(self) -> None:
        self._id_producto_ajuste = None

        self._stock_actual_ajuste = (
            Decimal("0")
        )

        if hasattr(
            self,
            "producto_ajuste",
        ):
            self.producto_ajuste.set(
                "Seleccione un producto "
                "en la grilla."
            )

            self.stock_sistema_texto.set(
                "-"
            )

            self.diferencia_texto.set(
                "-"
            )

            self.txt_stock_contado.delete(
                0,
                "end",
            )

            self.txt_motivo_ajuste.delete(
                0,
                "end",
            )

            self.btn_ajustar_stock.configure(
                state="disabled"
            )


    def _actualizar_diferencia_ajuste(
        self,
        _evento=None,
    ) -> None:
        if self._id_producto_ajuste is None:
            return

        texto = (
            self.txt_stock_contado
            .get()
            .strip()
        )

        if not texto:
            self.diferencia_texto.set(
                "-"
            )
            return

        try:
            stock_contado = convertir_stock(
                texto
            )

        except ValueError:
            self.diferencia_texto.set(
                "-"
            )
            return

        diferencia = (
            stock_contado
            - self._stock_actual_ajuste
        )

        texto_diferencia = formato_cantidad(
            diferencia
        )

        if diferencia > 0:
            texto_diferencia = (
                "+"
                + texto_diferencia
            )

        self.diferencia_texto.set(
            texto_diferencia
        )


    def _ajustar_stock(self) -> None:
        if self._id_producto_ajuste is None:
            messagebox.showwarning(
                "Ajuste de stock",
                "Debe seleccionar un producto.",
                parent=self,
            )
            return

        try:
            stock_contado = convertir_stock(
                self.txt_stock_contado.get()
            )

        except ValueError as error:
            messagebox.showwarning(
                "Ajuste de stock",
                str(error),
                parent=self,
            )
            return

        motivo = (
            self.txt_motivo_ajuste
            .get()
            .strip()
        )

        if not motivo:
            messagebox.showwarning(
                "Ajuste de stock",
                (
                    "Debe indicar el motivo "
                    "del ajuste."
                ),
                parent=self,
            )

            self.txt_motivo_ajuste.focus_set()
            return

        diferencia = (
            stock_contado
            - self._stock_actual_ajuste
        )

        if diferencia == 0:
            messagebox.showinfo(
                "Ajuste de stock",
                (
                    "El stock contado coincide "
                    "con el stock del sistema.\n\n"
                    "No es necesario realizar "
                    "ningún ajuste."
                ),
                parent=self,
            )
            return

        diferencia_texto = (
            formato_cantidad(
                diferencia
            )
        )

        if diferencia > 0:
            diferencia_texto = (
                "+"
                + diferencia_texto
            )

        confirmar = messagebox.askyesno(
            "Confirmar ajuste de stock",
            (
                f"Producto:\n"
                f"{self.producto_ajuste.get()}\n\n"
                f"Stock sistema: "
                f"{formato_cantidad(self._stock_actual_ajuste)}\n"
                f"Stock contado: "
                f"{formato_cantidad(stock_contado)}\n"
                f"Diferencia: "
                f"{diferencia_texto}\n\n"
                f"Motivo:\n"
                f"{motivo}\n\n"
                "¿Confirma el ajuste?"
            ),
            parent=self,
        )

        if not confirmar:
            return

        # Segunda protección para ajustes enormes.
        if abs(diferencia) >= Decimal("1000"):
            confirmar_grande = (
                messagebox.askyesno(
                    "Ajuste extraordinario",
                    (
                        "ATENCIÓN\n\n"
                        "La diferencia ingresada es "
                        f"{diferencia_texto}.\n\n"
                        "Verifique nuevamente el "
                        "stock contado antes de "
                        "continuar.\n\n"
                        "¿Confirma que la cantidad "
                        "es correcta?"
                    ),
                    parent=self,
                )
            )

            if not confirmar_grande:
                self.txt_stock_contado.focus_set()
                return

        try:
            resultado = ajustar_stock_producto(
                id_producto=(
                    self._id_producto_ajuste
                ),
                stock_contado=stock_contado,
                motivo=motivo,
            )

        except Exception as error:
            messagebox.showerror(
                "Ajuste de stock",
                (
                    "No se pudo registrar "
                    "el ajuste."
                    f"\n\n{error}"
                ),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Ajuste de stock",
            (
                "Stock ajustado correctamente."
                "\n\n"
                f"Movimiento: "
                f"{resultado['tipo_movimiento']}\n"
                f"Cantidad: "
                f"{formato_cantidad(resultado['cantidad_movimiento'])}\n"
                f"Stock anterior: "
                f"{formato_cantidad(resultado['stock_anterior'])}\n"
                f"Stock actual: "
                f"{formato_cantidad(resultado['stock_resultante'])}"
            ),
            parent=self,
        )

        self._actualizar()
    def _imprimir(self) -> None:
        filas_visibles = []

        for item in (
            self.grilla.get_children()
        ):
            filas_visibles.append(
                self.grilla.item(
                    item,
                    "values",
                )
            )

        if not filas_visibles:
            messagebox.showinfo(
                "Stock y necesidad",
                (
                    "No hay información "
                    "para imprimir."
                ),
                parent=self,
            )
            return

        fecha_desde = (
            self.fecha_desde
            .get_date()
        )

        fecha_hasta = (
            self.fecha_hasta
            .get_date()
        )

        filas_html: list[str] = []

        for valores in filas_visibles:
            (
                producto,
                stock,
                comprometido,
                libre,
                pedidos,
                necesidad,
                desde_stock,
                elaborar,
                estado,
            ) = valores

            filas_html.append(
                f"""
                <tr>
                    <td>
                        {
                            html.escape(
                                str(producto)
                            )
                        }
                    </td>

                    <td class="numero">
                        {stock}
                    </td>

                    <td class="numero">
                        {comprometido}
                    </td>

                    <td class="numero">
                        {libre}
                    </td>

                    <td class="numero">
                        {pedidos}
                    </td>

                    <td class="numero">
                        {necesidad}
                    </td>

                    <td class="numero">
                        {desde_stock}
                    </td>

                    <td class="numero">
                        {elaborar}
                    </td>

                    <td>
                        {
                            html.escape(
                                str(estado)
                            )
                        }
                    </td>
                </tr>
                """
            )

        contenido = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="utf-8">

            <title>
                Stock y necesidad
            </title>

            <style>
                @page {{
                    size: A4 landscape;
                    margin: 12mm;
                }}

                body {{
                    font-family:
                        Arial,
                        sans-serif;
                    color: #222;
                    margin: 0;
                }}

                h1 {{
                    font-size: 20px;
                    margin-bottom: 4px;
                }}

                .periodo {{
                    margin-bottom: 16px;
                    color: #555;
                }}

                table {{
                    width: 100%;
                    border-collapse:
                        collapse;
                    font-size: 10px;
                }}

                th,
                td {{
                    border:
                        1px solid #999;
                    padding: 5px;
                }}

                th {{
                    background: #eeeeee;
                    text-align: left;
                }}

                .numero {{
                    text-align: right;
                }}

                .pie {{
                    margin-top: 12px;
                    font-size: 10px;
                    color: #666;
                }}
            </style>
        </head>

        <body>
            <h1>
                Stock y necesidad
            </h1>

            <div class="periodo">
                Necesidad entre
                {
                    fecha_desde.strftime(
                        "%d/%m/%Y"
                    )
                }
                y
                {
                    fecha_hasta.strftime(
                        "%d/%m/%Y"
                    )
                }
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Producto</th>
                        <th>Stock</th>
                        <th>Comprometido</th>
                        <th>Libre</th>
                        <th>Pedidos</th>
                        <th>Necesidad</th>
                        <th>Desde stock</th>
                        <th>A elaborar</th>
                        <th>Estado</th>
                    </tr>
                </thead>

                <tbody>
                    {
                        ''.join(
                            filas_html
                        )
                    }
                </tbody>
            </table>

            <div class="pie">
                Reporte generado desde
                el Punto de Venta.
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

        archivo = (
            Path(
                tempfile.gettempdir()
            )
            / "stock_necesidad.html"
        )

        archivo.write_text(
            contenido,
            encoding="utf-8",
        )

        webbrowser.open(
            archivo.as_uri()
        )

