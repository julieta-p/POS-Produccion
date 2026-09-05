from __future__ import annotations

import tkinter as tk
from decimal import Decimal
from pathlib import Path
from tkinter import messagebox
from typing import Any

from db.caja_repository import obtener_sesion_abierta
from db.conexion import probar_conexion
from ui.caja_apertura import VentanaAperturaCaja
from ui.navegacion import NavegadorPOS


# -----------------------------------------------------------------------------
# Utilidades
# -----------------------------------------------------------------------------
def obtener_valor(
    datos: dict[str, Any],
    *nombres: str,
    predeterminado: Any = None,
) -> Any:
    for nombre in nombres:
        valor = datos.get(nombre.lower())
        if valor is not None:
            return valor
    return predeterminado


def formato_moneda(valor: Any) -> str:
    if valor is None:
        valor = 0
    numero = Decimal(str(valor))
    texto = f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"$ {texto}"


class VentanaPrincipal(tk.Tk):
    """Dashboard principal. Los cambios de este archivo son exclusivamente visuales."""

    def __init__(self) -> None:
        super().__init__()

        self._ancho_pantalla = self.winfo_screenwidth()
        self._alto_pantalla = self.winfo_screenheight()
        self._pantalla_compacta = (
            self._ancho_pantalla < 1100 or self._alto_pantalla < 700
        )

        self.navegador = NavegadorPOS(self)
        self.estado = tk.StringVar(value="Comprobando conexión...")
        self.sesion_caja: dict[str, Any] | None = None
        self.datos_conexion: dict[str, Any] | None = None
        self.conexion_disponible = False

        # Tema: comienza en claro. El usuario puede cambiarlo desde el Dashboard.
        self._tema = "claro"
        self.navegador.tema = self._tema

        # Referencias para actualizar colores sin reconstruir la ventana.
        self._tema_frames: list[tuple[tk.Misc, str]] = []
        self._tema_labels: list[tuple[tk.Misc, str, str | None]] = []
        self._tema_buttons: list[tuple[tk.Button, str]] = []
        self._tema_cards: list[tk.Frame] = []
        self._tema_lines: list[tuple[tk.Frame, str]] = []
        self._tarjetas: list[dict[str, Any]] = []
        self._logo_img: tk.PhotoImage | None = None

        self.title("Doña Elina - Sistema de Gestión")
        self.resizable(True, True)
        self._ajustar_tamano_inicial()
        self._crear_interfaz()
        self._aplicar_tema()
        self._comprobar_conexion()

        if self.conexion_disponible:
            self._actualizar_estado_caja()

    # ------------------------------------------------------------------
    # PALETA
    # ------------------------------------------------------------------
    def _colores(self) -> dict[str, str]:
        if self._tema == "oscuro":
            return {
                "bg": "#15171b",
                "panel": "#1d2025",
                "surface": "#24282e",
                "surface_alt": "#292e35",
                "border": "#363c44",
                "text": "#f3f4f6",
                "muted": "#aeb5bf",
                "sidebar": "#321019",
                "sidebar_hover": "#4a1723",
                "sidebar_border": "#6a2737",
                "gold": "#d5a63a",
                "burgundy": "#c13b58",
                "green": "#4d9a59",
                "blue": "#4b82c3",
                "purple": "#8d55b4",
                "danger": "#e05b68",
                "success": "#55bd69",
                "white": "#ffffff",
                "logo_bg": "#fff8f8",
            }

        return {
            "bg": "#f3f1ef",
            "panel": "#ebe8e6",
            "surface": "#ffffff",
            "surface_alt": "#faf8f7",
            "border": "#ddd7d4",
            "text": "#252328",
            "muted": "#6d6870",
            "sidebar": "#3a111b",
            "sidebar_hover": "#511522",
            "sidebar_border": "#6c2637",
            "gold": "#c99624",
            "burgundy": "#9f1230",
            "green": "#3d8149",
            "blue": "#2f6fae",
            "purple": "#733da0",
            "danger": "#c94b57",
            "success": "#3caa55",
            "white": "#ffffff",
            "logo_bg": "#fff9f9",
        }

    def _aplicar_tema(self) -> None:
        c = self._colores()
        self.configure(bg=c["bg"])

        for widget, key in self._tema_frames:
            try:
                widget.configure(bg=c[key])
            except tk.TclError:
                pass

        for widget, fg_key, bg_key in self._tema_labels:
            try:
                widget.configure(
                    fg=c[fg_key],
                    bg=c[bg_key] if bg_key else c["surface"],
                )
            except tk.TclError:
                pass

        for widget, color_key in self._tema_buttons:
            try:
                widget.configure(
                    bg=c[color_key],
                    fg=c["white"],
                    activebackground=c["sidebar_hover"] if color_key == "sidebar" else c[color_key],
                    activeforeground=c["white"],
                )
            except tk.TclError:
                pass

        for widget, color_key in self._tema_lines:
            try:
                widget.configure(bg=c[color_key])
            except tk.TclError:
                pass

        # Logos siempre conservan un fondo claro para no alterar el aspecto del archivo.
        if hasattr(self, "logo_box"):
            self.logo_box.configure(bg=c["logo_bg"])
        if self._logo_img is not None and hasattr(self, "logo_label"):
            self.logo_label.configure(bg=c["logo_bg"])

        # Tarjetas y sus elementos internos.
        for tarjeta in self._tarjetas:
            card = tarjeta["card"]
            color_key = tarjeta["color"]
            try:
                card.configure(bg=c["surface"], highlightbackground=c["border"])
                tarjeta["top"].configure(bg=c["surface"])
                tarjeta["title_box"].configure(bg=c["surface"])
                tarjeta["list"].configure(bg=c["surface"])
                tarjeta["icon"].configure(bg=c["surface"], fg=c[color_key])
                tarjeta["title"].configure(bg=c["surface"], fg=c[color_key])
                tarjeta["subtitle"].configure(bg=c["surface"], fg=c["muted"])
                for label in tarjeta["items"]:
                    label.configure(bg=c["surface"], fg=c["text"])
                tarjeta["button"].configure(
                    bg=c[color_key],
                    fg=c["white"],
                    activebackground=c[color_key],
                    activeforeground=c["white"],
                )
                tarjeta["line"].configure(bg=c[color_key])
            except tk.TclError:
                pass

        # Caja lateral.
        if hasattr(self, "caja_status"):
            try:
                self.caja_status.configure(bg=c["sidebar_hover"], highlightbackground=c["gold"] if self.sesion_caja else c["sidebar_border"])
                self.caja_icon.configure(bg=c["sidebar_hover"], fg=c["gold"] if self.sesion_caja else c["muted"])
                self.caja_titulo.configure(bg=c["sidebar_hover"], fg=c["white"])
                self.caja_valor.configure(bg=c["sidebar_hover"], fg=c["success"] if self.sesion_caja else c["danger"])
                self.caja_sub.configure(bg=c["sidebar_hover"], fg="#c6aeb4")
            except tk.TclError:
                pass

        if hasattr(self, "lbl_conexion"):
            try:
                self.lbl_conexion.configure(fg=c["success"] if self.conexion_disponible else c["danger"], bg=c["panel"])
            except tk.TclError:
                pass

        if hasattr(self, "btn_tema"):
            try:
                self.btn_tema.configure(
                    text="☾  Modo oscuro" if self._tema == "claro" else "☀  Modo claro",
                    bg=c["surface"],
                    fg=c["text"],
                    activebackground=c["surface_alt"],
                    activeforeground=c["text"],
                )
            except tk.TclError:
                pass

        if hasattr(self, "barra_estado"):
            try:
                self.barra_estado.configure(bg=c["surface"], fg=c["muted"])
            except tk.TclError:
                pass

        if hasattr(self, "info_panel"):
            try:
                self.info_panel.configure(bg=c["surface"], highlightbackground=c["border"])
                self.info_titulo.configure(bg=c["surface"], fg=c["text"])
                self.info_bd.configure(bg=c["surface"], fg=c["muted"])
                self.info_caja.configure(bg=c["surface"], fg=c["muted"])
                self.info_fecha.configure(bg=c["surface"], fg=c["muted"])
            except tk.TclError:
                pass

    def _alternar_tema(self) -> None:
        self._tema = "oscuro" if self._tema == "claro" else "claro"
        self.navegador.tema = self._tema
        self._aplicar_tema()

    # ------------------------------------------------------------------
    # VENTANA
    # ------------------------------------------------------------------
    def _ajustar_tamano_inicial(self) -> None:
        ancho_disponible = max(self._ancho_pantalla - 30, 900)
        alto_disponible = max(self._alto_pantalla - 70, 600)

        ancho = min(max(int(self._ancho_pantalla * 0.90), 1050), 1450, ancho_disponible)
        alto = min(max(int(alto_disponible * 0.90), 650), 850, alto_disponible)

        self._ancho_ventana = ancho
        self._alto_ventana = alto
        self.minsize(min(980, ancho), min(620, alto))

        x = max((self._ancho_pantalla - ancho) // 2, 0)
        y = max((self._alto_pantalla - alto) // 2, 0)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")

    # ------------------------------------------------------------------
    # HELPERS VISUALES
    # ------------------------------------------------------------------
    def _frame(self, parent: tk.Misc, key: str, **kwargs) -> tk.Frame:
        c = self._colores()
        frame = tk.Frame(parent, bg=c[key], bd=0, highlightthickness=0, **kwargs)
        self._tema_frames.append((frame, key))
        return frame

    def _label(self, parent: tk.Misc, text: str, fg: str = "text", bg: str = "surface", **kwargs) -> tk.Label:
        c = self._colores()
        label = tk.Label(parent, text=text, fg=c[fg], bg=c[bg], bd=0, **kwargs)
        self._tema_labels.append((label, fg, bg))
        return label

    def _crear_interfaz(self) -> None:
        c = self._colores()

        self._crear_botones_compatibilidad()

        self.contenedor = self._frame(self, "bg")
        self.contenedor.grid(row=0, column=0, sticky="nsew")
        self.contenedor.columnconfigure(0, weight=0)
        self.contenedor.columnconfigure(1, weight=1)
        self.contenedor.rowconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._crear_sidebar()
        self._crear_area_principal()

        self.barra_estado = tk.Label(
            self,
            textvariable=self.estado,
            anchor="w",
            padx=16,
            pady=6,
            font=("Segoe UI", 9),
            bd=0,
            highlightthickness=1,
            highlightbackground=c["border"],
        )
        self.barra_estado.grid(row=1, column=0, sticky="ew")

    def _crear_sidebar(self) -> None:
        c = self._colores()

        # Barra lateral fija: navegación rápida y estado de caja.
        sidebar = tk.Frame(
            self.contenedor,
            width=255,
            bg=c["sidebar"],
            bd=0,
            highlightthickness=0,
        )
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        self._tema_frames.append((sidebar, "sidebar"))

        # ------------------------------------------------------------------
        # Logo
        # ------------------------------------------------------------------
        self.logo_box = tk.Frame(
            sidebar,
            bg=c["logo_bg"],
            bd=0,
            highlightthickness=0,
        )
        self.logo_box.pack(fill="x", padx=14, pady=(16, 16))

        ruta_logo = Path(__file__).resolve().parent.parent / "assets" / "logo_dona_elina.png"
        try:
            if ruta_logo.exists():
                self._logo_img = tk.PhotoImage(file=str(ruta_logo))
                if self._logo_img.width() > 215:
                    factor = max(1, self._logo_img.width() // 215)
                    self._logo_img = self._logo_img.subsample(factor, factor)
                self.logo_label = tk.Label(
                    self.logo_box,
                    image=self._logo_img,
                    bg=c["logo_bg"],
                    bd=0,
                )
                self.logo_label.pack(padx=8, pady=8)
            else:
                self.logo_label = tk.Label(
                    self.logo_box,
                    text="Doña Elina",
                    font=("Segoe Script", 24, "bold"),
                    fg=c["burgundy"],
                    bg=c["logo_bg"],
                    bd=0,
                )
                self.logo_label.pack(pady=24)
        except Exception:
            self.logo_label = tk.Label(
                self.logo_box,
                text="Doña Elina",
                font=("Segoe Script", 24, "bold"),
                fg=c["burgundy"],
                bg=c["logo_bg"],
                bd=0,
            )
            self.logo_label.pack(pady=24)

        # ------------------------------------------------------------------
        # Título de navegación
        # ------------------------------------------------------------------
        titulo = self._label(
            sidebar,
            "ACCESOS RÁPIDOS",
            fg="gold",
            bg="sidebar",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        titulo.pack(fill="x", padx=22, pady=(2, 7))

        linea = tk.Frame(sidebar, height=1, bg=c["gold"], bd=0)
        linea.pack(fill="x", padx=20, pady=(0, 11))
        self._tema_lines.append((linea, "gold"))

        # ------------------------------------------------------------------
        # Menú rápido
        # ------------------------------------------------------------------
        opciones = (
            ("＋", "Nuevo pedido", self._nuevo_pedido),
            ("☷", "Lista de precios", self._abrir_reporte_precios),
            ("▰", "Salidas y Entregas", self._abrir_salidas),
            ("⚙", "Configuración", lambda: self._funcion_pendiente("Configuración")),
        )

        for icono, texto, comando in opciones:
            boton = tk.Button(
                sidebar,
                text=f"{icono}   {texto}",
                command=comando,
                anchor="w",
                font=("Segoe UI", 10, "bold"),
                bd=0,
                relief="flat",
                padx=18,
                pady=11,
                cursor="hand2",
                highlightthickness=1,
                highlightbackground=c["sidebar_border"],
                highlightcolor=c["gold"],
            )
            boton.pack(fill="x", padx=12, pady=2)
            self._tema_buttons.append((boton, "sidebar"))
            self._agregar_hover(boton)

        linea2 = tk.Frame(sidebar, height=1, bg=c["gold"], bd=0)
        linea2.pack(fill="x", padx=20, pady=(15, 10))
        self._tema_lines.append((linea2, "gold"))

        # Salir queda como acción independiente, antes del estado de caja.
        salir = tk.Button(
            sidebar,
            text="⇥   Salir",
            command=self.destroy,
            anchor="w",
            font=("Segoe UI", 10, "bold"),
            bd=0,
            relief="flat",
            padx=18,
            pady=11,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=c["sidebar_border"],
            highlightcolor=c["gold"],
        )
        salir.pack(fill="x", padx=12, pady=(0, 10))
        self._tema_buttons.append((salir, "sidebar"))
        self._agregar_hover(salir)

        # ------------------------------------------------------------------
        # Estado de caja
        # ------------------------------------------------------------------
        self.caja_status = tk.Frame(
            sidebar,
            bg=c["sidebar_hover"],
            bd=0,
            highlightthickness=1,
            highlightbackground=c["sidebar_border"],
        )
        self.caja_status.pack(fill="x", padx=14, pady=(0, 8))

        self.caja_icon = tk.Label(
            self.caja_status,
            text="▣",
            font=("Segoe UI Symbol", 22, "bold"),
            bg=c["sidebar_hover"],
            fg=c["muted"],
            bd=0,
        )
        self.caja_icon.grid(row=0, column=0, rowspan=3, padx=(11, 8), pady=10)

        self.caja_titulo = tk.Label(
            self.caja_status,
            text="Estado de Caja",
            font=("Segoe UI", 9, "bold"),
            bg=c["sidebar_hover"],
            fg=c["white"],
            anchor="w",
            bd=0,
        )
        self.caja_titulo.grid(row=0, column=1, sticky="w", pady=(9, 0), padx=(0, 8))

        self.caja_valor = tk.Label(
            self.caja_status,
            text="CERRADA",
            font=("Segoe UI", 12, "bold"),
            bg=c["sidebar_hover"],
            fg=c["danger"],
            anchor="w",
            bd=0,
        )
        self.caja_valor.grid(row=1, column=1, sticky="w", padx=(0, 8))

        self.caja_sub = tk.Label(
            self.caja_status,
            text="Abrí la caja para comenzar",
            font=("Segoe UI", 8),
            bg=c["sidebar_hover"],
            fg="#c6aeb4",
            anchor="w",
            bd=0,
        )
        self.caja_sub.grid(row=2, column=1, sticky="w", pady=(1, 9), padx=(0, 8))

        self.caja_status.columnconfigure(1, weight=1)

        # Pie fijo al fondo.
        pie = self._label(
            sidebar,
            "Doña Elina - Sistema de Gestión\nVersión 1.0.0",
            fg="gold",
            bg="sidebar",
            font=("Segoe UI", 7),
            justify="left",
            anchor="w",
        )
        pie.pack(side="bottom", fill="x", padx=20, pady=(0, 12))

    def _agregar_hover(self, boton: tk.Button) -> None:
        """Hover visual para el menú lateral, sin alterar ninguna lógica."""
        def entrar(_event=None) -> None:
            try:
                boton.configure(bg=self._colores()["sidebar_hover"])
            except tk.TclError:
                pass

        def salir(_event=None) -> None:
            try:
                boton.configure(bg=self._colores()["sidebar"])
            except tk.TclError:
                pass

        boton.bind("<Enter>", entrar)
        boton.bind("<Leave>", salir)

    def _crear_area_principal(self) -> None:
        c = self._colores()
        area = self._frame(self.contenedor, "bg")
        area.grid(row=0, column=1, sticky="nsew", padx=(22, 22), pady=(20, 16))
        area.columnconfigure(0, weight=1)
        area.rowconfigure(1, weight=1)

        # Encabezado limpio: eliminamos el título "Dashboard" y dejamos
        # el mensaje de bienvenida como encabezado principal.
        encabezado = self._frame(area, "surface")
        encabezado.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        encabezado.columnconfigure(0, weight=1)
        encabezado.configure(highlightthickness=0)

        bienvenida = self._label(
            encabezado,
            "Bienvenido al sistema de gestión",
            fg="text",
            bg="surface",
            font=("Segoe UI", 19, "bold"),
            anchor="w",
        )
        bienvenida.grid(row=0, column=0, sticky="w", padx=(16, 8), pady=(11, 4))

        detalle = self._label(
            encabezado,
            "Seleccioná una opción para comenzar",
            fg="muted",
            bg="surface",
            font=("Segoe UI", 9),
            anchor="w",
        )
        detalle.grid(row=1, column=0, sticky="w", padx=(17, 8), pady=(0, 11))

        derecha = self._frame(encabezado, "surface")
        derecha.grid(row=0, column=1, rowspan=2, sticky="e", padx=14)

        self.lbl_conexion = self._label(derecha, "●  Conectado", fg="success", bg="panel", font=("Segoe UI", 9, "bold"))
        self.lbl_conexion.pack(side="left", padx=(0, 14))

        self.btn_tema = tk.Button(
            derecha,
            text="☾  Modo oscuro",
            command=self._alternar_tema,
            font=("Segoe UI", 9, "bold"),
            bd=0,
            relief="flat",
            padx=12,
            pady=7,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=c["border"],
        )
        self.btn_tema.pack(side="left")

        # Contenedor de tarjetas.
        cuerpo = self._frame(area, "bg")
        cuerpo.grid(row=1, column=0, sticky="nsew")
        for col in range(3):
            cuerpo.columnconfigure(col, weight=1, uniform="cards")
        for row in range(2):
            cuerpo.rowconfigure(row, weight=1, uniform="card_rows")

        self._crear_tarjeta(cuerpo, 0, 0, "▣", "Caja", "Administración de caja", ["Abrir caja", "Ver caja abierta", "Cerrar caja", "Caja chica"], "Ir a Caja", self._abrir_modulo_caja, "gold")
        self._crear_tarjeta(cuerpo, 0, 1, "☷", "Pedidos", "Gestión de pedidos", ["Nuevo pedido", "Proyectados", "Por entregar", "Salidas / Entregas", "Cobros"], "Ir a Pedidos", self._abrir_modulo_pedidos, "burgundy")
        self._crear_tarjeta(cuerpo, 0, 2, "▰", "Reparto", "Entregas y logística", ["Pedidos por entregar", "Entregas del día", "Historial de entregas"], "Ir a Reparto", lambda: self._funcion_pendiente("Reparto"), "green")
        self._crear_tarjeta(cuerpo, 1, 0, "▤", "Cobros", "Cobros y cuentas corrientes", ["Buscar cliente", "Ventas pendientes", "Registrar cobros", "Historial de cobros"], "Ir a Cobros", self._abrir_cobros, "blue")
        self._crear_tarjeta(cuerpo, 1, 1, "▥", "Proyectados / Stock", "Producción y stock", ["Stock actual", "Proyectados", "Planificación", "Movimientos de stock"], "Ir a Stock", self._abrir_stock, "purple", colspan=2)

        # Franja informativa inferior.
        self.info_panel = tk.Frame(area, bg=c["surface"], bd=0, highlightthickness=1, highlightbackground=c["border"])
        self.info_panel.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.info_titulo = tk.Label(self.info_panel, text="Información del sistema", font=("Segoe UI", 8, "bold"), bg=c["surface"], fg=c["text"], bd=0)
        self.info_titulo.pack(side="left", padx=(14, 8), pady=8)
        self.info_bd = tk.Label(self.info_panel, text="Base de datos: Produccion", font=("Segoe UI", 8), bg=c["surface"], fg=c["muted"], bd=0)
        self.info_bd.pack(side="left", padx=8)
        self.info_caja = tk.Label(self.info_panel, text="Caja: cerrada", font=("Segoe UI", 8), bg=c["surface"], fg=c["muted"], bd=0)
        self.info_caja.pack(side="left", padx=8)
        self.info_fecha = tk.Label(self.info_panel, text="", font=("Segoe UI", 8), bg=c["surface"], fg=c["muted"], bd=0)
        self.info_fecha.pack(side="right", padx=14)
        self._actualizar_fecha_hora()

    def _crear_tarjeta(
        self,
        parent: tk.Misc,
        row: int,
        column: int,
        icono: str,
        titulo: str,
        subtitulo: str,
        items: list[str],
        texto_boton: str,
        comando,
        color_key: str,
        colspan: int = 1,
    ) -> None:
        c = self._colores()
        card = tk.Frame(parent, bg=c["surface"], bd=0, highlightthickness=1, highlightbackground=c["border"])
        card.grid(row=row, column=column, columnspan=colspan, sticky="nsew", padx=6, pady=6)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)

        top = tk.Frame(card, bg=c["surface"], bd=0)
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 0))
        top.columnconfigure(1, weight=1)

        icon = tk.Label(top, text=icono, font=("Segoe UI Symbol", 25, "bold"), fg=c[color_key], bg=c["surface"], bd=0)
        icon.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 11))

        title_box = tk.Frame(top, bg=c["surface"], bd=0)
        title_box.grid(row=0, column=1, sticky="ew")
        title = tk.Label(title_box, text=titulo, font=("Segoe UI", 16, "bold"), fg=c[color_key], bg=c["surface"], anchor="w", bd=0)
        title.pack(anchor="w")
        subtitle = tk.Label(title_box, text=subtitulo, font=("Segoe UI", 8), fg=c["muted"], bg=c["surface"], anchor="w", bd=0)
        subtitle.pack(anchor="w", pady=(1, 0))

        line = tk.Frame(card, height=2, bg=c[color_key], bd=0)
        line.grid(row=1, column=0, sticky="ew", padx=16, pady=(9, 5))

        lista = tk.Frame(card, bg=c["surface"], bd=0)
        lista.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 4))
        for item in items:
            lbl = tk.Label(lista, text=f"•  {item}", font=("Segoe UI", 8), fg=c["text"], bg=c["surface"], anchor="w", bd=0)
            lbl.pack(fill="x", pady=2)

        boton = tk.Button(
            card,
            text=f"{texto_boton}   →",
            command=comando,
            font=("Segoe UI", 9, "bold"),
            bd=0,
            relief="flat",
            padx=10,
            pady=7,
            cursor="hand2",
        )
        boton.grid(row=3, column=0, sticky="ew", padx=16, pady=(6, 13))

        self._tarjetas.append({
            "card": card,
            "top": top,
            "title_box": title_box,
            "list": lista,
            "icon": icon,
            "title": title,
            "subtitle": subtitle,
            "items": [w for w in lista.winfo_children()],
            "button": boton,
            "line": line,
            "color": color_key,
        })

    def _actualizar_fecha_hora(self) -> None:
        try:
            from datetime import datetime
            self.info_fecha.configure(text=datetime.now().strftime("%d/%m/%Y   %H:%M"))
            self.after(30000, self._actualizar_fecha_hora)
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # COMPATIBILIDAD: conserva referencias que utiliza la lógica existente.
    # ------------------------------------------------------------------
    def _crear_botones_compatibilidad(self) -> None:
        comandos = {
            "btn_abrir_caja": self._abrir_caja,
            "btn_nuevo_pedido": self._nuevo_pedido,
            "btn_pedidos_proyectados": self._abrir_pedidos_proyectados,
            "btn_planificacion": self._abrir_planificacion,
            "btn_confirmar_elaboracion": self._abrir_confirmar_elaboracion,
            "btn_salidas_entregas": self._abrir_salidas,
            "btn_reporte_pedidos": self._abrir_reporte_pedidos,
            "btn_cobros": self._abrir_cobros,
            "btn_stock": self._abrir_stock,
            "btn_caja_chica": self._abrir_caja_chica,
            "btn_reporte_precios": self._abrir_reporte_precios,
            "btn_cerrar_caja": self._cerrar_caja,
        }
        for nombre, comando in comandos.items():
            boton = tk.Button(self, command=comando)
            setattr(self, nombre, boton)

    # ------------------------------------------------------------------
    # CONEXIÓN / ESTADO DE CAJA
    # ------------------------------------------------------------------
    def _comprobar_conexion(self) -> None:
        try:
            self.datos_conexion = probar_conexion()
            self.conexion_disponible = True
            self.lbl_conexion.configure(text="●  Conectado")
            self._mostrar_estado_general()
            self._aplicar_tema()
        except Exception as error:
            self.conexion_disponible = False
            self.estado.set("Sin conexión con SQL Server")
            self.lbl_conexion.configure(text="●  Sin conexión")
            messagebox.showerror(
                "Conexión",
                "No se pudo conectar con SQL Server.\n\n" f"{error}",
                parent=self,
            )
            self._deshabilitar_operaciones()
            self._aplicar_tema()

    def _mostrar_estado_general(self) -> None:
        if not self.datos_conexion:
            return
        texto = f"Conectado a {self.datos_conexion['servidor']} · Base: {self.datos_conexion['base_datos']}"
        if self.sesion_caja:
            descripcion = obtener_valor(self.sesion_caja, "caja_descripcion", "descripcion_caja", "descripcion", predeterminado="Caja abierta")
            id_sesion = obtener_valor(self.sesion_caja, "id_caja_sesion", predeterminado="-")
            texto += f" · {descripcion} · Sesión: {id_sesion}"
        else:
            texto += " · Caja cerrada"
        self.estado.set(texto)

    def _actualizar_estado_caja(self) -> bool:
        try:
            sesion_actual = obtener_sesion_abierta()
        except Exception as error:
            messagebox.showerror("Caja", "No se pudo comprobar el estado de la caja.\n\n" f"{error}", parent=self)
            return False

        self.sesion_caja = sesion_actual
        self.btn_abrir_caja.configure(state="normal")
        self.btn_cerrar_caja.configure(state="normal" if self.sesion_caja else "disabled")

        if hasattr(self, "caja_valor"):
            c = self._colores()
            self.caja_valor.configure(text="ABIERTA" if self.sesion_caja else "CERRADA", fg=c["success"] if self.sesion_caja else c["danger"])
            self.caja_sub.configure(text="Caja lista para operar" if self.sesion_caja else "Abrí la caja para comenzar")
            self.caja_icon.configure(fg=c["gold"] if self.sesion_caja else c["muted"])
            self.info_caja.configure(text="Caja: abierta" if self.sesion_caja else "Caja: cerrada")
        self._mostrar_estado_general()
        return True

    def _abrir_modulo_caja(self) -> None:
        """Abre el panel visual del módulo Caja."""
        self.navegador.abrir_caja()

    def _abrir_caja(self) -> None:
        if not self._actualizar_estado_caja():
            return
        if self.sesion_caja:
            self._mostrar_sesion_abierta()
            return
        VentanaAperturaCaja(self, al_abrir=self._caja_abierta_correctamente)

    def _caja_abierta_correctamente(self, _id_sesion: int) -> None:
        self._actualizar_estado_caja()

    def _mostrar_sesion_abierta(self) -> None:
        if not self.sesion_caja:
            return
        id_sesion = obtener_valor(self.sesion_caja, "id_caja_sesion", predeterminado="-")
        caja = obtener_valor(self.sesion_caja, "caja_descripcion", "descripcion_caja", "descripcion", predeterminado="Caja")
        usuario = obtener_valor(self.sesion_caja, "usuario_apertura", "usuario", predeterminado="-")
        fecha = obtener_valor(self.sesion_caja, "fecha_apertura", predeterminado="-")
        saldo = obtener_valor(self.sesion_caja, "saldo_inicial", predeterminado=0)
        messagebox.showinfo(
            "Caja abierta",
            f"Caja: {caja}\nSesión: {id_sesion}\nUsuario: {usuario}\nApertura: {fecha}\nSaldo inicial: {formato_moneda(saldo)}",
            parent=self,
        )

    def _deshabilitar_operaciones(self) -> None:
        botones = (
            self.btn_abrir_caja,
            self.btn_nuevo_pedido,
            self.btn_planificacion,
            self.btn_cobros,
            self.btn_confirmar_elaboracion,
            self.btn_salidas_entregas,
            self.btn_cerrar_caja,
            self.btn_reporte_pedidos,
            self.btn_stock,
            self.btn_reporte_precios,
        )
        for boton in botones:
            try:
                boton.configure(state="disabled")
            except tk.TclError:
                pass
        for tarjeta in self._tarjetas:
            try:
                tarjeta["button"].configure(state="disabled")
            except tk.TclError:
                pass

    def _funcion_pendiente(self, titulo: str) -> None:
        messagebox.showinfo(titulo, "Esta función será incorporada en el próximo paso.", parent=self)

    # ------------------------------------------------------------------
    # NAVEGACIÓN EXISTENTE — NO SE MODIFICA LA LÓGICA DE BD.
    # ------------------------------------------------------------------
    def _abrir_reporte_precios(self) -> None:
        self.navegador.abrir_reporte_precios()

    def _abrir_stock(self) -> None:
        self.navegador.abrir_stock()

    def _abrir_reporte_pedidos(self) -> None:
        self.navegador.abrir_reporte_pedidos()

    def _cerrar_caja(self) -> None:
        if not self._actualizar_estado_caja():
            return
        if not self.sesion_caja:
            messagebox.showinfo("Cerrar caja", "No hay una sesión de caja abierta.", parent=self)
            return
        self.navegador.abrir_cierre_caja()

    def _abrir_modulo_pedidos(self) -> None:
        self.navegador.abrir_pedidos()

    def _nuevo_pedido(self) -> None:
        self.navegador.abrir_pedido()

    def _abrir_pedidos_proyectados(self) -> None:
        self.navegador.abrir_pedidos_proyectados()

    def _abrir_planificacion(self) -> None:
        self.navegador.abrir_planificacion()

    def _abrir_confirmar_elaboracion(self) -> None:
        self.navegador.abrir_elaboracion()

    def _abrir_salidas(self) -> None:
        self.navegador.abrir_salidas()

    def _abrir_cobros(self) -> None:
        self.navegador.abrir_cobros()

    def _abrir_caja_chica(self) -> None:
        self.navegador.abrir_caja_chica()
