from __future__ import annotations

import tkinter as tk
from pathlib import Path
from decimal import Decimal
from tkinter import messagebox, simpledialog, ttk
from typing import Any

from db.caja_repository import (
    anular_movimiento_caja,
    listar_medios_pago,
    listar_movimientos_caja,
    listar_tipos_movimiento_caja,
    obtener_sesion_abierta,
    registrar_movimiento_caja,
)
from ui.pedido import convertir_decimal, formato_decimal
from ui.ventana_util import maximizar_ventana


def numero(valor: Any) -> Decimal:
    if valor is None:
        return Decimal("0")

    return Decimal(str(valor))


def fecha_hora_texto(valor: Any) -> str:
    if valor is None:
        return ""

    try:
        return valor.strftime(
            "%d/%m/%Y %H:%M"
        )
    except AttributeError:
        return str(valor)


class VentanaCajaChica(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        navegador=None,
    ) -> None:
        super().__init__(parent)

        self.navegador = navegador
        self._tema = getattr(navegador, "tema", "claro")
        self._c = self._obtener_colores_tema()

        self._sesion: dict[str, Any] | None = None
        self._tipos: dict[str, dict[str, Any]] = {}
        self._medios: dict[str, dict[str, Any]] = {}
        self._movimientos: dict[str, dict[str, Any]] = {}

        self.title("Caja chica - Doña Elina")
        self.resizable(True, True)
        maximizar_ventana(self)

        self._crear_interfaz()
        self._inicializar()

        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    # =========================================================
    # Interfaz
    # =========================================================

    def _crear_interfaz(self) -> None:
        """Construye la interfaz visual sin alterar la lógica ni la BD."""
        colores = self._obtener_colores_tema()
        self._c = colores
        self._configurar_estilos(colores)
        self.configure(bg=colores["bg"])
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._crear_sidebar()

        contenedor = ttk.Frame(self, style="CajaChica.TFrame", padding=(22, 18))
        contenedor.grid(row=0, column=1, sticky="nsew")
        contenedor.columnconfigure(0, weight=1)
        contenedor.rowconfigure(3, weight=1)

        encabezado = tk.Frame(
            contenedor, bg=colores["surface"], bd=0,
            highlightthickness=1, highlightbackground=colores["border"]
        )
        encabezado.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        encabezado.columnconfigure(0, weight=1)

        tk.Label(
            encabezado, text="Caja chica",
            font=("Segoe UI", 22, "bold"),
            fg=colores["burgundy"], bg=colores["surface"], anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(16, 8), pady=(12, 2))

        tk.Label(
            encabezado, text="Administración de movimientos menores de la caja",
            font=("Segoe UI", 10),
            fg=colores["muted"], bg=colores["surface"], anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=(17, 8), pady=(0, 11))

        # Controles de tema y cierre, alineados como en el Dashboard.
        self.btn_tema = tk.Button(
            encabezado,
            text="☾  Modo oscuro",
            command=self._alternar_tema,
            font=("Segoe UI", 9, "bold"),
            bd=0, relief="flat", padx=12, pady=7, cursor="hand2",
            highlightthickness=1, highlightbackground=colores["border"],
            bg=colores["surface"], fg=colores["text"],
            activebackground=colores["surface_alt"], activeforeground=colores["text"],
        )
        self.btn_tema.grid(row=0, column=1, rowspan=2, sticky="e", padx=(8, 4), pady=7)

        # Botón X visible dentro de la aplicación, arriba a la derecha.
        boton_cerrar = tk.Button(
            encabezado, text="×", command=self._cerrar,
            font=("Segoe UI", 18, "bold"),
            fg=colores["muted"], bg=colores["surface"],
            activeforeground=colores["white"], activebackground=colores["danger"],
            bd=0, relief="flat", width=3, cursor="hand2",
        )
        boton_cerrar.grid(row=0, column=2, rowspan=2, sticky="ne", padx=8, pady=7)
        boton_cerrar.bind("<Enter>", lambda _e: boton_cerrar.configure(bg=colores["danger"], fg=colores["white"]))
        boton_cerrar.bind("<Leave>", lambda _e: boton_cerrar.configure(bg=colores["surface"], fg=colores["muted"]))

        self._crear_encabezado(contenedor)
        self._crear_carga(contenedor)
        self._crear_grilla(contenedor)
        self._crear_pie(contenedor)

    def _crear_sidebar(self) -> None:
        c = self._obtener_colores_tema()
        sidebar = tk.Frame(self, bg=c["sidebar"], width=245, bd=0)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        # Logo
        box = tk.Frame(sidebar, bg=c["logo_bg"], bd=0)
        box.pack(fill="x", padx=14, pady=(16, 14))
        ruta_logo = Path(__file__).resolve().parent.parent / "assets" / "logo_dona_elina.png"
        try:
            self._logo_img = tk.PhotoImage(file=str(ruta_logo))
            if self._logo_img.width() > 215:
                factor = max(1, self._logo_img.width() // 215)
                self._logo_img = self._logo_img.subsample(factor, factor)
            tk.Label(box, image=self._logo_img, bg=c["logo_bg"], bd=0).pack(padx=8, pady=8)
        except Exception:
            tk.Label(box, text="Doña Elina", font=("Segoe Script", 24, "bold"),
                     fg=c["burgundy"], bg=c["logo_bg"]).pack(pady=25)

        tk.Label(sidebar, text="ACCESOS RÁPIDOS", font=("Segoe UI", 10, "bold"),
                 fg=c["gold"], bg=c["sidebar"], anchor="w").pack(fill="x", padx=24, pady=(4, 7))
        tk.Frame(sidebar, height=1, bg=c["gold"]).pack(fill="x", padx=24, pady=(0, 8))

        # Navegación lateral, en lugar de la antigua barra superior.
        opciones = (
            ("+", "Nuevo pedido", lambda: self.navegador.abrir_pedido(self)),
            ("☷", "Lista de precios", lambda: self.navegador.abrir_reporte_precios(self)),
            ("▰", "Salidas y Entregas", lambda: self.navegador.abrir_salidas(self)),
            ("⚙", "Configuración", lambda: messagebox.showinfo("Configuración", "Esta función se mantiene para el próximo módulo.", parent=self)),
        )
        for icono, texto, comando in opciones:
            self._menu_button(sidebar, icono, texto, comando, c)

        tk.Frame(sidebar, height=1, bg=c["gold"]).pack(fill="x", padx=24, pady=(12, 8))
        self._menu_button(sidebar, "‹", "Menú principal", lambda: self.navegador.volver_menu(self), c)
        self._menu_button(sidebar, "×", "Cerrar", self._cerrar, c)

        pie = tk.Label(sidebar, text="Doña Elina - Sistema de Gestión\nVersión 1.0.0",
                       font=("Segoe UI", 7), fg=c["gold"], bg=c["sidebar"],
                       justify="left", anchor="w")
        pie.pack(side="bottom", fill="x", padx=20, pady=(0, 12))

    def _menu_button(self, parent, icono, texto, comando, c) -> None:
        boton = tk.Button(
            parent, text=f"  {icono}   {texto}", command=comando,
            anchor="w", font=("Segoe UI", 10, "bold"),
            bg=c["sidebar"], fg=c["white"],
            activebackground=c["sidebar_hover"], activeforeground=c["white"],
            bd=0, relief="flat", padx=14, pady=9, cursor="hand2",
        )
        boton.pack(fill="x", padx=12, pady=2)
        boton.configure(overrelief="flat", takefocus=0)
        def _entrar(_event=None):
            try:
                boton.configure(bg=self._obtener_colores_tema()["sidebar_hover"])
            except tk.TclError:
                pass
        def _salir(_event=None):
            try:
                boton.configure(bg=self._obtener_colores_tema()["sidebar"])
            except tk.TclError:
                pass
        boton.bind("<Enter>", _entrar, add="+")
        boton.bind("<Leave>", _salir, add="+")

    def _cerrar(self) -> None:
        if self.navegador is not None:
            self.navegador.volver_menu(self)
        else:
            self.destroy()

    def _obtener_colores_tema(self) -> dict[str, str]:
        if self._tema == "oscuro":
            return {
                "bg": "#15171b", "panel": "#1d2025", "surface": "#24282e",
                "surface_alt": "#292e35", "border": "#363c44", "text": "#f3f4f6",
                "muted": "#aeb5bf", "sidebar": "#321019", "sidebar_hover": "#4a1723",
                "gold": "#d5a63a", "burgundy": "#c13b58", "green": "#4d9a59",
                "blue": "#4b82c3", "purple": "#8d55b4", "danger": "#e05b68",
                "success": "#55bd69", "white": "#ffffff", "logo_bg": "#fff8f8",
            }
        return {
            "bg": "#f3f1ef", "panel": "#ebe8e6", "surface": "#ffffff",
            "surface_alt": "#faf8f7", "border": "#ddd7d4", "text": "#252328",
            "muted": "#6d6870", "sidebar": "#3a111b", "sidebar_hover": "#511522",
            "gold": "#c99624", "burgundy": "#9f1230", "green": "#3d8149",
            "blue": "#2f6fae", "purple": "#733da0", "danger": "#c94b57",
            "success": "#3caa55", "white": "#ffffff", "logo_bg": "#fff9f9",
        }

    def _alternar_tema(self) -> None:
        self._tema = "oscuro" if self._tema == "claro" else "claro"
        if self.navegador is not None:
            self.navegador.tema = self._tema
        self._aplicar_tema()

    def _aplicar_tema(self) -> None:
        nuevo = self._obtener_colores_tema()
        viejo = self._c
        # Reemplazamos únicamente colores conocidos; así conservamos
        # burgundy/gold/danger y demás colores semánticos.
        mapa = {viejo[k]: nuevo[k] for k in viejo if k in nuevo}

        def recolorear(widget):
            try:
                for opcion in ("bg", "background", "fg", "foreground", "activebackground", "activeforeground", "highlightbackground", "highlightcolor", "insertbackground", "selectbackground", "selectforeground"):
                    try:
                        valor = widget.cget(opcion)
                    except (tk.TclError, KeyError):
                        continue
                    if valor in mapa:
                        widget.configure(**{opcion: mapa[valor]})
                for hijo in widget.winfo_children():
                    recolorear(hijo)
            except tk.TclError:
                pass

        recolorear(self)
        self._c = nuevo
        self._configurar_estilos(nuevo)
        self.configure(bg=nuevo["bg"])
        self.btn_tema.configure(
            text="☾  Modo oscuro" if self._tema == "claro" else "☀  Modo claro",
            bg=nuevo["surface"], fg=nuevo["text"],
            activebackground=nuevo["surface_alt"], activeforeground=nuevo["text"],
            highlightbackground=nuevo["border"],
        )

    def _configurar_estilos(self, c: dict[str, str]) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("CajaChica.TFrame", background=c["bg"])
        style.configure(
            "CajaChica.Card.TLabelframe",
            background=c["surface"],
            bordercolor=c["border"],
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "CajaChica.Card.TLabelframe.Label",
            background=c["surface"],
            foreground=c["burgundy"],
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "CajaChica.TLabel",
            background=c["surface"],
            foreground=c["text"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "CajaChica.Title.TLabel",
            background=c["bg"],
            foreground=c["burgundy"],
            font=("Segoe UI", 22, "bold"),
        )
        style.configure(
            "CajaChica.Subtitle.TLabel",
            background=c["bg"],
            foreground=c["muted"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "CajaChica.Session.TLabel",
            background=c["surface"],
            foreground=c["text"],
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "CajaChica.Entry.TEntry",
            fieldbackground=c["surface_alt"],
            foreground=c["text"],
            bordercolor=c["border"],
            lightcolor=c["border"],
            darkcolor=c["border"],
            padding=7,
        )
        style.configure(
            "CajaChica.TCombobox",
            fieldbackground=c["surface_alt"],
            foreground=c["text"],
            bordercolor=c["border"],
            lightcolor=c["border"],
            darkcolor=c["border"],
            padding=6,
        )
        style.map(
            "CajaChica.TCombobox",
            fieldbackground=[("readonly", c["surface_alt"])],
            foreground=[("readonly", c["text"])],
        )
        style.configure(
            "CajaChica.Primary.TButton",
            background=c["burgundy"],
            foreground=c["white"],
            font=("Segoe UI", 9, "bold"),
            padding=(14, 8),
            borderwidth=0,
        )
        style.map(
            "CajaChica.Primary.TButton",
            background=[("active", c["sidebar_hover"]), ("disabled", c["border"])],
            foreground=[("disabled", c["muted"])],
        )
        style.configure(
            "CajaChica.Secondary.TButton",
            background=c["surface_alt"],
            foreground=c["text"],
            font=("Segoe UI", 9, "bold"),
            padding=(12, 7),
            borderwidth=1,
            bordercolor=c["border"],
        )
        style.map(
            "CajaChica.Secondary.TButton",
            background=[("active", c["panel"])],
        )
        style.configure(
            "CajaChica.Treeview",
            background=c["surface"],
            fieldbackground=c["surface"],
            foreground=c["text"],
            rowheight=30,
            font=("Segoe UI", 9),
            bordercolor=c["border"],
            lightcolor=c["border"],
            darkcolor=c["border"],
        )
        style.configure(
            "CajaChica.Treeview.Heading",
            background=c["sidebar"],
            foreground=c["white"],
            font=("Segoe UI", 9, "bold"),
            padding=(8, 8),
        )
        style.map(
            "CajaChica.Treeview",
            background=[("selected", c["burgundy"])],
            foreground=[("selected", c["white"])],
        )
        style.configure(
            "CajaChica.Total.TLabel",
            background=c["bg"],
            foreground=c["text"],
            font=("Segoe UI", 10, "bold"),
        )

    def _crear_encabezado(self, parent: ttk.Frame) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="  Sesión de caja  ",
            style="CajaChica.Card.TLabelframe",
            padding=(14, 12),
        )
        marco.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        marco.columnconfigure(0, weight=1)

        self.texto_sesion = tk.StringVar(value="Buscando caja abierta...")
        ttk.Label(
            marco,
            textvariable=self.texto_sesion,
            style="CajaChica.Session.TLabel",
        ).grid(row=0, column=0, sticky="w")

    def _crear_carga(self, parent: ttk.Frame) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="  Registrar movimiento  ",
            style="CajaChica.Card.TLabelframe",
            padding=(14, 12),
        )
        marco.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        marco.columnconfigure(0, weight=0)
        marco.columnconfigure(1, weight=0)
        marco.columnconfigure(2, weight=0)
        marco.columnconfigure(3, weight=2)
        marco.columnconfigure(4, weight=3)

        ttk.Label(marco, text="Tipo", style="CajaChica.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.cbo_tipo = ttk.Combobox(marco, state="readonly", width=20, style="CajaChica.TCombobox")
        self.cbo_tipo.grid(row=1, column=0, padx=(0, 10), sticky="w")

        ttk.Label(marco, text="Medio", style="CajaChica.TLabel").grid(row=0, column=1, sticky="w", pady=(0, 4))
        self.cbo_medio = ttk.Combobox(marco, state="readonly", width=18, style="CajaChica.TCombobox")
        self.cbo_medio.grid(row=1, column=1, padx=(0, 10), sticky="w")

        ttk.Label(marco, text="Importe", style="CajaChica.TLabel").grid(row=0, column=2, sticky="w", pady=(0, 4))
        self.txt_importe = ttk.Entry(marco, width=16, justify="right", style="CajaChica.Entry.TEntry")
        self.txt_importe.grid(row=1, column=2, padx=(0, 10), sticky="w")

        ttk.Label(marco, text="Concepto", style="CajaChica.TLabel").grid(row=0, column=3, sticky="w", pady=(0, 4))
        self.txt_concepto = ttk.Entry(marco, style="CajaChica.Entry.TEntry")
        self.txt_concepto.grid(row=1, column=3, padx=(0, 10), sticky="ew")

        ttk.Label(marco, text="Observaciones", style="CajaChica.TLabel").grid(row=0, column=4, sticky="w", pady=(0, 4))
        self.txt_observaciones = ttk.Entry(marco, style="CajaChica.Entry.TEntry")
        self.txt_observaciones.grid(row=1, column=4, sticky="ew")

        acciones = ttk.Frame(marco, style="CajaChica.TFrame")
        acciones.grid(row=2, column=0, columnspan=5, sticky="e", pady=(12, 0))
        self.btn_registrar = ttk.Button(
            acciones,
            text="Registrar movimiento",
            command=self._registrar,
            state="disabled",
            style="CajaChica.Primary.TButton",
        )
        self.btn_registrar.pack(side="left")

        self.txt_importe.bind("<Return>", lambda _evento: self._registrar())
        self.txt_concepto.bind("<Return>", lambda _evento: self._registrar())

    def _crear_grilla(self, parent: ttk.Frame) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="  Movimientos de la sesión  ",
            style="CajaChica.Card.TLabelframe",
            padding=(10, 10),
        )
        marco.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(0, weight=1)

        columnas = ("fecha", "tipo", "medio", "concepto", "importe", "estado", "usuario")
        self.grilla = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
            style="CajaChica.Treeview",
        )

        titulos = {
            "fecha": "Fecha y hora", "tipo": "Tipo", "medio": "Medio",
            "concepto": "Concepto", "importe": "Importe", "estado": "Estado", "usuario": "Usuario",
        }
        for columna, titulo in titulos.items():
            self.grilla.heading(columna, text=titulo)

        self.grilla.column("fecha", width=145, minwidth=125, anchor="center", stretch=False)
        self.grilla.column("tipo", width=140, minwidth=100, anchor="w", stretch=False)
        self.grilla.column("medio", width=120, minwidth=90, anchor="w", stretch=False)
        self.grilla.column("concepto", width=350, minwidth=180, anchor="w", stretch=True)
        self.grilla.column("importe", width=130, minwidth=100, anchor="e", stretch=False)
        self.grilla.column("estado", width=110, minwidth=90, anchor="center", stretch=False)
        self.grilla.column("usuario", width=180, minwidth=120, anchor="w", stretch=True)

        barra_vertical = ttk.Scrollbar(marco, orient="vertical", command=self.grilla.yview)
        barra_horizontal = ttk.Scrollbar(marco, orient="horizontal", command=self.grilla.xview)
        self.grilla.configure(yscrollcommand=barra_vertical.set, xscrollcommand=barra_horizontal.set)
        self.grilla.grid(row=0, column=0, sticky="nsew")
        barra_vertical.grid(row=0, column=1, sticky="ns")
        barra_horizontal.grid(row=1, column=0, sticky="ew")
        self.grilla.bind("<<TreeviewSelect>>", self._seleccionar_movimiento)

    def _crear_pie(self, parent: ttk.Frame) -> None:
        pie = ttk.Frame(parent, style="CajaChica.TFrame")
        pie.grid(row=4, column=0, sticky="ew")
        pie.columnconfigure(0, weight=1)

        self.texto_totales = tk.StringVar(value="")
        ttk.Label(
            pie,
            textvariable=self.texto_totales,
            style="CajaChica.Total.TLabel",
        ).grid(row=0, column=0, sticky="w")

        acciones = ttk.Frame(pie, style="CajaChica.TFrame")
        acciones.grid(row=0, column=1, sticky="e")

        self.btn_anular = ttk.Button(
            acciones,
            text="Anular movimiento",
            command=self._anular,
            state="disabled",
            style="CajaChica.Secondary.TButton",
        )
        self.btn_anular.pack(side="left", padx=(0, 8))

        ttk.Button(
            acciones,
            text="Actualizar",
            command=self._actualizar_movimientos,
            style="CajaChica.Secondary.TButton",
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            acciones,
            text="Cerrar",
            command=self.destroy,
            style="CajaChica.Secondary.TButton",
        ).pack(side="left")

    # =========================================================
    # Inicialización
    # =========================================================

    def _inicializar(self) -> None:
        self._cargar_sesion()

        if self._sesion is None:
            return

        self._cargar_tipos()
        self._cargar_medios()

        self._actualizar_movimientos()

        self.btn_registrar.configure(
            state="normal",
        )

        self.txt_importe.focus_set()

    def _cargar_sesion(self) -> None:
        try:
            sesion = (
                obtener_sesion_abierta()
            )

        except Exception as error:
            messagebox.showerror(
                "Caja chica",
                (
                    "No se pudo recuperar "
                    "la sesión de caja."
                    f"\n\n{error}"
                ),
                parent=self,
            )
            return

        if sesion is None:
            self.texto_sesion.set(
                "No hay una sesión de caja abierta."
            )

            messagebox.showwarning(
                "Caja chica",
                (
                    "Debe abrir una caja antes "
                    "de registrar movimientos."
                ),
                parent=self,
            )
            return

        self._sesion = sesion

        id_sesion = int(
            sesion["id_caja_sesion"]
        )

        saldo_inicial = numero(
            sesion.get(
                "saldo_inicial"
            )
        )

        fecha_apertura = (
            fecha_hora_texto(
                sesion.get(
                    "fecha_apertura"
                )
            )
        )

        descripcion_caja = (
            sesion.get(
                "descripcion"
            )
            or sesion.get(
                "caja"
            )
            or f"Caja {sesion.get('id_caja', '')}"
        )

        self.texto_sesion.set(
            f"{descripcion_caja} · "
            f"Sesión {id_sesion} · "
            f"Abierta {fecha_apertura} · "
            "Saldo inicial: $"
            f"{formato_decimal(
                saldo_inicial,
                decimales=2,
            )}"
        )

    def _cargar_tipos(self) -> None:
        try:
            filas = (
                listar_tipos_movimiento_caja()
            )

        except Exception as error:
            messagebox.showerror(
                "Caja chica",
                (
                    "No se pudieron recuperar "
                    "los tipos de movimiento."
                    f"\n\n{error}"
                ),
                parent=self,
            )
            return

        self._tipos.clear()

        valores: list[str] = []

        valor_gasto = None

        for fila in filas:
            factor = int(
                fila["factor"]
            )

            signo = (
                "+"
                if factor > 0
                else "-"
            )

            texto = (
                f"{fila['descripcion']} "
                f"({signo})"
            )

            self._tipos[
                texto
            ] = fila

            valores.append(
                texto
            )

            if (
                str(
                    fila["codigo"]
                ).upper()
                == "GASTO"
            ):
                valor_gasto = texto

        self.cbo_tipo.configure(
            values=valores
        )

        if valor_gasto:
            self.cbo_tipo.set(
                valor_gasto
            )

        elif valores:
            self.cbo_tipo.set(
                valores[0]
            )

    def _cargar_medios(self) -> None:
        try:
            filas = listar_medios_pago()

        except Exception as error:
            messagebox.showerror(
                "Caja chica",
                (
                    "No se pudieron recuperar "
                    "los medios de pago."
                    f"\n\n{error}"
                ),
                parent=self,
            )
            return

        self._medios.clear()

        valores: list[str] = []

        valor_efectivo = None

        for fila in filas:
            texto = str(
                fila["descripcion"]
            )

            self._medios[
                texto
            ] = fila

            valores.append(
                texto
            )

            if (
                str(
                    fila["codigo"]
                ).upper()
                == "EFECTIVO"
            ):
                valor_efectivo = texto

        self.cbo_medio.configure(
            values=valores
        )

        if valor_efectivo:
            self.cbo_medio.set(
                valor_efectivo
            )

        elif valores:
            self.cbo_medio.set(
                valores[0]
            )

    # =========================================================
    # Movimientos
    # =========================================================

    def _actualizar_movimientos(
        self,
    ) -> None:
        if self._sesion is None:
            return

        id_sesion = int(
            self._sesion[
                "id_caja_sesion"
            ]
        )

        try:
            filas = (
                listar_movimientos_caja(
                    id_sesion
                )
            )

        except Exception as error:
            messagebox.showerror(
                "Caja chica",
                (
                    "No se pudieron recuperar "
                    "los movimientos."
                    f"\n\n{error}"
                ),
                parent=self,
            )
            return

        self._movimientos.clear()

        for item in (
            self.grilla.get_children()
        ):
            self.grilla.delete(
                item
            )

        total_ingresos = Decimal("0")
        total_egresos = Decimal("0")

        for indice, fila in enumerate(
            filas
        ):
            iid = (
                "movimiento-"
                f"{fila['id_caja_movimiento']}"
                f"-{indice}"
            )

            self._movimientos[
                iid
            ] = fila

            importe = numero(
                fila["importe"]
            )

            factor = int(
                fila["factor"]
            )

            estado = str(
                fila["estado"]
            ).upper()

            if estado == "CONFIRMADO":
                if factor > 0:
                    total_ingresos += (
                        importe
                    )
                else:
                    total_egresos += (
                        importe
                    )

            importe_mostrado = (
                importe
                if factor > 0
                else -importe
            )

            self.grilla.insert(
                "",
                "end",
                iid=iid,
                values=(
                    fecha_hora_texto(
                        fila[
                            "fecha_hora"
                        ]
                    ),

                    fila[
                        "tipo_movimiento"
                    ],

                    fila[
                        "medio_pago"
                    ],

                    fila[
                        "concepto"
                    ],

                    formato_decimal(
                        importe_mostrado,
                        decimales=2,
                    ),

                    fila[
                        "estado"
                    ],

                    fila[
                        "usuario_alta"
                    ],
                ),
            )

        neto = (
            total_ingresos
            - total_egresos
        )

        self.texto_totales.set(
            "Ingresos: $"
            f"{formato_decimal(
                total_ingresos,
                decimales=2,
            )}"
            "  ·  Egresos: $"
            f"{formato_decimal(
                total_egresos,
                decimales=2,
            )}"
            "  ·  Neto: $"
            f"{formato_decimal(
                neto,
                decimales=2,
            )}"
        )

        self.btn_anular.configure(
            state="disabled",
        )

    def _seleccionar_movimiento(
        self,
        _evento=None,
    ) -> None:
        seleccion = (
            self.grilla.selection()
        )

        if not seleccion:
            self.btn_anular.configure(
                state="disabled",
            )
            return

        movimiento = (
            self._movimientos.get(
                seleccion[0]
            )
        )

        if movimiento is None:
            self.btn_anular.configure(
                state="disabled",
            )
            return

        estado = str(
            movimiento["estado"]
        ).upper()

        self.btn_anular.configure(
            state=(
                "normal"
                if estado == "CONFIRMADO"
                else "disabled"
            )
        )

    def _registrar(self) -> None:
        if self._sesion is None:
            return

        tipo = self._tipos.get(
            self.cbo_tipo.get()
        )

        medio = self._medios.get(
            self.cbo_medio.get()
        )

        if tipo is None:
            messagebox.showwarning(
                "Caja chica",
                "Seleccione un tipo de movimiento.",
                parent=self,
            )
            return

        if medio is None:
            messagebox.showwarning(
                "Caja chica",
                "Seleccione un medio de pago.",
                parent=self,
            )
            return

        try:
            importe = convertir_decimal(
                self.txt_importe.get(),
                decimales=2,
            )

        except Exception as error:
            messagebox.showwarning(
                "Caja chica",
                f"Importe inválido.\n\n{error}",
                parent=self,
            )
            return

        if importe <= 0:
            messagebox.showwarning(
                "Caja chica",
                "El importe debe ser mayor que cero.",
                parent=self,
            )
            return

        concepto = (
            self.txt_concepto
            .get()
            .strip()
        )

        if not concepto:
            messagebox.showwarning(
                "Caja chica",
                "Debe indicar el concepto.",
                parent=self,
            )
            return

        factor = int(
            tipo["factor"]
        )

        accion = (
            "ingreso"
            if factor > 0
            else "egreso"
        )

        confirmar = (
            messagebox.askyesno(
                "Registrar movimiento",
                (
                    f"Tipo: {tipo['descripcion']}\n"
                    f"Medio: {medio['descripcion']}\n"
                    f"Importe: $"
                    f"{formato_decimal(
                        importe,
                        decimales=2,
                    )}\n"
                    f"Concepto: {concepto}"
                    "\n\n"
                    f"Se registrará un {accion} "
                    "en la caja."
                    "\n\n"
                    "¿Confirmar?"
                ),
                parent=self,
            )
        )

        if not confirmar:
            return

        try:
            resultado = (
                registrar_movimiento_caja(
                    id_caja_sesion=int(
                        self._sesion[
                            "id_caja_sesion"
                        ]
                    ),

                    id_tipo_movimiento_caja=int(
                        tipo[
                            "id_tipo_movimiento_caja"
                        ]
                    ),

                    id_medio_pago=int(
                        medio[
                            "id_medio_pago"
                        ]
                    ),

                    importe=importe,

                    concepto=concepto,

                    observaciones=(
                        self.txt_observaciones
                        .get()
                        .strip()
                        or None
                    ),
                )
            )

        except Exception as error:
            messagebox.showerror(
                "Caja chica",
                (
                    "No se pudo registrar "
                    "el movimiento."
                    f"\n\n{error}"
                ),
                parent=self,
            )
            return

        saldo_resultante = numero(
            resultado.get(
                "saldo_resultante"
            )
        )

        messagebox.showinfo(
            "Movimiento registrado",
            (
                "Movimiento registrado correctamente."
                "\n\n"
                "Número: "
                f"{resultado['id_caja_movimiento']}\n"
                "Tipo: "
                f"{resultado['tipo_movimiento']}\n"
                "Importe: $"
                f"{formato_decimal(
                    numero(resultado['importe']),
                    decimales=2,
                )}\n"
                "Saldo teórico del medio: $"
                f"{formato_decimal(
                    saldo_resultante,
                    decimales=2,
                )}"
            ),
            parent=self,
        )

        self._limpiar_carga()
        self._actualizar_movimientos()

    def _anular(self) -> None:
        seleccion = (
            self.grilla.selection()
        )

        if not seleccion:
            return

        movimiento = (
            self._movimientos.get(
                seleccion[0]
            )
        )

        if movimiento is None:
            return

        if (
            str(
                movimiento["estado"]
            ).upper()
            != "CONFIRMADO"
        ):
            return

        id_movimiento = int(
            movimiento[
                "id_caja_movimiento"
            ]
        )

        motivo = (
            simpledialog.askstring(
                "Anular movimiento",
                (
                    "Movimiento: "
                    f"{id_movimiento}\n"
                    "Concepto: "
                    f"{movimiento['concepto']}\n"
                    "Importe: $"
                    f"{formato_decimal(
                        numero(
                            movimiento[
                                'importe'
                            ]
                        ),
                        decimales=2,
                    )}"
                    "\n\n"
                    "Indique el motivo "
                    "de la anulación:"
                ),
                parent=self,
            )
        )

        if motivo is None:
            return

        motivo = motivo.strip()

        if not motivo:
            messagebox.showwarning(
                "Anular movimiento",
                (
                    "Debe indicar el motivo "
                    "de la anulación."
                ),
                parent=self,
            )
            return

        confirmar = (
            messagebox.askyesno(
                "Confirmar anulación",
                (
                    f"Movimiento: {id_movimiento}\n"
                    f"Concepto: "
                    f"{movimiento['concepto']}\n"
                    "\n"
                    "El movimiento no se eliminará; "
                    "quedará registrado como ANULADO."
                    "\n\n"
                    f"Motivo: {motivo}"
                    "\n\n"
                    "¿Confirmar?"
                ),
                parent=self,
            )
        )

        if not confirmar:
            return

        try:
            anular_movimiento_caja(
                id_caja_movimiento=
                    id_movimiento,

                motivo=motivo,
            )

        except Exception as error:
            messagebox.showerror(
                "Anular movimiento",
                (
                    "No se pudo anular "
                    "el movimiento."
                    f"\n\n{error}"
                ),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Movimiento anulado",
            (
                f"Movimiento {id_movimiento} "
                "anulado correctamente."
            ),
            parent=self,
        )

        self._actualizar_movimientos()

    def _limpiar_carga(self) -> None:
        self.txt_importe.delete(
            0,
            "end",
        )

        self.txt_concepto.delete(
            0,
            "end",
        )

        self.txt_observaciones.delete(
            0,
            "end",
        )

        self.txt_importe.focus_set()