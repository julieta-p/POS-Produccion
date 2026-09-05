from __future__ import annotations

import tkinter as tk
from pathlib import Path
from datetime import date, datetime, timedelta
from decimal import Decimal
from tkinter import messagebox, simpledialog, ttk
from typing import Any
from ui.ventana_util import maximizar_ventana

from tkcalendar import DateEntry

from db.planificacion_repository import (
    asignar_stock,
)

from ui.pedido import (
    convertir_cantidad,
    convertir_decimal,
    formato_cantidad,
    formato_decimal,
)

from db.salida_repository import (
    cancelar_pedido,
    cancelar_saldo_pedido,
    confirmar_salida,
    confirmar_salida_multiple,
    crear_pedido_adicional,
    listar_detalle_pendiente,
    listar_pedidos_pendientes,
    reprogramar_saldo_pedido,
)
from ui.navegacion import aplicar_tema_ventana



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


class VentanaSalidaPedido(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        navegador=None,
    ) -> None:
        super().__init__(parent)

        self.navegador = navegador

        self._pedidos: dict[
            str,
            dict[str, Any],
        ] = {}

        self._detalle: dict[
            str,
            dict[str, Any],
        ] = {}

        self._cantidades: dict[
            int,
            Decimal,
        ] = {}

        self._adicionales_preparados: dict[
            int,
            dict[str, Any],
        ] = {}

        self._id_pedido_base_adicionales: int | None = None

        self._pedido_seleccionado: (
            dict[str, Any] | None
        ) = None

        self._ancho_pantalla = (
            self.winfo_screenwidth()
        )

        self._alto_pantalla = (
            self.winfo_screenheight()
        )

        self.title("Salidas y entregas")
        # self.transient(parent)
        self.resizable(True, True)
        maximizar_ventana(self)

        # self._ajustar_tamano_inicial()

        self._tema = getattr(self.navegador, "tema", "claro")

        self._crear_interfaz()
        self.after_idle(self._forzar_controles_tema)

        self._seleccionar_semana_actual(
            actualizar=False
        )

        self._actualizar_pedidos()
    def _forzar_controles_tema(self) -> None:
        """Aplica un aspecto controlado a los filtros de Por Entregar.

        Estos cuatro controles no deben quedar con el gris del tema nativo
        de Linux. Se fuerzan explícitamente a blanco/negro según el tema.
        """
        try:
            estilo = ttk.Style(self)
            # Clam permite controlar fieldbackground/foreground de forma
            # consistente en Linux Mint.
            try:
                estilo.theme_use("clam")
            except tk.TclError:
                pass

            oscuro = getattr(self.navegador, "tema", "claro") == "oscuro"
            fondo = "#000000" if oscuro else "#ffffff"
            texto = "#ffffff" if oscuro else "#000000"
            borde = "#ffffff" if oscuro else "#000000"
            seleccionado = "#333333" if oscuro else "#e6e6e6"

            estilo.configure(
                "SalidaFiltro.TEntry",
                foreground=texto,
                fieldbackground=fondo,
                background=fondo,
                insertcolor=texto,
                bordercolor=borde,
                lightcolor=borde,
                darkcolor=borde,
                padding=(7, 5),
            )
            estilo.map(
                "SalidaFiltro.TEntry",
                fieldbackground=[
                    ("disabled", fondo),
                    ("readonly", fondo),
                    ("focus", fondo),
                    ("active", fondo),
                    ("!disabled", fondo),
                ],
                foreground=[
                    ("disabled", texto),
                    ("readonly", texto),
                    ("focus", texto),
                    ("active", texto),
                    ("!disabled", texto),
                ],
                bordercolor=[("focus", borde), ("!focus", borde)],
            )

            estilo.configure(
                "SalidaFiltro.TCombobox",
                foreground=texto,
                fieldbackground=fondo,
                background=fondo,
                insertcolor=texto,
                bordercolor=borde,
                lightcolor=borde,
                darkcolor=borde,
                arrowcolor=texto,
                padding=(7, 5),
            )
            estilo.map(
                "SalidaFiltro.TCombobox",
                fieldbackground=[
                    ("disabled", fondo),
                    ("readonly", fondo),
                    ("focus", fondo),
                    ("active", fondo),
                    ("!disabled", fondo),
                ],
                background=[
                    ("disabled", fondo),
                    ("readonly", fondo),
                    ("focus", fondo),
                    ("active", fondo),
                    ("!disabled", fondo),
                ],
                foreground=[
                    ("disabled", texto),
                    ("readonly", texto),
                    ("focus", texto),
                    ("active", texto),
                    ("!disabled", texto),
                ],
                bordercolor=[("focus", borde), ("!focus", borde)],
            )

            self.txt_cliente.configure(style="SalidaFiltro.TEntry")
            self.cbo_modalidad.configure(style="SalidaFiltro.TCombobox")

            # DateEntry es ttk.Entry + calendario. Se estiliza el campo y,
            # además, se pasan las opciones propias de tkcalendar para que
            # tampoco conserve el gris del tema de Linux.
            for widget in (self.fecha_desde, self.fecha_hasta):
                try:
                    widget.configure(
                        style="SalidaFiltro.TEntry",
                        background=fondo,
                        foreground=texto,
                        bordercolor=borde,
                        selectbackground=seleccionado,
                        selectforeground=texto,
                        normalbackground=fondo,
                        normalforeground=texto,
                        headersbackground=fondo,
                        headersforeground=texto,
                        weekendbackground=fondo,
                        weekendforeground=texto,
                        othermonthbackground=fondo,
                        othermonthforeground=texto,
                    )
                except (tk.TclError, TypeError):
                    try:
                        widget.configure(style="SalidaFiltro.TEntry")
                    except tk.TclError:
                        pass

                # DateEntry expone internamente el Entry ttk; reforzamos el
                # estilo sobre ese objeto cuando está disponible.
                interno = getattr(widget, "_entry", None)
                if interno is not None:
                    try:
                        interno.configure(style="SalidaFiltro.TEntry")
                    except tk.TclError:
                        pass

        except tk.TclError:
            pass

    def _aplicar_tema_global(self, tema: str) -> None:
        """Hook llamado por el selector global al cambiar Claro/Oscuro."""
        self._forzar_controles_tema()

    def _ajustar_tamano_inicial(self) -> None:
        ancho = int(
            self._ancho_pantalla * 0.96
        )

        alto_disponible = max(
            self._alto_pantalla - 70,
            500,
        )

        alto = int(
            alto_disponible * 0.97
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
            850,
            ancho,
        )

        alto_minimo = min(
            560,
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

    def _colores(self) -> dict[str, str]:
        if self._tema == "oscuro":
            return {
                "bg": "#15171b",
                "surface": "#20242a",
                "surface2": "#292e35",
                "border": "#3b414a",
                "text": "#f3f4f6",
                "muted": "#aeb5bf",
                "sidebar": "#321019",
                "sidebar_hover": "#4a1723",
                "gold": "#d5a63a",
                "burgundy": "#bd3658",
            }
        return {
            "bg": "#f3f1ef",
            "surface": "#ffffff",
            "surface2": "#faf8f7",
            "border": "#ddd7d4",
            "text": "#252328",
            "muted": "#6d6870",
            "sidebar": "#3a111b",
            "sidebar_hover": "#511522",
            "gold": "#c99624",
            "burgundy": "#bd3658",
        }

    def _crear_interfaz(self) -> None:
        # Tipografía y filas más grandes para que la pantalla sea legible a simple vista.
        estilo = ttk.Style(self)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("Salida.TLabelFrame", padding=12)
        estilo.configure("Salida.TLabelFrame.Label", font=("Segoe UI", 11, "bold"))
        estilo.configure("Salida.TLabel", font=("Segoe UI", 10))
        estilo.configure("Salida.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 8))
        estilo.configure("Salida.Treeview", font=("Segoe UI", 10), rowheight=34)
        estilo.configure("Salida.Treeview.Heading", font=("Segoe UI", 10, "bold"), padding=(8, 9))

        raiz = tk.Frame(self, bg=self._colores()["bg"])
        raiz.pack(fill="both", expand=True)
        raiz.columnconfigure(1, weight=1)
        raiz.rowconfigure(0, weight=1)
        self._raiz = raiz

        self._crear_sidebar(raiz)

        contenido = tk.Frame(raiz, bg=self._colores()["bg"])
        contenido.grid(row=0, column=1, sticky="nsew", padx=(20, 20), pady=(12, 12))
        contenido.columnconfigure(0, weight=1)
        contenido.rowconfigure(2, weight=2)
        contenido.rowconfigure(4, weight=3)
        self._contenido = contenido

        encabezado = tk.Frame(contenido, bg=self._colores()["bg"])
        encabezado.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        encabezado.columnconfigure(0, weight=1)

        titulo_box = tk.Frame(encabezado, bg=self._colores()["bg"])
        titulo_box.grid(row=0, column=0, sticky="w")
        self.lbl_titulo = tk.Label(
            titulo_box, text="Salidas y Entregas",
            font=("Segoe UI", 25, "bold"),
            bg=self._colores()["bg"], fg=self._colores()["burgundy"], anchor="w"
        )
        self.lbl_titulo.pack(anchor="w")
        self.lbl_subtitulo = tk.Label(
            titulo_box,
            text="Prepará, controlá y confirmá las entregas de los pedidos.",
            font=("Segoe UI", 10),
            bg=self._colores()["bg"], fg=self._colores()["muted"], anchor="w"
        )
        self.lbl_subtitulo.pack(anchor="w", pady=(2, 0))

        self.btn_tema = tk.Button(
            encabezado, text="☾  Modo oscuro", command=self._alternar_tema,
            font=("Segoe UI", 9, "bold"), bd=0, relief="flat", padx=13, pady=7,
            cursor="hand2", highlightthickness=1
        )
        self.btn_tema.grid(row=0, column=1, sticky="e", padx=(15, 0))

        self._crear_filtros(contenido)
        self._crear_grilla_pedidos(contenido)
        self._crear_encabezado_salida(contenido)
        self._crear_grilla_detalle(contenido)
        self._crear_edicion_cantidad(contenido)
        self._crear_confirmacion(contenido)
        self._aplicar_tema()

    def _crear_sidebar(self, parent: tk.Misc) -> None:
        # Barra lateral con el mismo diseño de navegación de las demás pantallas.
        c = self._colores()
        sidebar = tk.Frame(parent, bg=c["sidebar"], width=255, bd=0, highlightthickness=0)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        self.sidebar = sidebar

        self._logo_img = None
        logo_box = tk.Frame(sidebar, bg="#fff9f9", bd=0, highlightthickness=0)
        logo_box.pack(fill="x", padx=14, pady=(16, 16))
        self.logo_box = logo_box
        ruta_logo = Path(__file__).resolve().parent.parent / "assets" / "logo_dona_elina.png"
        try:
            if ruta_logo.exists():
                self._logo_img = tk.PhotoImage(file=str(ruta_logo))
                if self._logo_img.width() > 215:
                    factor = max(1, self._logo_img.width() // 215)
                    self._logo_img = self._logo_img.subsample(factor, factor)
                self.logo_label = tk.Label(logo_box, image=self._logo_img, bg="#fff9f9", bd=0)
                self.logo_label.pack(padx=8, pady=8)
            else:
                self.logo_label = tk.Label(logo_box, text="Doña Elina", font=("Segoe Script", 24, "bold"),
                                           fg=c["burgundy"], bg="#fff9f9", bd=0)
                self.logo_label.pack(pady=25)
        except Exception:
            self.logo_label = tk.Label(logo_box, text="Doña Elina", font=("Segoe Script", 24, "bold"),
                                       fg=c["burgundy"], bg="#fff9f9", bd=0)
            self.logo_label.pack(pady=25)

        self._titulo_sidebar("ACCESOS RÁPIDOS")
        self._sidebar_button("＋", "Nuevo pedido", lambda: self.navegador.abrir_pedido(self))
        self._sidebar_button("☷", "Lista de precios", lambda: self.navegador.abrir_reporte_precios(self))
        self._sidebar_button("▰", "Salidas y Entregas", lambda: None, selected=True)
        self._sidebar_button("⚙", "Configuración", lambda: None)
        self._linea_sidebar()
        self._titulo_sidebar("MENÚ PRINCIPAL")
        self._sidebar_button("⌂", "Dashboard", lambda: self.navegador.volver_menu(self))
        self._sidebar_button("▣", "Caja", lambda: self.navegador.abrir_caja(self))
        self._sidebar_button("🛒", "Pedidos", lambda: self.navegador.abrir_pedidos(self))
        self._sidebar_button("▰", "Reparto", lambda: None)
        self._sidebar_button("▤", "Cobros", lambda: self.navegador.abrir_cobros(self))
        self._sidebar_button("▥", "Reportes", lambda: self.navegador.abrir_reporte_pedidos(self))
        self._sidebar_button("⚙", "Configuración", lambda: None)
        self._linea_sidebar()
        self._sidebar_button("⇥", "Salir", self._salir)

        self.sidebar_footer = tk.Label(
            sidebar, text="Doña Elina - Sistema de Gestión\nVersión 1.0.0",
            font=("Segoe UI", 8), bg=c["sidebar"], fg=c["gold"], justify="left"
        )
        self.sidebar_footer.pack(side="bottom", anchor="w", padx=22, pady=(0, 14))

    def _titulo_sidebar(self, texto: str) -> None:
        c = self._colores()
        etiqueta = tk.Label(
            self.sidebar, text=texto, font=("Segoe UI", 10, "bold"),
            bg=c["sidebar"], fg=c["gold"], anchor="w"
        )
        etiqueta.pack(fill="x", padx=22, pady=(2, 7))
        if not hasattr(self, "_sidebar_labels"):
            self._sidebar_labels = []
        self._sidebar_labels.append(etiqueta)

    def _linea_sidebar(self) -> None:
        linea = tk.Frame(self.sidebar, bg=self._colores()["gold"], height=1)
        linea.pack(fill="x", padx=20, pady=(0, 10))
        if not hasattr(self, "_sidebar_lines"):
            self._sidebar_lines = []
        self._sidebar_lines.append(linea)

    def _sidebar_button(self, icono: str, texto: str, comando, selected: bool = False) -> None:
        c = self._colores()
        bg = c["sidebar_hover"] if selected else c["sidebar"]
        boton = tk.Button(
            self.sidebar, text=f"{icono}   {texto}", command=comando,
            font=("Segoe UI", 10, "bold"), anchor="w", bd=0, relief="flat",
            padx=18, pady=9, cursor="hand2", bg=bg, fg="#ffffff",
            activebackground=c["sidebar_hover"], activeforeground="#ffffff",
            highlightthickness=1 if selected else 0,
            highlightbackground=c["burgundy"] if selected else c["sidebar"],
            highlightcolor=c["gold"],
        )
        boton.pack(fill="x", padx=12, pady=2)

        def entrar(_e):
            if not selected:
                boton.configure(bg=self._colores()["sidebar_hover"])
        def salir(_e):
            if not selected:
                boton.configure(bg=self._colores()["sidebar"])
        boton.bind("<Enter>", entrar)
        boton.bind("<Leave>", salir)

        if not hasattr(self, "_sidebar_buttons"):
            self._sidebar_buttons = []
        self._sidebar_buttons.append((boton, selected))

    def _alternar_tema(self) -> None:
        self._tema = "oscuro" if self._tema == "claro" else "claro"
        if self.navegador is not None:
            self.navegador.tema = self._tema
        self._aplicar_tema()

    def _aplicar_tema(self) -> None:
        c = self._colores()
        try:
            self.configure(bg=c["bg"])
            self._raiz.configure(bg=c["bg"])
            self._contenido.configure(bg=c["bg"])
            self.btn_tema.configure(
                text="☀  Modo claro" if self._tema == "oscuro" else "☾  Modo oscuro",
                bg=c["sidebar_hover"] if self._tema == "oscuro" else c["surface"],
                fg="#ffffff" if self._tema == "oscuro" else c["text"],
                activebackground=c["surface2"], activeforeground=c["text"],
                highlightbackground=c["border"],
            )
            self.lbl_titulo.configure(bg=c["bg"], fg=c["burgundy"])
            self.lbl_subtitulo.configure(bg=c["bg"], fg=c["muted"])
            self.sidebar.configure(bg=c["sidebar"])
            self.logo_box.configure(bg="#fff9f9")
            self.logo_label.configure(bg="#fff9f9")
            self.sidebar_footer.configure(bg=c["sidebar"], fg=c["gold"])
            for etiqueta in getattr(self, "_sidebar_labels", []):
                etiqueta.configure(bg=c["sidebar"], fg=c["gold"])
            for linea in getattr(self, "_sidebar_lines", []):
                linea.configure(bg=c["gold"])
            for boton, selected in getattr(self, "_sidebar_buttons", []):
                boton.configure(
                    bg=c["sidebar_hover"] if selected else c["sidebar"],
                    fg="#ffffff", activebackground=c["sidebar_hover"], activeforeground="#ffffff",
                    highlightbackground=c["burgundy"] if selected else c["sidebar"],
                )
            aplicar_tema_ventana(self, self._tema)
            self._forzar_controles_tema()
        except tk.TclError:
            pass

    def _salir(self) -> None:
        try:
            self.destroy()
        except tk.TclError:
            pass

    def _crear_filtros(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Pedidos pendientes",
            padding=12,
            style="Salida.TLabelFrame",
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
            weight=0,
        )
        campos.columnconfigure(
            3,
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
            style="SalidaFiltro.TEntry",
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
            style="SalidaFiltro.TEntry",
        )
        self.fecha_hasta.grid(
            row=1,
            column=1,
            padx=(0, 8),
            sticky="w",
        )

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
            state="readonly",
            width=14,
            style="SalidaFiltro.TCombobox",
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
        self.cbo_modalidad.set("TODAS")

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
            style="SalidaFiltro.TEntry",
        )
        self.txt_cliente.grid(
            row=1,
            column=3,
            sticky="ew",
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
            style="Salida.TButton",
            text="Semana actual",
            command=self._seleccionar_semana_actual,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            acciones,
            style="Salida.TButton",
            text="Actualizar",
            command=self._actualizar_pedidos,
        ).pack(
            side="left",
        )

        self.txt_cliente.bind(
            "<Return>",
            lambda _evento:
                self._actualizar_pedidos(),
        )

    def _crear_grilla_pedidos(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Pedidos",
            padding=12,
            style="Salida.TLabelFrame",
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
            "pedido",
            "entrega",
            "hora",
            "modalidad",
            "cliente",
            "estado",
            "productos",
            "pendiente",
        )

        self.grilla_pedidos = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
            height=8,
            style="Salida.Treeview",
        )

        titulos = {
            "pedido": "Pedido",
            "entrega": "Entrega",
            "hora": "Hora",
            "modalidad": "Modalidad",
            "cliente": "Cliente",
            "estado": "Estado",
            "productos": "Productos",
            "pendiente": "Cantidad pendiente",
        }

        anchos = {
            "pedido": 70,
            "entrega": 95,
            "hora": 65,
            "modalidad": 100,
            "cliente": 260,
            "estado": 125,
            "productos": 85,
            "pendiente": 125,
        }

        for columna in columnas:
            self.grilla_pedidos.heading(
                columna,
                text=titulos[columna],
            )

            self.grilla_pedidos.column(
                columna,
                width=anchos[columna],
                minwidth=(
                    160
                    if columna == "cliente"
                    else 65
                ),
                anchor=(
                    "w"
                    if columna == "cliente"
                    else "center"
                ),
                stretch=(
                    columna == "cliente"
                ),
            )

        barra_vertical = ttk.Scrollbar(
            marco,
            orient="vertical",
            command=self.grilla_pedidos.yview,
        )

        barra_horizontal = ttk.Scrollbar(
            marco,
            orient="horizontal",
            command=self.grilla_pedidos.xview,
        )

        self.grilla_pedidos.configure(
            yscrollcommand=barra_vertical.set,
            xscrollcommand=barra_horizontal.set,
        )

        self.grilla_pedidos.grid(
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

        self.grilla_pedidos.bind(
            "<<TreeviewSelect>>",
            self._seleccionar_pedido,
        )

    def _crear_encabezado_salida(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Salida seleccionada",
            padding=12,
            style="Salida.TLabelFrame",
        )
        marco.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(0, 8),
    )

        self.texto_pedido = tk.StringVar(
            value="Seleccione un pedido."
        )

        self.texto_tipo_salida = tk.StringVar(
            value=""
        )

        ttk.Label(
            marco,
            textvariable=self.texto_pedido,
            font=("Segoe UI", 10, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        ttk.Label(
            marco,
            text="Tipo de salida:",
        ).grid(
            row=0,
            column=1,
            padx=(30, 6),
        )

        ttk.Label(
            marco,
            textvariable=self.texto_tipo_salida,
            font=("Segoe UI", 11, "bold"),
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )
        marco.columnconfigure(
            0,
            weight=1,
        )

    def _crear_grilla_detalle(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Productos del pedido",
            padding=12,
            style="Salida.TLabelFrame",
        )
        marco.grid(
            row=4,
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
            "producto",
            "pedido",
            "cancelado",
            "entregado",
            "pendiente",
            "entregar",
        )

        self.grilla_detalle = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
            height=8,
            style="Salida.Treeview",
        )

        titulos = {
            "producto": "Producto",
            "pedido": "Pedido",
            "cancelado": "Cancelado",
            "entregado": "Ya entregado",
            "pendiente": "Pendiente",
            "entregar": "Entregar ahora",
        }

        for columna, titulo in titulos.items():
            self.grilla_detalle.heading(
                columna,
                text=titulo,
            )

        self.grilla_detalle.column(
            "producto",
            width=380,
            minwidth=180,
            anchor="w",
            stretch=True,
        )

        for columna in (
            "pedido",
            "cancelado",
            "entregado",
            "pendiente",
            "entregar",
        ):
            self.grilla_detalle.column(
                columna,
                width=110,
                minwidth=85,
                anchor="e",
                stretch=False,
            )

        barra_vertical = ttk.Scrollbar(
            marco,
            orient="vertical",
            command=self.grilla_detalle.yview,
        )

        barra_horizontal = ttk.Scrollbar(
            marco,
            orient="horizontal",
            command=self.grilla_detalle.xview,
        )

        self.grilla_detalle.configure(
            yscrollcommand=barra_vertical.set,
            xscrollcommand=barra_horizontal.set,
        )

        self.grilla_detalle.grid(
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

        self.grilla_detalle.bind(
            "<<TreeviewSelect>>",
            self._seleccionar_detalle,
        )

        self.grilla_detalle.bind(
            "<Double-1>",
            self._seleccionar_detalle,
        )

    def _crear_edicion_cantidad(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Cantidad a entregar",
            padding=12,
            style="Salida.TLabelFrame",
        )
        marco.grid(
            row=5,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        marco.columnconfigure(
            1,
            weight=1,
        )

        ttk.Label(
            marco,
            text="Producto seleccionado",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.txt_cantidad = ttk.Entry(
            marco,
            justify="right",
        )
        self.txt_cantidad.grid(
            row=1,
            column=0,
            padx=(0, 8),
            sticky="ew",
        )

        acciones = ttk.Frame(marco)
        acciones.grid(
            row=1,
            column=1,
            sticky="e",
        )

        ttk.Button(
            acciones,
            style="Salida.TButton",
            text="Aplicar cantidad",
            command=self._aplicar_cantidad,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            acciones,
            style="Salida.TButton",
            text="Todo pendiente",
            command=self._cargar_todo_pendiente,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            acciones,
            style="Salida.TButton",
            text="Limpiar cantidades",
            command=self._limpiar_cantidades,
        ).pack(
            side="left",
        )

        self.txt_cantidad.bind(
            "<Return>",
            lambda _evento:
                self._aplicar_cantidad(),
        )

    def _crear_confirmacion(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Confirmación",
            padding=12,
            style="Salida.TLabelFrame",
        )
        marco.grid(
            row=6,
            column=0,
            sticky="ew",
        )

        marco.columnconfigure(
            0,
            weight=1,
        )

        ttk.Label(
            marco,
            text="Observaciones",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.txt_observaciones = ttk.Entry(
            marco,
        )
        self.txt_observaciones.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        acciones = ttk.Frame(
            marco,
        )
        acciones.grid(
            row=2,
            column=0,
            sticky="e",
            pady=(10, 0),
        )

        self.btn_cancelar = ttk.Button(
            acciones,
            style="Salida.TButton",
            text="Cancelar pedido",
            command=self._cancelar_pedido,
            state="disabled",
        )
        self.btn_cancelar.pack(
            side="left",
            padx=(0, 8)
        )

        self.btn_reprogramar_saldo = ttk.Button(
            acciones,
            style="Salida.TButton",
            text="Reprogramar saldo",
            command=self._reprogramar_saldo_pendiente,
            state="disabled",
        )
        self.btn_reprogramar_saldo.pack(
            side="left",
            padx=(0,16),
        )

        self.btn_cancelar_saldo = ttk.Button(
            acciones,
            style="Salida.TButton",
            text="Cancelar saldo",
            command=self._cancelar_saldo_pendiente,
            state="disabled",
        )
        self.btn_cancelar_saldo.pack(
            side="left",
            padx=(0,8),
        )

        self.btn_confirmar = ttk.Button(
            acciones,
            style="Salida.TButton",
            text="Confirmar entrega",
            command=self._confirmar_salida,
            state="disabled",
        )
        self.btn_confirmar.pack(
            side="left",
            
        )
           
    

    def _sincronizar_fecha_hasta(
        self,
        _evento=None,
    ) -> None:
        self.fecha_hasta.set_date(
            self.fecha_desde.get_date()
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
            self._actualizar_pedidos()

    def _actualizar_pedidos(
        self,
        *,
        conservar_id: int | None = None,
    ) -> None:
        fecha_desde = self.fecha_desde.get_date()
        fecha_hasta = self.fecha_hasta.get_date()

        if fecha_desde > fecha_hasta:
            messagebox.showwarning(
                "Salidas y entregas",
                "La fecha desde no puede ser posterior "
                "a la fecha hasta.",
                parent=self,
            )
            return

        modalidad = self.cbo_modalidad.get()

        if modalidad == "TODAS":
            modalidad = None

        cliente = (
            self.txt_cliente.get().strip()
            or None
        )

        try:
            filas = listar_pedidos_pendientes(
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                modalidad=modalidad,
                cliente=cliente,
            )

        except Exception as error:
            messagebox.showerror(
                "Salidas y entregas",
                "No se pudieron recuperar los pedidos."
                f"\n\n{error}",
                parent=self,
            )
            return

        self._pedidos.clear()

        for item in self.grilla_pedidos.get_children():
            self.grilla_pedidos.delete(item)

        item_a_seleccionar = None

        for indice, fila in enumerate(filas):
            iid = f"pedido-{fila['id_pedido']}-{indice}"

            self._pedidos[iid] = fila

            self.grilla_pedidos.insert(
                "",
                "end",
                iid=iid,
                values=(
                    fila["id_pedido"],
                    fecha_texto(
                        fila["fecha_entrega"]
                    ),
                    hora_texto(
                        fila["hora_entrega"]
                    ),
                    fila["modalidad_entrega"],
                    fila["cliente"],
                    fila["estado_pedido"],
                    fila["cantidad_productos"],
                    formato_cantidad(numero(
                            fila[
                                "cantidad_total_pendiente"
                            ]
                        )),
                ),
            )

            if (
                conservar_id is not None
                and int(fila["id_pedido"])
                == conservar_id
            ):
                item_a_seleccionar = iid

        if item_a_seleccionar:
            self.grilla_pedidos.selection_set(
                item_a_seleccionar
            )
            self.grilla_pedidos.focus(
                item_a_seleccionar
            )
            self.grilla_pedidos.see(
                item_a_seleccionar
            )
            self._seleccionar_pedido()

        else:
            self._limpiar_pedido()

    def _seleccionar_pedido(
        self,
        _evento=None,
    ) -> None:
        seleccion = (
            self.grilla_pedidos.selection()
        )

        if not seleccion:
            self._limpiar_pedido()
            return

        iid = seleccion[0]

        pedido = self._pedidos.get(iid)

        if pedido is None:
            messagebox.showerror(
                "Salidas y entregas",
                "No se encontró internamente el pedido "
                "seleccionado.",
                parent=self,
            )
            self._limpiar_pedido()
            return

        self._pedido_seleccionado = pedido

        id_pedido = int(
            pedido["id_pedido"]
        )

        modalidad = str(
            pedido["modalidad_entrega"]
        ).upper()

        tipo_salida = (
            "ENTREGADO"
            if modalidad == "MOSTRADOR"
            else "LLEVAR"
        )

        self.texto_pedido.set(
            f"Pedido {id_pedido} · "
            f"{pedido['cliente']} · "
            "Entrega "
            f"{fecha_texto(pedido['fecha_entrega'])}"
        )

        self.texto_tipo_salida.set(
            tipo_salida
        )

        self.txt_observaciones.delete(
            0,
            "end",
        )

        # Cancelar no depende de que el detalle
        # pueda recuperarse correctamente.
        estado_pedido = str(
            pedido["estado_pedido"]
        ).upper()

        if estado_pedido == "SALIDA_PARCIAL":
            # Ya existió una entrega:
            # no puede cancelarse el pedido completo, 
            # pero sí el saldo pendiente.
            self.btn_cancelar.configure(
                state="disabled",
            )

            self.btn_cancelar_saldo.configure(
                state="normal",
            )

            self.btn_reprogramar_saldo.configure(
                state="normal",
            )

        else:
            # Todavía no hubo entregas:
            # puede cancelarse el pedido completo.
            self.btn_cancelar.configure(
                state="normal",
            )

            self.btn_cancelar_saldo.configure(
                state="disabled",
            )

            self.btn_reprogramar_saldo.configure(
                state="disabled",
            )
    

        detalle_cargado = self._cargar_detalle(
            id_pedido
        )

        texto_boton = (
            "Confirmar entrega"
            if tipo_salida == "ENTREGADO"
            else "Confirmar despacho"
        )

        self.btn_confirmar.configure(
            text=texto_boton,
            state=(
                "normal"
                if detalle_cargado
                else "disabled"
            ),
        )

    def _cargar_detalle(
        self,
        id_pedido: int,
    ) -> bool:
        self._detalle.clear()
        self._cantidades.clear()

        for item in self.grilla_detalle.get_children():
            self.grilla_detalle.delete(item)

        try:
            filas = listar_detalle_pendiente(
                id_pedido
            )

        except Exception as error:
            messagebox.showerror(
                "Salidas y entregas",
                "No se pudo recuperar el detalle."
                f"\n\n{error}",
                parent=self,
            )
            return False

        if not filas:
            messagebox.showwarning(
                "Salidas y entregas",
                (
                    f"El pedido {id_pedido} no tiene "
                    "productos pendientes para entregar."
                ),
                parent=self,
            )
            return False

        try:
            for fila in filas:
                id_detalle = int(
                    fila["id_pedido_detalle"]
                )

                self._cantidades[id_detalle] = (
                    Decimal("0")
                )

                iid = f"detalle-{id_detalle}"
                self._detalle[iid] = fila

            self._recargar_grilla_detalle()

        except Exception as error:
            messagebox.showerror(
                "Salidas y entregas",
                "Se recuperó el pedido, pero no se pudo "
                "mostrar su detalle."
                f"\n\n{error}",
                parent=self,
            )
            return False

        return True

    def _recargar_grilla_detalle(self) -> None:
        seleccion_anterior = (
            self.grilla_detalle.selection()
        )

        iid_anterior = (
            seleccion_anterior[0]
            if seleccion_anterior
            else None
        )

        for item in self.grilla_detalle.get_children():
            self.grilla_detalle.delete(item)

        for iid, fila in self._detalle.items():
            id_detalle = int(
                fila["id_pedido_detalle"]
            )

            self.grilla_detalle.insert(
                "",
                "end",
                iid=iid,
                values=(
                    fila["descripcion_producto"],
                    formato_cantidad(numero(fila["cantidad_pedida"])),
                    formato_cantidad(numero(
                            fila["cantidad_cancelada"]
                        )),
                    formato_cantidad(numero(
                            fila["cantidad_entregada"]
                        )),
                    formato_cantidad(numero(
                            fila["cantidad_pendiente"]
                        )),
                    formato_cantidad(self._cantidades.get(
                            id_detalle,
                            Decimal("0"),
                        )),
                ),
            )

        if (
            iid_anterior
            and iid_anterior
            in self._detalle
        ):
            self.grilla_detalle.selection_set(
                iid_anterior
            )

    def _seleccionar_detalle(
        self,
        _evento=None,
    ) -> None:
        seleccion = (
            self.grilla_detalle.selection()
        )

        if not seleccion:
            return

        fila = self._detalle[
            seleccion[0]
        ]

        self.txt_cantidad.delete(0, "end")

        self.txt_cantidad.focus_set()
        self.txt_cantidad.selection_range(
            0,
            "end",
        )

    def _aplicar_cantidad(self) -> None:
        seleccion = (
            self.grilla_detalle.selection()
        )

        if not seleccion:
            messagebox.showinfo(
                "Salidas y entregas",
                "Seleccione un producto.",
                parent=self,
            )
            return

        fila = self._detalle[
            seleccion[0]
        ]

        try:
            cantidad = convertir_cantidad(self.txt_cantidad.get())

        except Exception as error:
            messagebox.showwarning(
                "Salidas y entregas",
                f"Cantidad inválida.\n\n{error}",
                parent=self,
            )
            return

        pendiente = numero(
            fila["cantidad_pendiente"]
        )

        if cantidad < 0:
            messagebox.showwarning(
                "Salidas y entregas",
                "La cantidad no puede ser negativa.",
                parent=self,
            )
            return

        if cantidad > pendiente:
            adicional = cantidad - pendiente

            id_detalle = int(
                fila["id_pedido_detalle"]
            )

            id_pedido = int(
                self._pedido_seleccionado[
                    "id_pedido"
                ]
            )

            producto = str(
                fila["descripcion_producto"]
            )

            confirmar_adicional = messagebox.askyesno(
                "Cantidad mayor al pedido",
                (
                    f"Pedido: {id_pedido}\n"
                    f"Producto: {producto}\n\n"
                    "Cantidad pendiente del pedido: "
                    f"{formato_cantidad(pendiente)}\n"
                    "Cantidad ingresada: "
                    f"{formato_cantidad(cantidad)}\n\n"
                    "La cantidad ingresada supera lo solicitado "
                    "originalmente en "
                    f"{formato_cantidad(adicional)}.\n\n"
                    "¿El cliente realmente necesita esa cantidad "
                    "adicional?\n\n"
                    "Si continúa, se creará un pedido nuevo por "
                    f"{formato_cantidad(adicional)}."
                ),
                parent=self,
            )

            if not confirmar_adicional:
                self.txt_cantidad.focus_set()
                self.txt_cantidad.selection_range(
                    0,
                    "end",
                )
                return

            try:
                resultado_adicional = (
                    crear_pedido_adicional(
                        id_pedido_origen=id_pedido,
                        id_pedido_detalle_origen=id_detalle,
                        cantidad_adicional=adicional,
                        observaciones=(
                            "Cantidad adicional confirmada "
                            "desde Salidas y entregas."
                        ),
                    )
                )

            except Exception as error:
                messagebox.showerror(
                    "Crear pedido adicional",
                    (
                        "No se pudo crear el pedido adicional."
                        f"\n\n{error}"
                    ),
                    parent=self,
                )
                return

            id_pedido_nuevo = int(
                resultado_adicional[
                    "id_pedido_destino"
                ]
            )

            id_detalle_nuevo = int(
                resultado_adicional[
                    "id_pedido_detalle_destino"
                ]
            )

            # El pedido original jamás entrega más
            # que su cantidad pendiente.
            self._cantidades[id_detalle] = pendiente

            self._recargar_grilla_detalle()

            self.txt_cantidad.delete(
                0,
                "end",
            )

            self.txt_cantidad.insert(
                0,
                formato_cantidad(pendiente),
            )

            usar_stock = messagebox.askyesno(
                "Pedido adicional creado",
                (
                    f"Se creó el pedido adicional "
                    f"{id_pedido_nuevo} por "
                    f"{formato_cantidad(adicional)} "
                    f"de {producto}.\n\n"
                    "El pedido original continuará con "
                    f"{formato_cantidad(pendiente)} "
                    "como máximo a entregar.\n\n"
                    "¿Desea intentar cubrir ahora el pedido "
                    "adicional con stock disponible?"
                ),
                parent=self,
            )

            if not usar_stock:
                messagebox.showinfo(
                    "Pedido adicional",
                    (
                        f"Pedido adicional {id_pedido_nuevo} "
                        "creado correctamente.\n\n"
                        "Quedará pendiente para su planificación."
                    ),
                    parent=self,
                )
                return

            try:
                asignar_stock(
                    id_pedido_detalle=id_detalle_nuevo,
                    cantidad_desde_stock=adicional,
                )

            except Exception as error:
                texto_error = str(error)

                if (
                    "50806" in texto_error
                    or
                    "Stock insuficiente para realizar la reserva"
                    in texto_error
                ):
                    ir_planificacion = messagebox.askyesno(
                        "Stock insuficiente",
                        (
                            f"El pedido adicional {id_pedido_nuevo} "
                            "fue creado correctamente.\n\n"
                            f"Producto: {producto}\n"
                            "Cantidad adicional: "
                            f"{formato_cantidad(adicional)}\n\n"
                            "No hay stock disponible suficiente "
                            "para entregarlo ahora.\n\n"
                            "El pedido quedó pendiente y deberá "
                            "ingresar al circuito de producción "
                            "antes de su entrega.\n\n"
                            "¿Desea ir a Planificación ahora?"
                        ),
                        parent=self,
                    )

                    if (
                        ir_planificacion
                        and self.navegador is not None
                    ):
                        self.navegador.abrir_planificacion(
                            self,
                            id_pedido=id_pedido_nuevo,
                        )

                    return

                messagebox.showerror(
                    "Pedido adicional",
                    (
                        f"El pedido adicional {id_pedido_nuevo} "
                        "se creó correctamente, pero ocurrió un error "
                        "al intentar reservar stock."
                        f"\n\nDetalle técnico:\n{error}"
                    ),
                    parent=self,
                )
                return


            if (
                self._id_pedido_base_adicionales
                != id_pedido
            ):
                self._adicionales_preparados.clear()

                self._id_pedido_base_adicionales = (
                    id_pedido
                )


            self._adicionales_preparados[
                id_pedido_nuevo
            ] = {
                "id_pedido":
                    id_pedido_nuevo,

                "id_pedido_detalle":
                    id_detalle_nuevo,

                "cantidad":
                    adicional,

                "producto":
                    producto,
            }


            messagebox.showinfo(
                "Pedido adicional preparado",
                (
                    f"Pedido adicional {id_pedido_nuevo} "
                    "creado correctamente.\n\n"
                    f"Se asignaron "
                    f"{formato_cantidad(adicional)} "
                    f"de {producto} desde stock.\n\n"
                    "El pedido adicional se entregará junto "
                    "con el pedido original al presionar "
                    "Confirmar entrega."
                ),
                parent=self,
            )

            return

        id_detalle = int(
            fila["id_pedido_detalle"]
        )

        self._cantidades[id_detalle] = cantidad
        self._recargar_grilla_detalle()

    def _cargar_todo_pendiente(self) -> None:
        for fila in self._detalle.values():
            id_detalle = int(
                fila["id_pedido_detalle"]
            )

            self._cantidades[id_detalle] = numero(
                fila["cantidad_pendiente"]
            )

        self._recargar_grilla_detalle()

    def _limpiar_cantidades(self) -> None:
        for id_detalle in self._cantidades:
            self._cantidades[id_detalle] = (
                Decimal("0")
            )

        self._recargar_grilla_detalle()

    def _elegir_destino_saldo(
        self,
        saldo_total: Decimal,
    ) -> tuple[str | None, str | None]:
        decision = messagebox.askyesnocancel(
            "Saldo pendiente del pedido",
            (
                "La entrega es menor que la cantidad pendiente."
                "\n\n"
                "Saldo restante: "
                f"{formato_cantidad(saldo_total)}"
                "\n\n"
                "¿Qué desea hacer con esa cantidad?"
                "\n\n"
                "Sí: cancelar el saldo."
                "\n"
                "No: dejarlo pendiente."
                "\n"
                "Cancelar: volver sin confirmar la entrega."
            ),
            parent=self,
        )

        # Cerró la ventana o eligió Cancelar.
        if decision is None:
            return None, None

        # Eligió No: el saldo continúa pendiente.
        if decision is False:
            return "PENDIENTE", None

        # Eligió Sí: cancelar definitivamente el saldo.
        motivo = simpledialog.askstring(
            "Cancelar saldo de pedido",
            (
                "Indique el motivo por el cual el cliente "
                "no retirará el saldo restante:"
            ),
            parent=self,
        )

        if motivo is None:
            return None, None

        motivo = motivo.strip()

        if not motivo:
            messagebox.showwarning(
                "Cancelar saldo",
                "Debe indicar el motivo de la cancelación.",
                parent=self,
            )
            return None, None

        return "CANCELAR", motivo

    
    def _confirmar_salida(self) -> None:
        if not self._pedido_seleccionado:
            return

        detalle_salida: list[
            dict[str, Any]
        ] = []

        cantidad_total = Decimal("0")
        saldo_total = Decimal("0")

        for fila in self._detalle.values():
            id_detalle = int(
                fila["id_pedido_detalle"]
            )

            pendiente = numero(
                fila["cantidad_pendiente"]
            )

            cantidad = self._cantidades.get(
                id_detalle,
                Decimal("0"),
            )

            saldo_linea = pendiente - cantidad

            if saldo_linea > 0:
                saldo_total += saldo_linea

            if cantidad > 0:
                detalle_salida.append(
                    {
                        "id_pedido_detalle":
                            id_detalle,

                        "cantidad":
                            cantidad,
                    }
                )

                cantidad_total += cantidad


        if not detalle_salida:
            messagebox.showwarning(
                "Salidas y entregas",
                "No hay cantidades para entregar.",
                parent=self,
            )
            return


        id_pedido = int(
            self._pedido_seleccionado[
                "id_pedido"
            ]
        )


        # Sólo usamos los adicionales que realmente
        # corresponden al pedido seleccionado.
        hay_adicionales = (
            bool(self._adicionales_preparados)
            and
            self._id_pedido_base_adicionales
            == id_pedido
        )


        cantidad_adicional_total = Decimal("0")

        if hay_adicionales:
            cantidad_adicional_total = sum(
                (
                    numero(
                        item["cantidad"]
                    )
                    for item
                    in self._adicionales_preparados.values()
                ),
                Decimal("0"),
            )


        cantidad_total_operacion = (
            cantidad_total
            + cantidad_adicional_total
        )


        destino_saldo = "PENDIENTE"
        motivo_saldo = None

        if saldo_total > 0:
            destino_saldo, motivo_saldo = (
                self._elegir_destino_saldo(
                    saldo_total
                )
            )

            if destino_saldo is None:
                return


        modalidad = str(
            self._pedido_seleccionado[
                "modalidad_entrega"
            ]
        ).upper()

        tipo_salida = (
            "ENTREGADO"
            if modalidad == "MOSTRADOR"
            else "LLEVAR"
        )


        if saldo_total <= 0:
            texto_saldo = (
                "Se entregará todo lo pendiente."
            )

        elif destino_saldo == "CANCELAR":
            texto_saldo = (
                "Saldo a cancelar: "
                f"{formato_cantidad(saldo_total)}"
                "\n"
                f"Motivo: {motivo_saldo}"
            )

        else:
            texto_saldo = (
                "Saldo que quedará pendiente: "
                f"{formato_cantidad(saldo_total)}"
            )


        texto_adicionales = ""

        if hay_adicionales:
            lineas = []

            for adicional in (
                self._adicionales_preparados.values()
            ):
                lineas.append(
                    "Pedido adicional "
                    f"{adicional['id_pedido']}: "
                    f"{formato_cantidad(adicional['cantidad'])} "
                    f"de {adicional['producto']}"
                )

            texto_adicionales = (
                "\n\n"
                + "\n".join(lineas)
                + "\n\n"
                "Cantidad total de la operación: "
                f"{formato_cantidad(cantidad_total_operacion)}"
            )


        confirmar = messagebox.askyesno(
            "Confirmar salida",
            (
                f"Pedido original: {id_pedido}\n"
                f"Tipo: {tipo_salida}\n"
                "Cantidad del pedido original: "
                f"{formato_cantidad(cantidad_total)}"
                f"{texto_adicionales}"
                "\n\n"
                f"{texto_saldo}"
                "\n\n"
                "¿Confirmar la operación?"
            ),
            parent=self,
        )

        if not confirmar:
            return


        try:
            if hay_adicionales:
                resultado_multiple = (
                    confirmar_salida_multiple(
                        id_pedido=id_pedido,
                        tipo_salida=tipo_salida,
                        detalle=detalle_salida,

                        pedidos_adicionales=list(
                            self._adicionales_preparados.keys()
                        ),

                        observaciones=(
                            self.txt_observaciones
                            .get()
                            .strip()
                            or None
                        ),

                        destino_saldo=destino_saldo,
                        motivo_saldo=motivo_saldo,
                    )
                )

                salidas_confirmadas = (
                    resultado_multiple["salidas"]
                )

                resumen = (
                    resultado_multiple["resumen"]
                )

            else:
                resultado = confirmar_salida(
                    id_pedido=id_pedido,
                    tipo_salida=tipo_salida,
                    detalle=detalle_salida,

                    observaciones=(
                        self.txt_observaciones
                        .get()
                        .strip()
                        or None
                    ),

                    destino_saldo=destino_saldo,
                    motivo_saldo=motivo_saldo,
                )

                salidas_confirmadas = [
                    resultado
                ]

                resumen = {
                    "cantidad_pedidos":
                        1,

                    "cantidad_ventas":
                        1,

                    "total_ventas":
                        resultado.get(
                            "total",
                            0,
                        ),
                }

        except Exception as error:
            messagebox.showerror(
                "Salidas y entregas",
                "No se pudo confirmar la salida."
                f"\n\n{error}",
                parent=self,
            )
            return


        # ---------------------------------------------------------
        # A partir de acá SQL confirmó correctamente TODA
        # la operación.
        # ---------------------------------------------------------

        ids_adicionales_entregados = (
            list(
                self._adicionales_preparados.keys()
            )
            if hay_adicionales
            else []
        )


        ventas = [
            str(item["id_venta"])
            for item in salidas_confirmadas
            if item.get("id_venta") is not None
        ]


        # Esta es la venta que usamos para abrir Cobros.
        # En una entrega múltiple será normalmente la del
        # pedido original. Cobros recuperará además las demás
        # ventas pendientes del mismo cliente.
        id_venta_cobros = next(
            (
                int(item["id_venta"])
                for item in salidas_confirmadas
                if item.get("id_venta") is not None
            ),
            None,
        )


        total_ventas = numero(
            resumen.get("total_ventas")
        )


        cantidad_cancelada = sum(
            (
                numero(
                    item.get(
                        "cantidad_saldo_cancelada"
                    )
                )
                for item
                in salidas_confirmadas
            ),
            Decimal("0"),
        )


        mensaje = (
            "Entrega registrada correctamente.\n\n"
            f"Pedido original: {id_pedido}\n"
        )


        if ids_adicionales_entregados:
            mensaje += (
                "Pedidos adicionales: "
                + ", ".join(
                    str(id_adicional)
                    for id_adicional
                    in ids_adicionales_entregados
                )
                + "\n"
            )


        mensaje += (
            "Cantidad total entregada: "
            f"{formato_cantidad(cantidad_total_operacion)}"
            "\n"
            "Ventas generadas: "
            + ", ".join(ventas)
            + "\n"
            "Total ventas: $"
            f"{formato_decimal(total_ventas, decimales=2)}"
        )


        if cantidad_cancelada > 0:
            mensaje += (
                "\n"
                "Saldo cancelado: "
                f"{formato_cantidad(cantidad_cancelada)}"
            )

        elif saldo_total > 0:
            mensaje += (
                "\n"
                "Saldo pendiente: "
                f"{formato_cantidad(saldo_total)}"
            )


        # ---------------------------------------------------------
        # ACÁ van los dos clear().
        #
        # La operación ya fue confirmada por SQL.
        # Guardamos antes los IDs en
        # ids_adicionales_entregados para poder mostrarlos.
        # ---------------------------------------------------------

        self._adicionales_preparados.clear()
        self._id_pedido_base_adicionales = None


        ir_a_cobros = messagebox.askyesno(
            "Salida confirmada",
            (
                mensaje
                + "\n\n"
                "La entrega se registró correctamente."
                "\n\n"
                "¿Desea ir a Cobros?"
            ),
            parent=self,
        )


        if (
            ir_a_cobros
            and self.navegador is not None
            and id_venta_cobros is not None
        ):
            self.navegador.abrir_cobros(
                self,

                id_cliente=int(
                    self._pedido_seleccionado[
                        "id_cliente"
                    ]
                ),

                id_venta=id_venta_cobros,
            )
            return


        self._actualizar_pedidos(
            conservar_id=id_pedido
        )
    
    def _pedir_datos_reprogramacion(
        self,
        pedido: dict[str, Any],
    ) -> dict[str, Any] | None:
        ventana = tk.Toplevel(self)
        ventana.title("Reprogramar saldo pendiente")
        ventana.transient(self)
        ventana.resizable(False, False)

        resultado: dict[str, Any] = {
            "datos": None,
        }

        marco = ttk.Frame(
            ventana,
            padding=16,
        )
        marco.pack(
            fill="both",
            expand=True,
        )

        marco.columnconfigure(
            1,
            weight=1,
        )

        id_pedido = int(
            pedido["id_pedido"]
        )

        cliente = str(
            pedido["cliente"]
        )

        saldo = numero(
            pedido["cantidad_total_pendiente"]
        )

        fecha_original = pedido["fecha_entrega"]

        fecha_inicial = max(
            date.today(),
            fecha_original + timedelta(days=1),
        )

        modalidad = str(
            pedido["modalidad_entrega"]
        ).upper()

        ttk.Label(
            marco,
            text=f"Pedido {id_pedido}",
            font=("Segoe UI", 12, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 4),
        )

        ttk.Label(
            marco,
            text=(
                f"{cliente} · "
                "Saldo a reprogramar: "
                f"{formato_cantidad(saldo)}"
            ),
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 14),
        )

        # ---------------------------------------------------------
        # Nueva fecha de entrega
        # ---------------------------------------------------------

        ttk.Label(
            marco,
            text="Nueva fecha de entrega",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=4,
        )

        fecha_entrega = DateEntry(
            marco,
            date_pattern="dd/mm/yyyy",
            locale="es_AR",
            firstweekday="monday",
        )
        fecha_entrega.grid(
            row=2,
            column=1,
            sticky="ew",
            pady=4,
        )

        fecha_entrega.set_date(
            fecha_inicial
        )

        # ---------------------------------------------------------
        # Hora
        # ---------------------------------------------------------

        ttk.Label(
            marco,
            text="Hora de entrega",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=4,
        )

        hora_var = tk.StringVar(
            value=(
                hora_texto(
                    pedido.get("hora_entrega")
                )
                or "12:00"
            )
        )

        txt_hora = ttk.Entry(
            marco,
            textvariable=hora_var,
            width=10,
        )
        txt_hora.grid(
            row=3,
            column=1,
            sticky="w",
            pady=4,
        )

        # ---------------------------------------------------------
        # Fecha de elaboración opcional
        # ---------------------------------------------------------

        fecha_manual_var = tk.BooleanVar(
            value=False
        )

        chk_fecha_manual = ttk.Checkbutton(
            marco,
            text="Definir manualmente la fecha de elaboración",
            variable=fecha_manual_var,
        )
        chk_fecha_manual.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 4),
        )

        ttk.Label(
            marco,
            text="Fecha de elaboración",
        ).grid(
            row=5,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=4,
        )

        fecha_elaboracion = DateEntry(
            marco,
            date_pattern="dd/mm/yyyy",
            locale="es_AR",
            firstweekday="monday",
        )
        fecha_elaboracion.grid(
            row=5,
            column=1,
            sticky="ew",
            pady=4,
        )

        fecha_elaboracion.set_date(
            (
                fecha_inicial - timedelta(days=1)
                if modalidad == "REPARTO"
                else fecha_inicial
            )
        )

        # ---------------------------------------------------------
        # Envío
        # ---------------------------------------------------------

        ttk.Label(
            marco,
            text="Importe de envío",
        ).grid(
            row=6,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=4,
        )

        txt_envio = ttk.Entry(
            marco,
            justify="right",
        )
        txt_envio.grid(
            row=6,
            column=1,
            sticky="ew",
            pady=4,
        )
        txt_envio.insert(
            0,
            "0,00",
        )

        # ---------------------------------------------------------
        # Motivo
        # ---------------------------------------------------------

        ttk.Label(
            marco,
            text="Motivo",
        ).grid(
            row=7,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=4,
        )

        txt_motivo = ttk.Entry(
            marco,
            width=50,
        )
        txt_motivo.grid(
            row=7,
            column=1,
            sticky="ew",
            pady=4,
        )

        # ---------------------------------------------------------
        # Observaciones del pedido nuevo
        # ---------------------------------------------------------

        ttk.Label(
            marco,
            text="Observaciones",
        ).grid(
            row=8,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=4,
        )

        txt_observaciones = ttk.Entry(
            marco,
        )
        txt_observaciones.grid(
            row=8,
            column=1,
            sticky="ew",
            pady=4,
        )

        # ---------------------------------------------------------
        # Aceptar
        # ---------------------------------------------------------

        def aceptar() -> None:
            nueva_fecha = (
                fecha_entrega.get_date()
            )

            if nueva_fecha <= fecha_original:
                messagebox.showwarning(
                    "Reprogramar saldo pendiente",
                    (
                        "La nueva fecha de entrega debe ser "
                        "posterior a la fecha original."
                    ),
                    parent=ventana,
                )
                return

            texto_hora = (
                hora_var.get().strip()
            )

            hora_nueva = None

            if texto_hora:
                try:
                    hora_nueva = (
                        datetime.strptime(
                            texto_hora,
                            "%H:%M",
                        ).time()
                    )

                except ValueError:
                    messagebox.showwarning(
                        "Reprogramar saldo pendiente",
                        (
                            "La hora debe tener formato "
                            "HH:MM."
                        ),
                        parent=ventana,
                    )
                    return

            motivo = (
                txt_motivo.get().strip()
            )

            if not motivo:
                messagebox.showwarning(
                    "Reprogramar saldo pendiente",
                    "Debe indicar el motivo de la reprogramación.",
                    parent=ventana,
                )
                return

            try:
                importe_envio = convertir_decimal(
                    txt_envio.get(),
                    decimales=2,
                )

            except Exception as error:
                messagebox.showwarning(
                    "Reprogramar saldo pendiente",
                    f"Importe de envío inválido.\n\n{error}",
                    parent=ventana,
                )
                return

            if importe_envio < 0:
                messagebox.showwarning(
                    "Reprogramar saldo pendiente",
                    "El importe de envío no puede ser negativo.",
                    parent=ventana,
                )
                return

            fecha_elaboracion_nueva = None

            if fecha_manual_var.get():
                fecha_elaboracion_nueva = (
                    fecha_elaboracion.get_date()
                )

            resultado["datos"] = {
                "fecha_entrega_nueva":
                    nueva_fecha,

                "hora_entrega_nueva":
                    hora_nueva,

                "fecha_elaboracion_nueva":
                    fecha_elaboracion_nueva,

                "importe_envio_nuevo":
                    importe_envio,

                "motivo":
                    motivo,

                "observaciones_nuevo":
                    (
                        txt_observaciones
                        .get()
                        .strip()
                        or None
                    ),
            }

            ventana.destroy()

        acciones = ttk.Frame(
            marco,
        )
        acciones.grid(
            row=9,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(16, 0),
        )

        acciones.columnconfigure(
            0,
            weight=1,
        )
        acciones.columnconfigure(
            1,
            weight=1,
        )

        ttk.Button(
            acciones,
            text="Reprogramar",
            command=aceptar,
        ).grid(
            row=0,
            column=0,
            padx=(0, 5),
            sticky="ew",
        )

        ttk.Button(
            acciones,
            text="Volver",
            command=ventana.destroy,
        ).grid(
            row=0,
            column=1,
            padx=(5, 0),
            sticky="ew",
        )

        ventana.update_idletasks()

        ancho = ventana.winfo_reqwidth()
        alto = ventana.winfo_reqheight()

        x = (
            self.winfo_rootx()
            + (
                self.winfo_width()
                - ancho
            ) // 2
        )

        y = (
            self.winfo_rooty()
            + (
                self.winfo_height()
                - alto
            ) // 2
        )

        ventana.geometry(
            f"+{max(x, 0)}+{max(y, 0)}"
        )

        ventana.grab_set()
        ventana.wait_window()

        return resultado["datos"]

    def _reprogramar_saldo_pendiente(
        self,
    ) -> None:
        if not self._pedido_seleccionado:
            return

        pedido = self._pedido_seleccionado

        id_pedido = int(
            pedido["id_pedido"]
        )

        cliente = str(
            pedido["cliente"]
        )

        estado_pedido = str(
            pedido["estado_pedido"]
        ).upper()

        if estado_pedido != "SALIDA_PARCIAL":
            messagebox.showwarning(
                "Reprogramar saldo pendiente",
                (
                    "Esta operación solamente puede aplicarse "
                    "a pedidos con una entrega parcial."
                ),
                parent=self,
            )
            return

        cantidad_pendiente = numero(
            pedido["cantidad_total_pendiente"]
        )

        datos = self._pedir_datos_reprogramacion(
            pedido
        )

        if datos is None:
            return

        fecha_entrega_nueva = (
            datos["fecha_entrega_nueva"]
        )

        fecha_elaboracion_nueva = (
            datos["fecha_elaboracion_nueva"]
        )

        confirmar = messagebox.askyesno(
            "Confirmar reprogramación",
            (
                f"Pedido original: {id_pedido}\n"
                f"Cliente: {cliente}\n"
                "Cantidad a reprogramar: "
                f"{formato_cantidad(cantidad_pendiente)}"
                "\n\n"
                "Nueva entrega: "
                f"{fecha_texto(fecha_entrega_nueva)}"
                "\n"
                "Hora: "
                f"{hora_texto(datos['hora_entrega_nueva']) or 'Sin especificar'}"
                "\n"
                "Elaboración: "
                f"{fecha_texto(fecha_elaboracion_nueva) if fecha_elaboracion_nueva else 'Automática'}"
                "\n"
                "Envío: $"
                f"{formato_decimal(datos['importe_envio_nuevo'], decimales=2)}"
                "\n\n"
                f"Motivo: {datos['motivo']}"
                "\n\n"
                "Se creará un nuevo pedido con el saldo "
                "pendiente y se cerrará el pedido original."
                "\n\n"
                "No se generará una venta ni un movimiento "
                "de stock por esta operación."
                "\n\n"
                "¿Confirmar la reprogramación?"
            ),
            parent=self,
        )

        if not confirmar:
            return

        try:
            resultado = reprogramar_saldo_pedido(
                id_pedido_origen=id_pedido,

                fecha_entrega_nueva=(
                    datos[
                        "fecha_entrega_nueva"
                    ]
                ),

                motivo=datos["motivo"],

                hora_entrega_nueva=(
                    datos[
                        "hora_entrega_nueva"
                    ]
                ),

                fecha_elaboracion_nueva=(
                    datos[
                        "fecha_elaboracion_nueva"
                    ]
                ),

                importe_envio_nuevo=(
                    datos[
                        "importe_envio_nuevo"
                    ]
                ),

                observaciones_nuevo=(
                    datos[
                        "observaciones_nuevo"
                    ]
                ),
            )

        except Exception as error:
            messagebox.showerror(
                "Reprogramar saldo pendiente",
                (
                    "No se pudo reprogramar el saldo "
                    "del pedido."
                    f"\n\n{error}"
                ),
                parent=self,
            )
            return

        cantidad_reprogramada = numero(
            resultado.get(
                "cantidad_reprogramada"
            )
        )

        descuento_reprogramado = numero(
            resultado.get(
                "descuento_reprogramado"
            )
        )

        total_nuevo = numero(
            resultado.get(
                "total_pedido_nuevo"
            )
        )

        planes_cancelados = int(
            resultado.get(
                "planes_cancelados",
                0,
            )
            or 0
        )

        messagebox.showinfo(
            "Saldo reprogramado",
            (
                "Reprogramación realizada correctamente."
                "\n\n"
                f"Pedido original: {id_pedido}\n"
                "Estado final: "
                f"{resultado['estado_pedido_origen']}"
                "\n\n"
                "Nuevo pedido: "
                f"{resultado['id_pedido_destino']}\n"
                "Nueva entrega: "
                f"{fecha_texto(resultado['fecha_entrega_nueva'])}"
                "\n"
                "Nueva elaboración: "
                f"{fecha_texto(resultado['fecha_elaboracion_nueva'])}"
                "\n\n"
                "Cantidad reprogramada: "
                f"{formato_cantidad(cantidad_reprogramada)}"
                "\n"
                "Descuento trasladado: $"
                f"{formato_decimal(descuento_reprogramado, decimales=2)}"
                "\n"
                "Total del nuevo pedido: $"
                f"{formato_decimal(total_nuevo, decimales=2)}"
                "\n"
                "Planes pendientes cancelados: "
                f"{planes_cancelados}"
            ),
            parent=self,
        )

        # El pedido original queda resuelto y desaparece
        # de la lista de pendientes.
        # El nuevo aparecerá si entra dentro del filtro actual.
        self._actualizar_pedidos()


    def _cancelar_saldo_pendiente(self) -> None:
        if not self._pedido_seleccionado:
            return

        pedido = self._pedido_seleccionado

        id_pedido = int(
            pedido["id_pedido"]
        )

        cliente = str(
            pedido["cliente"]
        )

        estado_pedido = str(
            pedido["estado_pedido"]
        ).upper()

        if estado_pedido != "SALIDA_PARCIAL":
            messagebox.showwarning(
                "Cancelar saldo pendiente",
                (
                    "Esta operación solamente puede aplicarse "
                    "a pedidos con una entrega parcial."
                ),
                parent=self,
            )
            return

        cantidad_pendiente = numero(
            pedido["cantidad_total_pendiente"]
        )

        motivo = simpledialog.askstring(
            "Cancelar saldo pendiente",
            (
                f"Pedido: {id_pedido}\n"
                f"Cliente: {cliente}\n"
                "Saldo pendiente: "
                f"{formato_cantidad(cantidad_pendiente)}"
                "\n\n"
                "Indique el motivo por el cual el cliente "
                "no retirará el saldo:"
            ),
            parent=self,
        )

        if motivo is None:
            return

        motivo = motivo.strip()

        if not motivo:
            messagebox.showwarning(
                "Cancelar saldo pendiente",
                "Debe indicar el motivo de la cancelación.",
                parent=self,
            )
            return

        confirmar = messagebox.askyesno(
            "Confirmar cancelación del saldo",
            (
                f"Pedido: {id_pedido}\n"
                f"Cliente: {cliente}\n"
                "Saldo a cancelar: "
                f"{formato_cantidad(cantidad_pendiente)}"
                "\n\n"
                "No se generará una nueva venta, entrega "
                "ni movimiento de stock."
                "\n\n"
                f"Motivo: {motivo}"
                "\n\n"
                "¿Confirmar la cancelación del saldo?"
            ),
            parent=self,
        )

        if not confirmar:
            return

        try:
            resultado = cancelar_saldo_pedido(
                id_pedido=id_pedido,
                motivo=motivo,
            )

        except Exception as error:
            messagebox.showerror(
                "Cancelar saldo pendiente",
                "No se pudo cancelar el saldo del pedido."
                f"\n\n{error}",
                parent=self,
            )
            return

        cantidad_entregada = numero(
            resultado.get("cantidad_entregada")
        )

        cantidad_cancelada = numero(
            resultado.get("cantidad_cancelada")
        )

        detalles_cancelados = int(
            resultado.get(
                "detalles_cancelados",
                0,
            )
            or 0
        )

        planes_cancelados = int(
            resultado.get(
                "planes_cancelados",
                0,
            )
            or 0
        )

        messagebox.showinfo(
            "Saldo cancelado",
            (
                f"Saldo del pedido {id_pedido} "
                "cancelado correctamente."
                "\n\n"
                "Cantidad entregada previamente: "
                f"{formato_cantidad(cantidad_entregada)}"
                "\n"
                "Cantidad cancelada: "
                f"{formato_cantidad(cantidad_cancelada)}"
                "\n"
                f"Productos afectados: {detalles_cancelados}"
                "\n"
                f"Planes pendientes cancelados: {planes_cancelados}"
                "\n"
                "Estado final: "
                f"{resultado['estado_pedido']}"
            ),
            parent=self,
        )

        # El pedido quedó completamente resuelto
        # y desaparecerá de la lista de pendientes.
        self._actualizar_pedidos()

    def _cancelar_pedido(self) -> None:
        if not self._pedido_seleccionado:
            return

        pedido = self._pedido_seleccionado

        id_pedido = int(
            pedido["id_pedido"]
        )

        cliente = str(
            pedido["cliente"]
        )

        cantidad_pendiente = numero(
            pedido["cantidad_total_pendiente"]
        )

        motivo = simpledialog.askstring(
            "Cancelar pedido",
            (
                f"Pedido: {id_pedido}\n"
                f"Cliente: {cliente}\n\n"
                "Indique el motivo de la cancelación:"
            ),
            parent=self,
        )

        # El usuario cerró la ventana o presionó Cancelar.
        if motivo is None:
            return

        motivo = motivo.strip()

        if not motivo:
            messagebox.showwarning(
                "Cancelar pedido",
                "Debe indicar el motivo de la cancelación.",
                parent=self,
            )
            return

        confirmar = messagebox.askyesno(
            "Confirmar cancelación",
            (
                f"Pedido: {id_pedido}\n"
                f"Cliente: {cliente}\n"
                "Cantidad pendiente: "
                f"{formato_cantidad(cantidad_pendiente)}"
                "\n\n"
                "Se cancelará la totalidad pendiente "
                "del pedido y se liberarán sus reservas."
                "\n\n"
                f"Motivo: {motivo}"
                "\n\n"
                "¿Confirmar la cancelación?"
            ),
            parent=self,
        )

        if not confirmar:
            return

        try:
            resultado = cancelar_pedido(
                id_pedido=id_pedido,
                motivo=motivo,
            )

        except Exception as error:
            messagebox.showerror(
                "Cancelar pedido",
                "No se pudo cancelar el pedido."
                f"\n\n{error}",
                parent=self,
            )
            return

        cantidad_cancelada = numero(
            resultado.get("cantidad_cancelada")
        )

        detalles_cancelados = int(
            resultado.get(
                "detalles_cancelados",
                0,
            )
            or 0
        )

        planes_cancelados = int(
            resultado.get(
                "planes_cancelados",
                0,
            )
            or 0
        )

        messagebox.showinfo(
            "Pedido cancelado",
            (
                f"Pedido {id_pedido} cancelado correctamente."
                "\n\n"
                "Cantidad cancelada: "
                f"{formato_cantidad(cantidad_cancelada)}"
                "\n"
                f"Productos afectados: {detalles_cancelados}"
                "\n"
                f"Planes pendientes cancelados: {planes_cancelados}"
            ),
            parent=self,
        )

        # El pedido cancelado ya no aparecerá en la vista
        # de pedidos pendientes.
        self._actualizar_pedidos()

    def _limpiar_pedido(self) -> None:
        self._pedido_seleccionado = None
        self._detalle.clear()
        self._cantidades.clear()

        self.texto_pedido.set(
            "Seleccione un pedido."
        )
        self.texto_tipo_salida.set("")

        self.txt_cantidad.delete(0, "end")
        self.txt_observaciones.delete(
            0,
            "end",
        )

        self.btn_confirmar.configure(
            text="Confirmar entrega",
            state="disabled",
        )

        self.btn_cancelar.configure(
            state="disabled",
        )
        self.btn_cancelar_saldo.configure(
        state="disabled",
        )

        self.btn_reprogramar_saldo.configure(
            state="disabled",
        )


        for item in self.grilla_detalle.get_children():
            self.grilla_detalle.delete(item)

    def _centrar(
        self,
        parent: tk.Misc,
    ) -> None:
        self.update_idletasks()

        ancho = self.winfo_width()
        alto = self.winfo_height()

        x = (
            parent.winfo_rootx()
            + (parent.winfo_width() - ancho) // 2
        )

        y = (
            parent.winfo_rooty()
            + (parent.winfo_height() - alto) // 2
        )

        self.geometry(
            f"+{max(x, 0)}+{max(y, 0)}"
        )