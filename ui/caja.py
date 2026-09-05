from __future__ import annotations

import tkinter as tk
from decimal import Decimal
from pathlib import Path
from tkinter import messagebox
from typing import Any

from db.caja_repository import obtener_sesion_abierta
from ui.caja_apertura import VentanaAperturaCaja


class VentanaCaja(tk.Toplevel):
    """Panel visual del módulo Caja.

    Este archivo solamente organiza la interfaz y reutiliza las operaciones
    de caja que ya existen en el proyecto. No modifica la estructura de la BD.
    """

    def __init__(self, parent: tk.Misc, navegador) -> None:
        super().__init__(parent)
        self.navegador = navegador
        self.sesion_caja: dict[str, Any] | None = None
        self._tema = getattr(navegador, "tema", "claro")
        self._logo_img: tk.PhotoImage | None = None

        self.title("Caja - Doña Elina")
        self.resizable(True, True)
        self.minsize(980, 620)
        self.geometry("1100x700")

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._crear_interfaz()
        self._actualizar_estado()

    def colores(self) -> dict[str, str]:
        if self._tema == "oscuro":
            return {
                "bg": "#15171b", "surface": "#20242a", "surface2": "#282d34",
                "border": "#3b414a", "text": "#f3f4f6", "muted": "#aeb5bf",
                "sidebar": "#321019", "sidebar_hover": "#4a1723", "gold": "#d5a63a",
                "success": "#55bd69", "danger": "#e05b68", "white": "#ffffff",
                "logo_bg": "#fff8f8",
            }
        return {
            "bg": "#f3f1ef", "surface": "#ffffff", "surface2": "#faf8f7",
            "border": "#ddd7d4", "text": "#252328", "muted": "#6d6870",
            "sidebar": "#3a111b", "sidebar_hover": "#511522", "gold": "#c99624",
            "success": "#3caa55", "danger": "#c94b57", "white": "#ffffff",
            "logo_bg": "#fff9f9",
        }

    def _crear_interfaz(self) -> None:
        c = self.colores()
        self.configure(bg=c["bg"])
        self._crear_sidebar()
        self._crear_contenido()

    def _crear_sidebar(self) -> None:
        c = self.colores()
        sidebar = tk.Frame(self, bg=c["sidebar"], width=245)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        box = tk.Frame(sidebar, bg=c["logo_bg"])
        box.pack(fill="x", padx=14, pady=(16, 14))
        ruta = Path(__file__).resolve().parent.parent / "assets" / "logo_dona_elina.png"
        try:
            self._logo_img = tk.PhotoImage(file=str(ruta))
            if self._logo_img.width() > 215:
                factor = max(1, self._logo_img.width() // 215)
                self._logo_img = self._logo_img.subsample(factor, factor)
            tk.Label(box, image=self._logo_img, bg=c["logo_bg"], bd=0).pack(padx=8, pady=8)
        except Exception:
            tk.Label(box, text="Doña Elina", font=("Segoe Script", 24, "bold"),
                     fg=c["danger"], bg=c["logo_bg"]).pack(pady=25)

        tk.Label(sidebar, text="ACCESOS RÁPIDOS", font=("Segoe UI", 10, "bold"),
                 fg=c["gold"], bg=c["sidebar"], anchor="w").pack(fill="x", padx=24, pady=(8, 7))
        tk.Frame(sidebar, height=1, bg=c["gold"]).pack(fill="x", padx=24)

        self._menu_button(sidebar, "+", "Nuevo pedido", lambda: self.navegador.abrir_pedido(self))
        self._menu_button(sidebar, "☷", "Lista de precios", lambda: self.navegador.abrir_reporte_precios(self))
        self._menu_button(sidebar, "▰", "Salidas y Entregas", lambda: self.navegador.abrir_salidas(self))
        self._menu_button(sidebar, "⚙", "Configuración", lambda: messagebox.showinfo("Configuración", "Esta función se mantiene para el próximo módulo.", parent=self))

        tk.Frame(sidebar, height=1, bg=c["gold"]).pack(fill="x", padx=24, pady=(10, 8))
        self._menu_button(sidebar, "‹", "Volver al inicio", lambda: self.navegador.volver_menu(self))
        self._menu_button(sidebar, "×", "Salir", self._salir)

    def _menu_button(self, parent, icono, texto, comando) -> None:
        c = self.colores()
        boton = tk.Button(parent, text=f"  {icono}   {texto}", command=comando,
                          anchor="w", font=("Segoe UI", 10, "bold"),
                          bg=c["sidebar"], fg=c["white"], activebackground=c["sidebar_hover"],
                          activeforeground=c["white"], bd=0, relief="flat", padx=14, pady=11,
                          cursor="hand2")
        boton.pack(fill="x", padx=12, pady=2)

    def _crear_contenido(self) -> None:
        c = self.colores()
        area = tk.Frame(self, bg=c["bg"])
        area.grid(row=0, column=1, sticky="nsew", padx=28, pady=24)
        area.columnconfigure(0, weight=1)
        area.rowconfigure(2, weight=1)

        encabezado = tk.Frame(area, bg=c["surface"], highlightthickness=1, highlightbackground=c["border"])
        encabezado.grid(row=0, column=0, sticky="ew")
        encabezado.columnconfigure(0, weight=1)
        tk.Label(encabezado, text="Caja", font=("Segoe UI", 27, "bold"),
                 fg=c["text"], bg=c["surface"], anchor="w").grid(row=0, column=0, padx=22, pady=(17, 0), sticky="w")
        tk.Label(encabezado, text="Administración de caja", font=("Segoe UI", 10),
                 fg=c["muted"], bg=c["surface"], anchor="w").grid(row=1, column=0, padx=22, pady=(0, 15), sticky="w")

        self.btn_tema = tk.Button(encabezado, text="☾  Modo oscuro", command=self._alternar_tema,
                                  font=("Segoe UI", 9, "bold"), bd=0, relief="flat",
                                  padx=12, pady=7, bg=c["surface2"], fg=c["text"], cursor="hand2")
        self.btn_tema.grid(row=0, column=1, rowspan=2, padx=18)

        self.estado_frame = tk.Frame(area, bg=c["surface2"], highlightthickness=1, highlightbackground=c["border"])
        self.estado_frame.grid(row=1, column=0, sticky="ew", pady=(14, 14))
        self.estado_icon = tk.Label(self.estado_frame, text="●", font=("Segoe UI", 20, "bold"), bg=c["surface2"], fg=c["danger"])
        self.estado_icon.pack(side="left", padx=(18, 10), pady=14)
        self.estado_titulo = tk.Label(self.estado_frame, text="Caja cerrada", font=("Segoe UI", 13, "bold"), bg=c["surface2"], fg=c["text"])
        self.estado_titulo.pack(side="left", pady=14)
        self.estado_detalle = tk.Label(self.estado_frame, text="Abrí la caja para comenzar a operar", font=("Segoe UI", 9), bg=c["surface2"], fg=c["muted"])
        self.estado_detalle.pack(side="left", padx=12, pady=14)

        cuerpo = tk.Frame(area, bg=c["bg"])
        cuerpo.grid(row=2, column=0, sticky="nsew")
        cuerpo.columnconfigure(0, weight=1, uniform="c")
        cuerpo.columnconfigure(1, weight=1, uniform="c")
        cuerpo.rowconfigure(0, weight=1, uniform="r")
        cuerpo.rowconfigure(1, weight=1, uniform="r")

        self._tarjeta(cuerpo, 0, 0, "▣", "Abrir Caja", "Iniciar una nueva sesión de caja", c["gold"], self._abrir_caja)
        self._tarjeta(cuerpo, 0, 1, "×", "Cerrar Caja", "Realizar el cierre de la sesión actual", c["danger"], self._cerrar_caja)
        self._tarjeta(cuerpo, 1, 0, "₽", "Ver Caja Abierta", "Consultar los datos de la sesión actual", c["success"], self._ver_caja)
        self._tarjeta(cuerpo, 1, 1, "↔", "Caja Chica", "Registrar y consultar movimientos de caja chica", c["gold"], self._caja_chica)

        pie = tk.Label(area, text="No se modifica la estructura de la base de datos", anchor="w",
                       font=("Segoe UI", 8), fg=c["muted"], bg=c["bg"])
        pie.grid(row=3, column=0, sticky="ew", pady=(12, 0))

    def _tarjeta(self, parent, row, col, icono, titulo, subtitulo, color, comando) -> None:
        c = self.colores()
        card = tk.Frame(parent, bg=c["surface"], highlightthickness=1, highlightbackground=c["border"])
        card.grid(row=row, column=col, sticky="nsew", padx=7, pady=7)
        card.columnconfigure(1, weight=1)
        tk.Label(card, text=icono, font=("Segoe UI Symbol", 28, "bold"), fg=color, bg=c["surface"]).grid(row=0, column=0, rowspan=2, padx=(22, 13), pady=22, sticky="n")
        tk.Label(card, text=titulo, font=("Segoe UI", 16, "bold"), fg=color, bg=c["surface"], anchor="w").grid(row=0, column=1, sticky="w", padx=(0, 15), pady=(22, 3))
        tk.Label(card, text=subtitulo, font=("Segoe UI", 9), fg=c["muted"], bg=c["surface"], anchor="w", wraplength=320).grid(row=1, column=1, sticky="w", padx=(0, 15))
        tk.Button(card, text="Abrir  →", command=comando, font=("Segoe UI", 9, "bold"),
                  bg=color, fg=c["white"], activebackground=color, activeforeground=c["white"],
                  bd=0, relief="flat", padx=12, pady=8, cursor="hand2").grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=(15, 18))

    def _actualizar_estado(self) -> None:
        try:
            self.sesion_caja = obtener_sesion_abierta()
        except Exception as error:
            self.sesion_caja = None
            self.estado_titulo.configure(text="No se pudo consultar la caja")
            self.estado_detalle.configure(text=str(error))
            return

        c = self.colores()
        if self.sesion_caja:
            caja = self._valor("caja_descripcion", "descripcion_caja", "descripcion", predeterminado="Caja")
            id_sesion = self._valor("id_caja_sesion", predeterminado="-")
            self.estado_icon.configure(text="●", fg=c["success"])
            self.estado_titulo.configure(text="Caja abierta")
            self.estado_detalle.configure(text=f"{caja}  ·  Sesión {id_sesion}")
        else:
            self.estado_icon.configure(text="●", fg=c["danger"])
            self.estado_titulo.configure(text="Caja cerrada")
            self.estado_detalle.configure(text="Abrí la caja para comenzar a operar")

    def _valor(self, *nombres: str, predeterminado=None):
        for nombre in nombres:
            valor = self.sesion_caja.get(nombre.lower()) if self.sesion_caja else None
            if valor is not None:
                return valor
        return predeterminado

    def _abrir_caja(self) -> None:
        self._actualizar_estado()
        if self.sesion_caja:
            self._ver_caja()
            return
        VentanaAperturaCaja(self, al_abrir=self._caja_abierta)

    def _caja_abierta(self, _id_sesion: int) -> None:
        self._actualizar_estado()

    def _ver_caja(self) -> None:
        if not self.sesion_caja:
            messagebox.showinfo("Caja", "No hay una caja abierta actualmente.", parent=self)
            return
        caja = self._valor("caja_descripcion", "descripcion_caja", "descripcion", predeterminado="Caja")
        sesion = self._valor("id_caja_sesion", predeterminado="-")
        usuario = self._valor("usuario_apertura", "usuario", predeterminado="-")
        fecha = self._valor("fecha_apertura", predeterminado="-")
        saldo = self._valor("saldo_inicial", predeterminado=0)
        try:
            saldo_texto = f"$ {Decimal(str(saldo)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            saldo_texto = str(saldo)
        messagebox.showinfo("Caja abierta", f"Caja: {caja}\nSesión: {sesion}\nUsuario: {usuario}\nApertura: {fecha}\nSaldo inicial: {saldo_texto}", parent=self)

    def _cerrar_caja(self) -> None:
        self._actualizar_estado()
        if not self.sesion_caja:
            messagebox.showinfo("Cerrar caja", "No hay una sesión de caja abierta.", parent=self)
            return
        self.navegador.abrir_cierre_caja(self)

    def _caja_chica(self) -> None:
        self.navegador.abrir_caja_chica(self)

    def _alternar_tema(self) -> None:
        # Para mantener la primera versión estable, el tema se aplica recreando
        # esta pantalla; la navegación y los datos permanecen intactos.
        self._tema = "oscuro" if self._tema == "claro" else "claro"
        # Los widgets de esta ventana se actualizarán al reconstruirla.
        tema = self._tema
        parent = self.master
        navegador = self.navegador
        self.destroy()
        nueva = VentanaCaja(parent, navegador)
        nueva._tema = tema
        # Reaplicar interfaz con el tema elegido.
        for widget in nueva.winfo_children():
            widget.destroy()
        nueva.columnconfigure(1, weight=1)
        nueva.rowconfigure(0, weight=1)
        nueva._crear_interfaz()
        nueva._actualizar_estado()
        navegador.ventana_actual = nueva
        nueva.protocol("WM_DELETE_WINDOW", lambda: navegador.volver_menu(nueva))
        nueva.lift()
        nueva.focus_force()

    def _salir(self) -> None:
        self.navegador.volver_menu(self)
