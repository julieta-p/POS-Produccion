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

from tkcalendar import DateEntry

from db.reporte_pedidos_repository import (
    listar_detalle_reparto,
    listar_pedidos_por_entregar,
)

from ui.pedido import (
    formato_cantidad,
    formato_decimal,
)
from ui.ventana_util import maximizar_ventana


PALETA_CLARO = {
    "bg": "#f3f1ef", "surface": "#ffffff", "border": "#ddd7d4",
    "text": "#252328", "muted": "#6d6870", "sidebar": "#3a111b",
    "sidebar_hover": "#511522", "gold": "#c99624", "burgundy": "#b93657",
    "burgundy_dark": "#8e2440", "white": "#ffffff", "surface2": "#f7f5f4",
}

PALETA_OSCURO = {
    "bg": "#15171b", "surface": "#20242a", "border": "#3b414a",
    "text": "#f3f4f6", "muted": "#aeb5bf", "sidebar": "#321019",
    "sidebar_hover": "#4a1723", "gold": "#d5a63a", "burgundy": "#c33b5c",
    "burgundy_dark": "#982a45", "white": "#ffffff", "surface2": "#2a2f36",
}


def numero(valor: Any) -> Decimal:
    if valor is None:
        return Decimal("0")

    return Decimal(str(valor))


def fecha_texto(valor: Any) -> str:
    if valor is None:
        return ""

    return valor.strftime("%d/%m/%Y")


def hora_texto(valor: Any) -> str:
    if valor is None:
        return ""

    try:
        return valor.strftime("%H:%M")
    except AttributeError:
        return str(valor)[:5]


class VentanaReportePedidos(tk.Toplevel):
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

        self._filas_visibles: list[
            dict[str, Any]
        ] = []
        self._tema = getattr(navegador, "tema", "claro")
        self._botones: list[tk.Button] = []
        self._botones_info: list[tuple[tk.Widget, str]] = []

        self.title(
            "Pedidos por entregar - Doña Elina"
        )

        self.resizable(
            True,
            True,
        )

        maximizar_ventana(self)

        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._crear_interfaz()
        self._aplicar_tema()

        self._seleccionar_hoy(
            actualizar=False
        )

        self._actualizar()

    # =====================================================
    # Barra lateral y tema
    # =====================================================

    def colores(self) -> dict[str, str]:
        return PALETA_OSCURO if self._tema == "oscuro" else PALETA_CLARO

    def _crear_sidebar(self) -> None:
        c = self.colores()
        self.sidebar = tk.Frame(self, bg=c["sidebar"], width=265, bd=0)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        logo_box = tk.Frame(self.sidebar, bg="#fff9f9", bd=0)
        logo_box.pack(fill="x", padx=14, pady=(16, 14))
        ruta = Path(__file__).resolve().parent.parent / "assets" / "logo_dona_elina.png"
        try:
            self._logo_img = tk.PhotoImage(file=str(ruta))
            if self._logo_img.width() > 215:
                factor = max(1, self._logo_img.width() // 215)
                self._logo_img = self._logo_img.subsample(factor, factor)
            self.logo_label = tk.Label(logo_box, image=self._logo_img, bg="#fff9f9", bd=0)
            self.logo_label.pack(padx=8, pady=8)
        except Exception:
            self.logo_label = tk.Label(logo_box, text="Doña Elina", font=("Segoe Script", 24, "bold"),
                                      fg=c["burgundy"], bg="#fff9f9", bd=0)
            self.logo_label.pack(pady=25)

        self._titulo_sidebar("ACCESOS RÁPIDOS")
        self._sidebar_button("＋", "Nuevo pedido", lambda: self.navegador.abrir_pedido(self))
        self._sidebar_button("☷", "Lista de precios", lambda: self.navegador.abrir_reporte_precios(self))
        self._sidebar_button("▰", "Salidas y Entregas", lambda: self.navegador.abrir_salidas(self))
        self._sidebar_button("⚙", "Configuración", lambda: messagebox.showinfo("Configuración", "Esta función se mantiene para el próximo módulo.", parent=self))

        linea = tk.Frame(self.sidebar, height=1, bg=c["gold"], bd=0)
        linea.pack(fill="x", padx=20, pady=(10, 8))
        self._botones_info.append((linea, "gold"))

        self._sidebar_button("‹", "Volver a Pedidos", lambda: self.navegador.abrir_pedidos(self))
        self._sidebar_button("×", "Salir", self.destroy)

        pie = tk.Label(self.sidebar, text="Doña Elina - Sistema de Gestión\nVersión 1.0.0",
                       font=("Segoe UI", 8), anchor="w", justify="left", bd=0,
                       bg=c["sidebar"], fg=c["gold"])
        pie.pack(side="bottom", fill="x", padx=22, pady=16)
        self.pie = pie

    def _titulo_sidebar(self, texto: str) -> None:
        c = self.colores()
        label = tk.Label(self.sidebar, text=texto, font=("Segoe UI", 10, "bold"),
                         fg=c["gold"], bg=c["sidebar"], anchor="w", bd=0)
        label.pack(fill="x", padx=22, pady=(4, 7))
        linea = tk.Frame(self.sidebar, height=1, bg=c["gold"], bd=0)
        linea.pack(fill="x", padx=20, pady=(0, 8))
        self._botones_info.extend(((label, "sidebar"), (linea, "gold")))

    def _sidebar_button(self, icono: str, texto: str, comando) -> None:
        c = self.colores()
        boton = tk.Button(self.sidebar, text=f"  {icono}   {texto}", command=comando, anchor="w",
                          font=("Segoe UI", 10, "bold"), bg=c["sidebar"], fg=c["white"],
                          activebackground=c["sidebar_hover"], activeforeground=c["white"], bd=0,
                          relief="flat", padx=12, pady=9, cursor="hand2",
                          highlightthickness=1, highlightbackground=c["sidebar"])
        boton.pack(fill="x", padx=12, pady=2)
        self._botones.append(boton)
        self._bind_hover(boton)

    def _bind_hover(self, boton: tk.Button) -> None:
        def entrar(_event=None):
            c = self.colores()
            boton.configure(bg=c["sidebar_hover"])
        def salir(_event=None):
            c = self.colores()
            boton.configure(bg=c["sidebar"])
        boton.bind("<Enter>", entrar)
        boton.bind("<Leave>", salir)
        boton.bind("<ButtonRelease-1>", lambda _e: boton.after(80, salir))

    def _alternar_tema(self) -> None:
        self._tema = "oscuro" if self._tema == "claro" else "claro"
        if self.navegador is not None:
            try:
                self.navegador.tema = self._tema
            except Exception:
                pass
        self._aplicar_tema()

    def _configurar_estilos(self) -> None:
        c = self.colores()
        style = ttk.Style(self)

        # Estilos propios del módulo para evitar que el tema nativo de
        # Tk/ttk vuelva a pintar los controles con grises/blancos.
        style.configure(
            "Pedidos.TFrame",
            background=c["bg"],
        )
        style.configure(
            "Pedidos.Surface.TFrame",
            background=c["surface"],
        )
        style.configure(
            "Pedidos.TLabel",
            background=c["surface"],
            foreground=c["text"],
        )
        style.configure(
            "Pedidos.Muted.TLabel",
            background=c["surface"],
            foreground=c["muted"],
        )
        style.configure(
            "Pedidos.TLabelframe",
            background=c["surface"],
            foreground=c["text"],
            bordercolor=c["border"],
            lightcolor=c["border"],
            darkcolor=c["border"],
        )
        style.configure(
            "Pedidos.TLabelframe.Label",
            background=c["surface"],
            foreground=c["burgundy"],
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Pedidos.TEntry",
            fieldbackground=c["surface"],
            foreground=c["text"],
            insertcolor=c["text"],
            bordercolor=c["border"],
            lightcolor=c["border"],
            darkcolor=c["border"],
        )
        style.map(
            "Pedidos.TEntry",
            fieldbackground=[("disabled", c["surface2"])],
            foreground=[("disabled", c["muted"])],
        )
        style.configure(
            "Pedidos.TCombobox",
            fieldbackground=c["surface"],
            foreground=c["text"],
            background=c["surface"],
            bordercolor=c["border"],
            lightcolor=c["border"],
            darkcolor=c["border"],
            arrowcolor=c["text"],
        )
        style.map(
            "Pedidos.TCombobox",
            fieldbackground=[("readonly", c["surface"])],
            foreground=[("readonly", c["text"])],
        )
        style.configure(
            "Pedidos.TCheckbutton",
            background=c["surface"],
            foreground=c["text"],
        )
        style.map(
            "Pedidos.TCheckbutton",
            background=[("active", c["surface2"])],
            foreground=[("disabled", c["muted"])],
        )
        style.configure(
            "Pedidos.TButton",
            background=c["surface2"],
            foreground=c["text"],
            bordercolor=c["border"],
            lightcolor=c["border"],
            darkcolor=c["border"],
            padding=(10, 6),
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "Pedidos.TButton",
            background=[("active", c["burgundy"]), ("pressed", c["burgundy_dark"])],
            foreground=[("active", c["white"]), ("pressed", c["white"])],
        )
        style.configure(
            "Pedidos.Treeview",
            background=c["surface2"],
            fieldbackground=c["surface2"],
            foreground=c["text"],
            rowheight=30,
            bordercolor=c["border"],
        )
        style.configure(
            "Pedidos.Treeview.Heading",
            background=c["burgundy"],
            foreground=c["white"],
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "Pedidos.Treeview",
            background=[("selected", c["burgundy_dark"])],
            foreground=[("selected", c["white"])],
        )
        style.configure(
            "Pedidos.Vertical.TScrollbar",
            background=c["surface2"],
            troughcolor=c["bg"],
            bordercolor=c["border"],
            arrowcolor=c["text"],
        )
        style.configure(
            "Pedidos.Horizontal.TScrollbar",
            background=c["surface2"],
            troughcolor=c["bg"],
            bordercolor=c["border"],
            arrowcolor=c["text"],
        )

        # También actualizamos los estilos por defecto para los controles
        # nativos que puedan aparecer dentro de DateEntry.
        style.configure("TEntry", fieldbackground=c["surface"], foreground=c["text"], insertcolor=c["text"])
        style.configure("TCombobox", fieldbackground=c["surface"], foreground=c["text"], background=c["surface"])
        style.map("TCombobox", fieldbackground=[("readonly", c["surface"])], foreground=[("readonly", c["text"])])
        style.configure("TCheckbutton", background=c["surface"], foreground=c["text"])

    def _configurar_dateentry(self, widget: DateEntry) -> None:
        c = self.colores()
        # En Linux tkcalendar combina un contenedor DateEntry con un Entry
        # interno. Configuramos ambos para evitar que el Entry interno conserve
        # el gris/blanco del tema nativo.
        opciones = {
            "background": c["bg"],
            "foreground": c["text"],
            "selectbackground": c["burgundy"],
            "selectforeground": c["white"],
            "normalbackground": c["bg"],
            "normalforeground": c["text"],
            "bordercolor": c["border"],
        }
        for clave, valor in opciones.items():
            try:
                widget.configure(**{clave: valor})
            except (tk.TclError, TypeError):
                pass

        try:
            widget.entry.configure(
                background=c["bg"],
                foreground=c["text"],
                insertbackground=c["text"],
                selectbackground=c["burgundy"],
                selectforeground=c["white"],
                disabledbackground=c["surface2"],
                disabledforeground=c["muted"],
                highlightbackground=c["border"],
                highlightcolor=c["burgundy"],
            )
        except (tk.TclError, AttributeError):
            pass

    def _aplicar_tema(self) -> None:
        c = self.colores()
        self.configure(bg=c["bg"])
        self._configurar_estilos()
        self.sidebar.configure(bg=c["sidebar"])
        for widget, tipo in self._botones_info:
            try:
                widget.configure(bg=c["gold"] if tipo == "gold" else c["sidebar"],
                                  fg=c["gold"] if tipo == "sidebar" else widget.cget("fg"))
            except tk.TclError:
                pass
        for boton in self._botones:
            boton.configure(bg=c["sidebar"], fg=c["white"], activebackground=c["sidebar_hover"],
                            activeforeground=c["white"])
        self.pie.configure(bg=c["sidebar"], fg=c["gold"])
        self._actualizar_widgets_tema(self, c)
        if hasattr(self, "fecha_desde"):
            self._configurar_dateentry(self.fecha_desde)
            self._configurar_dateentry(self.fecha_hasta)

        # Estos cuatro controles deben verse como un único bloque visual,
        # sin el gris por defecto del tema de Tk/ttk.
        for widget in (
            getattr(self, "cbo_modalidad", None),
            getattr(self, "txt_cliente", None),
        ):
            if widget is None:
                continue
            try:
                widget.configure(
                    style=(
                        "Pedidos.TCombobox"
                        if isinstance(widget, ttk.Combobox)
                        else "Pedidos.TEntry"
                    )
                )
            except tk.TclError:
                pass

        if hasattr(self, "btn_tema"):
            self.btn_tema.configure(text="☾  Modo oscuro" if self._tema == "claro" else "☀  Modo claro",
                                    bg=c["surface"], fg=c["text"], activebackground=c["surface"],
                                    activeforeground=c["text"], highlightbackground=c["border"])

    def _actualizar_widgets_tema(self, widget, c) -> None:
        try:
            if widget is self.sidebar:
                return
            if isinstance(widget, tk.Label):
                widget.configure(bg=c["surface"], fg=c["text"])
            elif isinstance(widget, tk.Frame):
                widget.configure(bg=c["surface"])
        except tk.TclError:
            pass
        for hijo in widget.winfo_children():
            self._actualizar_widgets_tema(hijo, c)

    # =====================================================
    # Interfaz
    # =====================================================

    def _crear_interfaz(self) -> None:
        self._crear_sidebar()

        contenedor = ttk.Frame(
            self,
            padding=(22, 18),
            style="Pedidos.TFrame",
        )
        contenedor.grid(
            row=0,
            column=1,
            sticky="nsew",
        )

        contenedor.columnconfigure(
            0,
            weight=1,
        )

        contenedor.rowconfigure(
            2,
            weight=1,
        )

        encabezado = ttk.Frame(contenedor, style="Pedidos.Surface.TFrame")
        encabezado.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        encabezado.columnconfigure(0, weight=1)

        titulo = ttk.Label(
            encabezado,
            text="🚚  Pedidos por entregar",
            style="Pedidos.TLabel",
            font=("Segoe UI", 24, "bold"),
        )
        titulo.grid(
            row=0,
            column=0,
            sticky="w",
            padx=(14, 8),
            pady=(12, 2),
        )

        subtitulo = ttk.Label(encabezado, text="Controlá y organizá los pedidos pendientes de entrega", style="Pedidos.Muted.TLabel",
                              font=("Segoe UI", 10))
        subtitulo.grid(row=1, column=0, sticky="w", padx=(16, 8), pady=(0, 12))

        self.btn_tema = tk.Button(encabezado, text="☾  Modo oscuro", command=self._alternar_tema,
                                  font=("Segoe UI", 9, "bold"), bd=0, relief="flat", padx=12, pady=7,
                                  cursor="hand2", highlightthickness=1)
        self.btn_tema.grid(row=0, column=1, rowspan=2, padx=(8, 14), pady=10)

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
            text="Control de entregas",
            padding=10,
            style="Pedidos.TLabelframe",
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
            marco,
            style="Pedidos.Surface.TFrame",
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
            weight=0,
        )
        campos.columnconfigure(
            3,
            weight=1,
        )
        campos.columnconfigure(
            4,
            weight=0,
        )

        # Desde
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
            style="Pedidos.TEntry",
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

        self._configurar_dateentry(self.fecha_desde)

        self.fecha_desde.bind(
            "<<DateEntrySelected>>",
            self._sincronizar_fecha_hasta,
        )

        # Hasta
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
            style="Pedidos.TEntry",
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

        # Modalidad
        ttk.Label(
            campos,
            text="Modalidad",
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )

        self.cbo_modalidad = ttk.Combobox(
            campos,
            style="Pedidos.TCombobox",
            state="readonly",
            width=14,
            values=(
                "TODAS",
                "MOSTRADOR",
                "REPARTO",
            ),
        )
        self.cbo_modalidad.grid(
            row=1,
            column=2,
            padx=(0, 12),
            sticky="w",
        )
        self.cbo_modalidad.set(
            "TODAS"
        )

        # Cliente
        ttk.Label(
            campos,
            text="Cliente",
        ).grid(
            row=0,
            column=3,
            sticky="w",
        )

        self.txt_cliente = ttk.Entry(
            campos,
            style="Pedidos.TEntry",
        )
        self.txt_cliente.grid(
            row=1,
            column=3,
            padx=(0, 12),
            sticky="ew",
        )

        self.txt_cliente.bind(
            "<Return>",
            lambda _evento:
                self._actualizar(),
        )

        # Sólo revisar
        self.solo_revisar = tk.BooleanVar(
            value=False
        )

        ttk.Checkbutton(
            campos,
            text="Sólo REVISAR",
            style="Pedidos.TCheckbutton",
            variable=self.solo_revisar,
            command=self._actualizar,
        ).grid(
            row=1,
            column=4,
            sticky="w",
        )

        # ---------------------------------
        # Botones: ARRIBA, como manda la ley
        # ---------------------------------

        acciones = ttk.Frame(
            marco,
            style="Pedidos.Surface.TFrame",
        )
        acciones.grid(
            row=1,
            column=0,
            sticky="e",
            pady=(8, 0),
        )

        ttk.Button(
            acciones,
            text="Hoy",
            style="Pedidos.TButton",
            command=self._seleccionar_hoy,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            acciones,
            text="Actualizar",
            style="Pedidos.TButton",
            command=self._actualizar,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            acciones,
            text="🖨 Imprimir",
            style="Pedidos.TButton",
            command=self._imprimir,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            acciones,
            text="Cerrar",
            style="Pedidos.TButton",
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
            text="Pedidos pendientes",
            padding=8,
            style="Pedidos.TLabelframe",
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
            "entrega",
            "hora",
            "pedido",
            "cliente",
            "modalidad",
            "direccion",
            "pendiente",
            "estado",
            "alerta",
        )

        self.grilla = ttk.Treeview(
            marco,
            style="Pedidos.Treeview",
            columns=columnas,
            show="headings",
            selectmode="browse",
        )

        titulos = {
            "entrega": "Entrega",
            "hora": "Hora",
            "pedido": "Pedido",
            "cliente": "Cliente",
            "modalidad": "Modalidad",
            "direccion": "Dirección",
            "pendiente": "Pendiente",
            "estado": "Estado",
            "alerta": "Alerta",
        }

        for columna, titulo in (
            titulos.items()
        ):
            self.grilla.heading(
                columna,
                text=titulo,
            )

        self.grilla.column(
            "entrega",
            width=95,
            minwidth=90,
            anchor="center",
            stretch=False,
        )

        self.grilla.column(
            "hora",
            width=65,
            minwidth=60,
            anchor="center",
            stretch=False,
        )

        self.grilla.column(
            "pedido",
            width=70,
            minwidth=65,
            anchor="center",
            stretch=False,
        )

        self.grilla.column(
            "cliente",
            width=260,
            minwidth=160,
            anchor="w",
            stretch=True,
        )

        self.grilla.column(
            "modalidad",
            width=100,
            minwidth=90,
            anchor="center",
            stretch=False,
        )

        self.grilla.column(
            "direccion",
            width=280,
            minwidth=160,
            anchor="w",
            stretch=True,
        )

        self.grilla.column(
            "pendiente",
            width=100,
            minwidth=85,
            anchor="e",
            stretch=False,
        )

        self.grilla.column(
            "estado",
            width=120,
            minwidth=100,
            anchor="center",
            stretch=False,
        )

        self.grilla.column(
            "alerta",
            width=95,
            minwidth=80,
            anchor="center",
            stretch=False,
        )

        barra_vertical = ttk.Scrollbar(
            marco,
            orient="vertical",
            command=self.grilla.yview,
            style="Pedidos.Vertical.TScrollbar",
        )

        barra_horizontal = ttk.Scrollbar(
            marco,
            orient="horizontal",
            command=self.grilla.xview,
            style="Pedidos.Horizontal.TScrollbar",
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

    # =====================================================
    # Pie
    # =====================================================

    def _crear_pie(
        self,
        parent: ttk.Frame,
    ) -> None:
        pie = ttk.Frame(
            parent,
            style="Pedidos.TFrame",
        )
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

    def _sincronizar_fecha_hasta(
        self,
        _evento=None,
    ) -> None:
        self.fecha_hasta.set_date(
            self.fecha_desde.get_date()
        )

    def _seleccionar_hoy(
        self,
        *,
        actualizar: bool = True,
    ) -> None:
        hoy = date.today()

        self.fecha_desde.set_date(
            hoy
        )

        self.fecha_hasta.set_date(
            hoy
        )

        if actualizar:
            self._actualizar()

    # =====================================================
    # Consulta
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
                "Pedidos por entregar",
                (
                    "La fecha desde no puede "
                    "ser posterior a la fecha hasta."
                ),
                parent=self,
            )
            return

        modalidad = (
            self.cbo_modalidad
            .get()
            .strip()
            .upper()
        )

        if modalidad == "TODAS":
            modalidad = None

        cliente = (
            self.txt_cliente
            .get()
            .strip()
            or None
        )

        try:
            filas = listar_pedidos_por_entregar(
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                modalidad=modalidad,
                cliente=cliente,
                solo_revisar=(
                    self.solo_revisar.get()
                ),
            )

        except Exception as error:
            messagebox.showerror(
                "Pedidos por entregar",
                (
                    "No se pudieron recuperar "
                    "los pedidos."
                    f"\n\n{error}"
                ),
                parent=self,
            )
            return

        self._filas_reporte = filas
        self._filas_visibles = filas

        self._mostrar_filas(
            filas
        )

    def _mostrar_filas(
        self,
        filas: list[dict[str, Any]],
    ) -> None:
        for item in (
            self.grilla.get_children()
        ):
            self.grilla.delete(
                item
            )

        total_pendiente = Decimal("0")
        cantidad_revisar = 0

        for indice, fila in enumerate(
            filas
        ):
            pendiente = numero(
                fila[
                    "cantidad_total_pendiente"
                ]
            )

            total_pendiente += pendiente

            alerta = str(
                fila.get(
                    "alerta",
                    "",
                )
                or ""
            )

            if alerta == "REVISAR":
                cantidad_revisar += 1

            self.grilla.insert(
                "",
                "end",
                iid=f"pedido-{indice}",
                values=(
                    fecha_texto(
                        fila["fecha_entrega"]
                    ),
                    hora_texto(
                        fila["hora_entrega"]
                    ),
                    fila["id_pedido"],
                    fila["cliente"],
                    fila["modalidad_entrega"],
                    fila.get(
                        "direccion_entrega"
                    )
                    or "",
                    formato_cantidad(
                        pendiente
                    ),
                    fila["estado_pedido"],
                    alerta,
                ),
            )

        self.estado.set(
            f"Pedidos: {len(filas)}"
            "  ·  "
            f"Cantidad pendiente: "
            f"{formato_cantidad(total_pendiente)}"
            "  ·  "
            f"REVISAR: {cantidad_revisar}"
        )

    # =====================================================
    # Impresión
    # =====================================================

    def _imprimir(self) -> None:
        if not self._filas_visibles:
            messagebox.showinfo(
                "Pedidos por entregar",
                "No hay información para imprimir.",
                parent=self,
            )
            return

        modalidad = (
            self.cbo_modalidad
            .get()
            .strip()
            .upper()
        )

        if modalidad == "REPARTO":
            self._imprimir_reparto()
            return

        self._imprimir_listado()

    def _imprimir_listado(self) -> None:
        fecha_desde = (
            self.fecha_desde
            .get_date()
        )

        fecha_hasta = (
            self.fecha_hasta
            .get_date()
        )

        filas_html: list[str] = []

        for fila in self._filas_visibles:
            alerta = html.escape(
                str(
                    fila.get(
                        "alerta",
                        "",
                    )
                    or ""
                )
            )

            filas_html.append(
                f"""
                <tr>
                    <td>{fecha_texto(fila["fecha_entrega"])}</td>
                    <td>{hora_texto(fila["hora_entrega"])}</td>
                    <td>{fila["id_pedido"]}</td>
                    <td>{html.escape(str(fila["cliente"]))}</td>
                    <td>{html.escape(str(fila["modalidad_entrega"]))}</td>
                    <td>{html.escape(str(fila.get("direccion_entrega") or ""))}</td>
                    <td class="numero">
                        {formato_cantidad(numero(fila["cantidad_total_pendiente"]))}
                    </td>
                    <td>{html.escape(str(fila["estado_pedido"]))}</td>
                    <td><strong>{alerta}</strong></td>
                </tr>
                """
            )

        contenido = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="utf-8">

            <title>Pedidos por entregar</title>

            <style>
                @page {{
                    size: A4 landscape;
                    margin: 12mm;
                }}

                body {{
                    font-family: Arial, sans-serif;
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
                    border-collapse: collapse;
                    font-size: 10px;
                }}

                th,
                td {{
                    border: 1px solid #999;
                    padding: 5px;
                }}

                th {{
                    background: #eeeeee;
                    text-align: left;
                }}

                .numero {{
                    text-align: right;
                }}
            </style>
        </head>

        <body>
            <h1>Pedidos por entregar</h1>

            <div class="periodo">
                Período:
                {fecha_desde.strftime("%d/%m/%Y")}
                al
                {fecha_hasta.strftime("%d/%m/%Y")}
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Entrega</th>
                        <th>Hora</th>
                        <th>Pedido</th>
                        <th>Cliente</th>
                        <th>Modalidad</th>
                        <th>Dirección</th>
                        <th>Pendiente</th>
                        <th>Estado</th>
                        <th>Alerta</th>
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

        self._abrir_html(
            contenido,
            "pedidos_por_entregar.html",
        )

    def _imprimir_reparto(self) -> None:
        fecha_desde = (
            self.fecha_desde
            .get_date()
        )

        fecha_hasta = (
            self.fecha_hasta
            .get_date()
        )

        ids_visibles = {
            int(fila["id_pedido"])
            for fila in self._filas_visibles
        }

        try:
            detalle = listar_detalle_reparto(
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
            )

        except Exception as error:
            messagebox.showerror(
                "Hoja de reparto",
                (
                    "No se pudo recuperar "
                    "el detalle del reparto."
                    f"\n\n{error}"
                ),
                parent=self,
            )
            return

        detalle = [
            fila
            for fila in detalle
            if int(fila["id_pedido"])
            in ids_visibles
        ]

        if not detalle:
            messagebox.showinfo(
                "Hoja de reparto",
                (
                    "No hay pedidos de reparto "
                    "para imprimir."
                ),
                parent=self,
            )
            return

        # =====================================================
        # Agrupar detalle por pedido
        # =====================================================

        pedidos: dict[
            int,
            list[dict[str, Any]],
        ] = {}

        # Resumen general de carga.
        # El envío NO participa porque no es producto.
        resumen_carga: dict[
            str,
            Decimal,
        ] = {}

        total_carga = Decimal("0")

        for fila in detalle:
            id_pedido = int(
                fila["id_pedido"]
            )

            pedidos.setdefault(
                id_pedido,
                [],
            ).append(
                fila
            )

            producto = str(
                fila["descripcion_producto"]
            )

            cantidad = numero(
                fila["cantidad_pendiente"]
            )

            resumen_carga[producto] = (
                resumen_carga.get(
                    producto,
                    Decimal("0"),
                )
                + cantidad
            )

            total_carga += cantidad

        # =====================================================
        # Bloques por pedido
        # =====================================================

        bloques_html: list[str] = []

        for id_pedido, productos in (
            pedidos.items()
        ):
            encabezado = productos[0]

            # -------------------------------------------------
            # Contacto
            # -------------------------------------------------

            telefono = str(
                encabezado.get(
                    "telefono"
                )
                or ""
            ).strip()

            celular = str(
                encabezado.get(
                    "celular"
                )
                or ""
            ).strip()

            contactos = []

            if telefono:
                contactos.append(
                    f"Tel.: {html.escape(telefono)}"
                )

            if celular:
                contactos.append(
                    f"Cel.: {html.escape(celular)}"
                )

            contacto_texto = (
                " / ".join(contactos)
                if contactos
                else "Sin teléfono informado"
            )

            direccion = str(
                encabezado.get(
                    "direccion_entrega"
                )
                or ""
            ).strip()

            localidad = str(
                encabezado.get(
                    "localidad"
                )
                or ""
            ).strip()

            ubicacion = []

            if direccion:
                ubicacion.append(
                    html.escape(direccion)
                )

            if localidad:
                ubicacion.append(
                    html.escape(localidad)
                )

            ubicacion_texto = (
                " - ".join(ubicacion)
                if ubicacion
                else "Sin dirección informada"
            )

            # -------------------------------------------------
            # Productos
            # -------------------------------------------------

            filas_productos: list[str] = []

            total_productos = Decimal("0")

            for producto in productos:
                cantidad = numero(
                    producto[
                        "cantidad_pendiente"
                    ]
                )

                precio_unitario = numero(
                    producto[
                        "precio_unitario"
                    ]
                )

                descuento = numero(
                    producto.get(
                        "descuento"
                    )
                )

                importe_linea = numero(
                    producto[
                        "importe_linea"
                    ]
                )

                total_productos += (
                    importe_linea
                )

                tipo_precio = str(
                    producto.get(
                        "tipo_precio"
                    )
                    or ""
                ).strip().upper()

                tipo_precio_texto = {
                    "MAYOR": "Mayor",
                    "MENOR": "Menor",
                    "ESPECIAL": "Especial",
                }.get(
                    tipo_precio,
                    tipo_precio.title(),
                )

                descuento_html = ""

                if descuento > 0:
                    descuento_html = (
                        "<div class='descuento'>"
                        "Desc.: $"
                        f"{formato_decimal(descuento, decimales=2)}"
                        "</div>"
                    )

                filas_productos.append(
                    f"""
                    <tr>
                        <td>
                            {
                                html.escape(
                                    str(
                                        producto[
                                            "descripcion_producto"
                                        ]
                                    )
                                )
                            }
                        </td>

                        <td class="numero cantidad">
                            {
                                formato_cantidad(
                                    cantidad
                                )
                            }
                        </td>

                        <td class="centro">
                            {tipo_precio_texto}
                        </td>

                        <td class="numero">
                            $
                            {
                                formato_decimal(
                                    precio_unitario,
                                    decimales=2,
                                )
                            }
                        </td>

                        <td class="numero">
                            $
                            {
                                formato_decimal(
                                    importe_linea,
                                    decimales=2,
                                )
                            }

                            {descuento_html}
                        </td>
                    </tr>
                    """
                )

            # -------------------------------------------------
            # Envío
            # -------------------------------------------------

            importe_envio = numero(
                encabezado.get(
                    "importe_envio"
                )
            )

            fila_envio = ""

            if importe_envio > 0:
                fila_envio = f"""
                    <tr class="envio">
                        <td>
                            Envío
                        </td>

                        <td class="numero cantidad">
                            1
                        </td>

                        <td class="centro">
                        </td>

                        <td class="numero">
                            $
                            {
                                formato_decimal(
                                    importe_envio,
                                    decimales=2,
                                )
                            }
                        </td>

                        <td class="numero">
                            $
                            {
                                formato_decimal(
                                    importe_envio,
                                    decimales=2,
                                )
                            }
                        </td>
                    </tr>
                """

            total_pedido = (
                total_productos
                + importe_envio
            )

            # -------------------------------------------------
            # Observaciones
            # -------------------------------------------------

            observaciones = str(
                encabezado.get(
                    "observaciones_pedido"
                )
                or ""
            ).strip()

            bloque_observaciones = ""

            if observaciones:
                bloque_observaciones = f"""
                    <div class="observaciones">
                        <strong>
                            Observaciones:
                        </strong>

                        {
                            html.escape(
                                observaciones
                            )
                        }
                    </div>
                """

            # -------------------------------------------------
            # Bloque completo
            # -------------------------------------------------

            bloques_html.append(
                f"""
                <section class="pedido">

                    <div class="cabecera">
                        <div>
                            <strong>
                                {html.escape(str(encabezado["cliente"]))}
                            </strong>
                        </div>

                        <div>
                            Pedido {id_pedido}
                        </div>
                    </div>

                    <table class="detalle">
                        <thead>
                            <tr>
                                <th>
                                    Producto
                                </th>

                                <th class="numero">
                                    Cantidad
                                </th>

                                <th class="centro">
                                    Precio
                                </th>

                                <th class="numero">
                                    Precio unitario
                                </th>

                                <th class="numero">
                                    Precio total
                                </th>
                            </tr>
                        </thead>

                        <tbody>
                            {''.join(filas_productos)}
                            {fila_envio}
                        </tbody>
                    </table>

                    <div class="pie-pedido">
                        <div>
                            <strong>
                                Fecha entrega:
                            </strong>

                            {
                                fecha_texto(
                                    encabezado[
                                        "fecha_entrega"
                                    ]
                                )
                            }

                            {
                                (
                                    " - "
                                    + hora_texto(
                                        encabezado[
                                            "hora_entrega"
                                        ]
                                    )
                                )
                                if encabezado.get(
                                    "hora_entrega"
                                )
                                else ""
                            }
                        </div>

                        <div class="total-pedido">
                            <strong>
                                Total general:
                                $
                                {
                                    formato_decimal(
                                        total_pedido,
                                        decimales=2,
                                    )
                                }
                            </strong>
                        </div>
                    </div>

                    <div class="domicilio">
                        {ubicacion_texto}
                    </div>

                    <div class="contacto">
                        {contacto_texto}
                    </div>

                    {bloque_observaciones}

                </section>
                """
            )

        # =====================================================
        # Resumen general de carga
        # =====================================================

        filas_resumen: list[str] = []

        for producto in sorted(
            resumen_carga,
            key=str.casefold,
        ):
            cantidad = (
                resumen_carga[
                    producto
                ]
            )

            filas_resumen.append(
                f"""
                <tr>
                    <td>
                        {
                            html.escape(
                                producto
                            )
                        }
                    </td>

                    <td class="numero">
                        {
                            formato_cantidad(
                                cantidad
                            )
                        }
                    </td>
                </tr>
                """
            )

        resumen_html = f"""
            <section class="resumen-carga">
                <h1>
                    Resumen de carga
                </h1>

                <div class="periodo">
                    {
                        fecha_desde.strftime(
                            "%d/%m/%Y"
                        )
                    }
                    al
                    {
                        fecha_hasta.strftime(
                            "%d/%m/%Y"
                        )
                    }
                </div>

                <table class="detalle">
                    <thead>
                        <tr>
                            <th>
                                Producto
                            </th>

                            <th class="numero">
                                Cantidad
                            </th>
                        </tr>
                    </thead>

                    <tbody>
                        {
                            ''.join(
                                filas_resumen
                            )
                        }
                    </tbody>

                    <tfoot>
                        <tr>
                            <td>
                                <strong>
                                    Total general
                                </strong>
                            </td>

                            <td class="numero">
                                <strong>
                                    {
                                        formato_cantidad(
                                            total_carga
                                        )
                                    }
                                </strong>
                            </td>
                        </tr>
                    </tfoot>
                </table>
            </section>
        """

        # =====================================================
        # Documento
        # =====================================================

        contenido = f"""
        <!DOCTYPE html>

        <html lang="es">

        <head>
            <meta charset="utf-8">

            <title>
                Hoja de reparto
            </title>

            <style>

                @page {{
                    size: A4 portrait;
                    margin: 10mm;
                }}

                body {{
                    font-family:
                        Arial,
                        sans-serif;

                    color: #222;
                    margin: 0;
                    font-size: 11px;
                }}

                h1 {{
                    margin:
                        0
                        0
                        4px
                        0;

                    font-size: 20px;
                }}

                .titulo {{
                    margin-bottom: 12px;
                }}

                .periodo {{
                    color: #555;
                    margin-bottom: 14px;
                }}

                .pedido {{
                    border-bottom:
                        1px solid #777;

                    padding:
                        0
                        0
                        10px
                        0;

                    margin-bottom: 12px;

                    break-inside: avoid;
                }}

                .cabecera {{
                    display: flex;
                    justify-content:
                        space-between;

                    font-size: 14px;
                    margin-bottom: 5px;
                }}

                table.detalle {{
                    width: 100%;
                    border-collapse:
                        collapse;

                    margin-top: 5px;
                }}

                table.detalle th,
                table.detalle td {{
                    border:
                        1px solid #999;

                    padding: 5px;
                }}

                table.detalle th {{
                    background: #eeeeee;
                    text-align: left;
                }}

                .numero {{
                    text-align: right;
                    white-space: nowrap;
                }}

                .centro {{
                    text-align: center;
                }}

                .cantidad {{
                    width: 70px;
                }}

                .envio td {{
                    font-weight: bold;
                }}

                .descuento {{
                    font-size: 9px;
                    color: #666;
                    margin-top: 2px;
                }}

                .pie-pedido {{
                    display: flex;
                    justify-content:
                        space-between;

                    margin-top: 6px;
                }}

                .total-pedido {{
                    font-size: 12px;
                }}

                .domicilio {{
                    margin-top: 6px;
                }}

                .contacto {{
                    margin-top: 2px;
                }}

                .observaciones {{
                    margin-top: 4px;
                }}

                .resumen-carga {{
                    break-before: page;
                }}

                .resumen-carga table {{
                    margin-top: 10px;
                }}

                tfoot td {{
                    background: #f4f4f4;
                }}

            </style>

        </head>

        <body>

            <div class="titulo">
                <h1>
                    Hoja de reparto
                </h1>

                <div class="periodo">
                    {
                        fecha_desde.strftime(
                            "%d/%m/%Y"
                        )
                    }
                    al
                    {
                        fecha_hasta.strftime(
                            "%d/%m/%Y"
                        )
                    }
                </div>
            </div>

            {''.join(bloques_html)}

            {resumen_html}

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

        self._abrir_html(
            contenido,
            "hoja_reparto.html",
        )

    def _abrir_html(
        self,
        contenido: str,
        nombre_archivo: str,
    ) -> None:
        archivo = (
            Path(
                tempfile.gettempdir()
            )
            / nombre_archivo
        )

        archivo.write_text(
            contenido,
            encoding="utf-8",
        )

        webbrowser.open(
            archivo.as_uri()
        )