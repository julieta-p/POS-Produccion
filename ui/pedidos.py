from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox


PALETA_CLARO = {
    "bg": "#f3f1ef",
    "surface": "#ffffff",
    "surface2": "#faf8f7",
    "border": "#ddd7d4",
    "text": "#252328",
    "muted": "#6d6870",
    "sidebar": "#3a111b",
    "sidebar_hover": "#511522",
    "gold": "#c99624",
    "burgundy": "#b93657",
    "burgundy_dark": "#8e2440",
    "white": "#ffffff",
}

PALETA_OSCURO = {
    "bg": "#15171b",
    "surface": "#20242a",
    "surface2": "#292e35",
    "border": "#3b414a",
    "text": "#f3f4f6",
    "muted": "#aeb5bf",
    "sidebar": "#321019",
    "sidebar_hover": "#4a1723",
    "gold": "#d5a63a",
    "burgundy": "#c33b5c",
    "burgundy_dark": "#982a45",
    "white": "#ffffff",
}


class VentanaPedidos(tk.Toplevel):
    """Panel principal visual del módulo Pedidos.

    Esta pantalla organiza accesos a los módulos existentes. No cambia
    tablas, datos ni procedimientos de SQL Server.
    """

    def __init__(self, parent: tk.Misc, navegador) -> None:
        super().__init__(parent)
        self.navegador = navegador
        self._tema = getattr(navegador, "tema", "claro")
        self._logo_img: tk.PhotoImage | None = None
        self._botones: list[tk.Button] = []
        self._botones_info: list[tuple[tk.Button, str]] = []
        self._tarjetas: list[dict] = []

        self.title("Pedidos - Doña Elina")
        self.minsize(1050, 650)
        self.geometry("1200x760")
        self.resizable(True, True)

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._crear_interfaz()
        self._aplicar_tema()

    def colores(self) -> dict[str, str]:
        return PALETA_OSCURO if self._tema == "oscuro" else PALETA_CLARO

    # ------------------------------------------------------------------
    # INTERFAZ
    # ------------------------------------------------------------------
    def _crear_interfaz(self) -> None:
        self._crear_sidebar()
        self._crear_contenido()

    def _crear_sidebar(self) -> None:
        c = self.colores()
        self.sidebar = tk.Frame(self, bg=c["sidebar"], width=265)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        logo_box = tk.Frame(self.sidebar, bg="#fff9f9", bd=0)
        logo_box.pack(fill="x", padx=14, pady=(16, 14))
        self.logo_box = logo_box

        ruta = Path(__file__).resolve().parent.parent / "assets" / "logo_dona_elina.png"
        try:
            self._logo_img = tk.PhotoImage(file=str(ruta))
            if self._logo_img.width() > 215:
                factor = max(1, self._logo_img.width() // 215)
                self._logo_img = self._logo_img.subsample(factor, factor)
            self.logo_label = tk.Label(logo_box, image=self._logo_img, bg="#fff9f9", bd=0)
            self.logo_label.pack(padx=8, pady=8)
        except Exception:
            self.logo_label = tk.Label(
                logo_box, text="Doña Elina", font=("Segoe Script", 24, "bold"),
                fg=c["burgundy"], bg="#fff9f9", bd=0,
            )
            self.logo_label.pack(pady=25)

        self._titulo_sidebar("ACCESOS RÁPIDOS")
        self._sidebar_button("＋", "Nuevo pedido", lambda: self.navegador.abrir_pedido(self))
        self._sidebar_button("☷", "Lista de precios", lambda: self.navegador.abrir_reporte_precios(self))
        self._sidebar_button("▰", "Salidas y Entregas", lambda: self.navegador.abrir_salidas(self))
        self._sidebar_button("⚙", "Configuración", self._configuracion)

        self._linea_sidebar()
        self._titulo_sidebar("MENÚ PRINCIPAL")
        self._sidebar_button("⌂", "Dashboard", lambda: self.navegador.volver_menu(self), selected=False)
        self._sidebar_button("▣", "Caja", lambda: self.navegador.abrir_caja(self), selected=False)
        self._sidebar_button("🛒", "Pedidos", lambda: None, selected=True)
        self._sidebar_button("▰", "Reparto", lambda: self._pendiente("Reparto"), selected=False)
        self._sidebar_button("▤", "Cobros", lambda: self.navegador.abrir_cobros(self), selected=False)
        self._sidebar_button("▥", "Reportes", lambda: self.navegador.abrir_reporte_pedidos(self), selected=False)
        self._sidebar_button("⚙", "Configuración", self._configuracion, selected=False)

        self._linea_sidebar()
        self._sidebar_button("⇥", "Salir", self._salir, selected=False)

        pie = tk.Label(
            self.sidebar,
            text="Doña Elina - Sistema de Gestión\nVersión 1.0.0",
            font=("Segoe UI", 8), anchor="w", justify="left", bd=0,
        )
        pie.pack(side="bottom", fill="x", padx=22, pady=16)
        self.pie = pie

    def _titulo_sidebar(self, texto: str) -> None:
        c = self.colores()
        label = tk.Label(
            self.sidebar, text=texto, font=("Segoe UI", 10, "bold"),
            fg=c["gold"], bg=c["sidebar"], anchor="w", bd=0,
        )
        label.pack(fill="x", padx=22, pady=(4, 7))
        linea = tk.Frame(self.sidebar, height=1, bg=c["gold"], bd=0)
        linea.pack(fill="x", padx=20, pady=(0, 8))
        self._botones_info.append((label, "sidebar"))
        self._botones_info.append((linea, "gold"))

    def _linea_sidebar(self) -> None:
        c = self.colores()
        linea = tk.Frame(self.sidebar, height=1, bg=c["gold"], bd=0)
        linea.pack(fill="x", padx=20, pady=(9, 8))
        self._botones_info.append((linea, "gold"))

    def _sidebar_button(self, icono: str, texto: str, comando, *, selected: bool = False) -> None:
        c = self.colores()
        boton = tk.Button(
            self.sidebar,
            text=f"  {icono}   {texto}",
            command=comando,
            anchor="w",
            font=("Segoe UI", 10, "bold"),
            bg=c["sidebar_hover"] if selected else c["sidebar"],
            fg=c["white"],
            activebackground=c["sidebar_hover"],
            activeforeground=c["white"],
            bd=0,
            relief="flat",
            padx=12,
            pady=9,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=c["burgundy"] if selected else c["sidebar"],
        )
        boton.pack(fill="x", padx=12, pady=2)
        boton._selected = selected
        self._botones.append(boton)
        self._bind_hover(boton, selected)

    def _bind_hover(self, boton: tk.Button, selected: bool = False) -> None:
        def entrar(_event=None):
            c = self.colores()
            boton.configure(bg=c["sidebar_hover"], activebackground=c["sidebar_hover"])

        def salir(_event=None):
            c = self.colores()
            boton.configure(bg=c["sidebar_hover"] if selected else c["sidebar"])

        boton.bind("<Enter>", entrar)
        boton.bind("<Leave>", salir)
        boton.bind("<ButtonRelease-1>", lambda _e: boton.after(80, salir))

    # ------------------------------------------------------------------
    # CONTENIDO
    # ------------------------------------------------------------------
    def _crear_contenido(self) -> None:
        c = self.colores()
        self.area = tk.Frame(self, bg=c["bg"])
        self.area.grid(row=0, column=1, sticky="nsew", padx=22, pady=20)
        self.area.columnconfigure(0, weight=1)
        self.area.rowconfigure(1, weight=1)

        encabezado = tk.Frame(
            self.area, bg=c["surface"], bd=0,
            highlightthickness=1, highlightbackground=c["border"],
        )
        encabezado.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        encabezado.columnconfigure(1, weight=1)
        self.encabezado = encabezado

        titulo = tk.Label(
            encabezado, text="🛒  Pedidos", font=("Segoe UI", 27, "bold"),
            fg=c["text"], bg=c["surface"], anchor="w",
        )
        titulo.grid(row=0, column=0, padx=(22, 8), pady=(17, 0), sticky="w")
        self.titulo = titulo

        subtitulo = tk.Label(
            encabezado, text="Gestioná tus pedidos de manera rápida y sencilla",
            font=("Segoe UI", 10), fg=c["muted"], bg=c["surface"], anchor="w",
        )
        subtitulo.grid(row=1, column=0, padx=(24, 8), pady=(0, 15), sticky="w")
        self.subtitulo = subtitulo

        self.btn_tema = tk.Button(
            encabezado,
            text="☾  Modo oscuro",
            command=self._alternar_tema,
            font=("Segoe UI", 9, "bold"),
            bd=0, relief="flat", padx=12, pady=7,
            cursor="hand2", highlightthickness=1,
            highlightbackground=c["border"],
        )
        self.btn_tema.grid(row=0, column=2, rowspan=2, padx=(10, 18), pady=10)

        cuerpo = tk.Frame(self.area, bg=c["bg"])
        cuerpo.grid(row=1, column=0, sticky="nsew")
        for col in range(2):
            cuerpo.columnconfigure(col, weight=1, uniform="pedido_cards")
        for row in range(2):
            cuerpo.rowconfigure(row, weight=1, uniform="pedido_rows")
        self.cuerpo = cuerpo

        self._crear_tarjeta(cuerpo, 0, 0, "＋", "Nuevo Pedido", "Creá un nuevo pedido para tu cliente", self._nuevo_pedido)
        self._crear_tarjeta(cuerpo, 0, 1, "▤", "Por Entregar", "Consultá los pedidos listos para entregar", self._por_entregar)
        self._crear_tarjeta(cuerpo, 1, 0, "▰", "Salida / Entregas", "Gestioná las salidas y entregas realizadas", self._salidas)
        self._crear_tarjeta(cuerpo, 1, 1, "$", "Cobros", "Registrá y consultá los cobros de pedidos", self._cobros)

        resumen = tk.Frame(
            self.area, bg=c["surface"], bd=0,
            highlightthickness=1, highlightbackground=c["border"],
        )
        resumen.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        self.resumen = resumen
        self._crear_resumen_item(resumen, 0, "▤", "Pedidos", "Gestionalos desde las opciones superiores")
        self._crear_resumen_item(resumen, 1, "▰", "Entregas", "Pedidos pendientes de salida")
        self._crear_resumen_item(resumen, 2, "$", "Cobros", "Acceso a cuentas y cobros")

    def _crear_tarjeta(self, parent, row: int, column: int, icono: str, titulo: str, descripcion: str, comando) -> None:
        c = self.colores()
        card = tk.Frame(
            parent, bg=c["surface"], bd=0,
            highlightthickness=1, highlightbackground=c["border"],
            cursor="hand2",
        )
        card.grid(row=row, column=column, sticky="nsew", padx=7, pady=7)
        card.columnconfigure(1, weight=1)
        card.rowconfigure(0, weight=1)

        icon_box = tk.Frame(card, bg=c["burgundy_dark"], width=72, height=72, bd=0)
        icon_box.grid(row=0, column=0, padx=(18, 14), pady=18)
        icon_box.grid_propagate(False)
        icon = tk.Label(icon_box, text=icono, font=("Segoe UI Symbol", 28, "bold"), fg=c["white"], bg=c["burgundy_dark"])
        icon.pack(expand=True)

        texts = tk.Frame(card, bg=c["surface"])
        texts.grid(row=0, column=1, sticky="nsew", pady=16)
        texts.columnconfigure(0, weight=1)
        tk.Label(texts, text=titulo, font=("Segoe UI", 16, "bold"), fg=c["text"], bg=c["surface"], anchor="w").grid(row=0, column=0, sticky="ew", pady=(5, 2))
        tk.Label(texts, text=descripcion, font=("Segoe UI", 9), fg=c["muted"], bg=c["surface"], anchor="w", justify="left", wraplength=260).grid(row=1, column=0, sticky="ew")

        flecha = tk.Label(card, text="›", font=("Segoe UI", 28), fg=c["muted"], bg=c["surface"])
        flecha.grid(row=0, column=2, padx=(8, 18))

        for widget in (card, icon_box, icon, texts, flecha):
            widget.bind("<Button-1>", lambda _e, cmd=comando: cmd())
            widget.bind("<Enter>", lambda _e, box=card: self._card_hover(box, True))
            widget.bind("<Leave>", lambda _e, box=card: self._card_hover(box, False))

        self._tarjetas.append({"card": card, "icon_box": icon_box, "icon": icon, "texts": texts, "flecha": flecha})

    def _crear_resumen_item(self, parent, column: int, icono: str, titulo: str, texto: str) -> None:
        c = self.colores()
        parent.columnconfigure(column, weight=1)
        item = tk.Frame(parent, bg=c["surface"])
        item.grid(row=0, column=column, sticky="nsew", padx=8, pady=8)
        if column > 0:
            sep = tk.Frame(parent, bg=c["border"], width=1)
            sep.grid(row=0, column=column, sticky="nsw", pady=10)
        tk.Label(item, text=icono, font=("Segoe UI Symbol", 20, "bold"), fg=c["burgundy"], bg=c["surface"]).pack(side="left", padx=(10, 8))
        tk.Label(item, text=titulo, font=("Segoe UI", 9, "bold"), fg=c["text"], bg=c["surface"]).pack(anchor="w", pady=(7, 0))
        tk.Label(item, text=texto, font=("Segoe UI", 8), fg=c["muted"], bg=c["surface"], wraplength=220, justify="left").pack(anchor="w", pady=(0, 7))

    def _card_hover(self, card, activo: bool) -> None:
        c = self.colores()
        try:
            card.configure(highlightbackground=c["burgundy"] if activo else c["border"])
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # TEMA
    # ------------------------------------------------------------------
    def _alternar_tema(self) -> None:
        self._tema = "oscuro" if self._tema == "claro" else "claro"
        self.navegador.tema = self._tema
        self._aplicar_tema()

    def _aplicar_tema(self) -> None:
        c = self.colores()
        self.configure(bg=c["bg"])
        self.sidebar.configure(bg=c["sidebar"])
        self.logo_box.configure(bg="#fff9f9")
        self.logo_label.configure(bg="#fff9f9")
        self.area.configure(bg=c["bg"])
        self.encabezado.configure(bg=c["surface"], highlightbackground=c["border"])
        self.titulo.configure(bg=c["surface"], fg=c["text"])
        self.subtitulo.configure(bg=c["surface"], fg=c["muted"])
        self.btn_tema.configure(
            text="☾  Modo oscuro" if self._tema == "claro" else "☀  Modo claro",
            bg=c["surface"],
            fg=c["text"],
            activebackground=c["surface2"],
            activeforeground=c["text"],
            highlightbackground=c["border"],
        )
        self.cuerpo.configure(bg=c["bg"])
        self.resumen.configure(bg=c["surface"], highlightbackground=c["border"])

        for widget, tipo in self._botones_info:
            try:
                widget.configure(bg=c[tipo])
                if tipo == "sidebar":
                    widget.configure(fg=c["gold"])
            except (tk.TclError, KeyError):
                pass

        for boton in self._botones:
            try:
                selected = getattr(boton, "_selected", False)
                boton.configure(
                    bg=c["sidebar_hover"] if selected else c["sidebar"],
                    fg=c["white"], activebackground=c["sidebar_hover"], activeforeground=c["white"],
                    highlightbackground=c["burgundy"] if selected else c["sidebar"],
                )
            except tk.TclError:
                pass
        self.pie.configure(bg=c["sidebar"], fg=c["gold"])

        for tarjeta in self._tarjetas:
            try:
                tarjeta["card"].configure(bg=c["surface"], highlightbackground=c["border"])
                tarjeta["icon_box"].configure(bg=c["burgundy_dark"])
                tarjeta["icon"].configure(bg=c["burgundy_dark"], fg=c["white"])
                tarjeta["texts"].configure(bg=c["surface"])
                for hijo in tarjeta["texts"].winfo_children():
                    hijo.configure(bg=c["surface"])
                    if hijo.winfo_class() == "Label":
                        hijo.configure(fg=c["text"] if hijo.cget("font")[0:2] else c["text"])
                tarjeta["flecha"].configure(bg=c["surface"], fg=c["muted"])
            except (tk.TclError, TypeError):
                pass

        # El resumen contiene etiquetas creadas sin guardar referencias.
        self._recolor_descendientes(self.resumen, c)

    def _recolor_descendientes(self, widget, c) -> None:
        try:
            clase = widget.winfo_class()
            if clase == "Frame":
                widget.configure(bg=c["surface"])
            elif clase == "Label":
                widget.configure(bg=c["surface"], fg=c["text"])
        except tk.TclError:
            return
        for hijo in widget.winfo_children():
            self._recolor_descendientes(hijo, c)

    # ------------------------------------------------------------------
    # ACCIONES
    # ------------------------------------------------------------------
    def _nuevo_pedido(self) -> None:
        self.navegador.abrir_pedido(self)

    def _por_entregar(self) -> None:
        self.navegador.abrir_reporte_pedidos(self)

    def _salidas(self) -> None:
        self.navegador.abrir_salidas(self)

    def _cobros(self) -> None:
        self.navegador.abrir_cobros(self)

    def _proyectados(self) -> None:
        self.navegador.abrir_pedidos_proyectados(self)

    def _reporte_pedidos(self) -> None:
        self.navegador.abrir_reporte_pedidos(self)

    def _configuracion(self) -> None:
        messagebox.showinfo("Configuración", "Esta función se mantiene para el próximo módulo.", parent=self)

    def _pendiente(self, modulo: str) -> None:
        messagebox.showinfo(modulo, f"El módulo {modulo} lo dejamos para el final.", parent=self)

    def _salir(self) -> None:
        self.navegador.volver_menu(self)
