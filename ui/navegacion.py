from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Any

import traceback
import tkinter as tk

from tkinter import messagebox
from collections.abc import Callable
from typing import Any


# =============================================================================
# TEMA GLOBAL
# =============================================================================
PALETA_CLARO = {
    "bg": "#f3f1ef", "surface": "#ffffff", "surface2": "#faf8f7",
    "border": "#ddd7d4", "text": "#252328", "muted": "#6d6870",
    "sidebar": "#3a111b", "sidebar_hover": "#511522", "gold": "#c99624",
    "danger": "#c94b57", "success": "#3c8149",
}

PALETA_OSCURO = {
    "bg": "#15171b", "surface": "#20242a", "surface2": "#292e35",
    "border": "#3b414a", "text": "#f3f4f6", "muted": "#aeb5bf",
    "sidebar": "#321019", "sidebar_hover": "#4a1723", "gold": "#d5a63a",
    "danger": "#e05b68", "success": "#55bd69",
}


def _tema_paleta(tema: str) -> dict[str, str]:
    return PALETA_OSCURO if tema == "oscuro" else PALETA_CLARO


def _configurar_ttk_tema(ventana: tk.Misc, c: dict[str, str]) -> None:
    """Estilos ttk comunes para que todas las pantallas respeten el tema."""
    try:
        estilo = ttk.Style(ventana)
        estilo.configure("Global.TFrame", background=c["bg"])
        estilo.configure("Global.Surface.TFrame", background=c["surface"])
        estilo.configure("TFrame", background=c["bg"])
        estilo.configure("TLabel", background=c["bg"], foreground=c["text"])
        estilo.configure("TButton", background=c["surface"], foreground=c["text"],
                         padding=(10, 6))
        estilo.map("TButton",
                   background=[("active", c["surface2"])],
                   foreground=[("active", c["text"])])
        estilo.configure("Sidebar.TFrame", background=c["sidebar"])
        estilo.configure("Sidebar.TLabel", background=c["sidebar"], foreground="#ffffff")
        estilo.configure("Sidebar.Gold.TLabel", background=c["sidebar"], foreground=c["gold"])
        estilo.configure("Sidebar.TButton", background=c["sidebar"], foreground="#ffffff",
                         padding=(14, 10), borderwidth=0, relief="flat", anchor="w")
        estilo.map("Sidebar.TButton",
                   background=[("active", c["sidebar_hover"]), ("pressed", c["sidebar_hover"])],
                   foreground=[("active", "#ffffff"), ("pressed", "#ffffff")])
        estilo.configure("TEntry", fieldbackground=c["surface"], foreground=c["text"])
        estilo.configure("TCombobox", fieldbackground=c["surface"],
                         background=c["surface"], foreground=c["text"])
        estilo.configure("Pedido.TEntry", fieldbackground=c["surface"], foreground=c["text"],
                         insertcolor=c["text"], padding=(8, 7))
        estilo.configure("Pedido.TCombobox", fieldbackground=c["surface"],
                         background=c["surface"], foreground=c["text"], padding=(7, 6))
        estilo.configure("Pedido.TSpinbox", fieldbackground=c["surface"],
                         background=c["surface"], foreground=c["text"], padding=(5, 5))
        estilo.configure("TCheckbutton", background=c["bg"], foreground=c["text"])
        estilo.configure("TRadiobutton", background=c["bg"], foreground=c["text"])
        estilo.configure("TNotebook", background=c["bg"])
        estilo.configure("TNotebook.Tab", background=c["surface"],
                         foreground=c["text"], padding=(10, 6))
        estilo.map("TNotebook.Tab",
                   background=[("selected", c["sidebar_hover"])],
                   foreground=[("selected", "#ffffff")])
        estilo.configure("TLabelframe", background=c["bg"], foreground=c["text"])
        estilo.configure("TLabelframe.Label", background=c["bg"], foreground=c["text"])
        estilo.configure("Treeview", background=c["surface"],
                         fieldbackground=c["surface"], foreground=c["text"],
                         rowheight=28)
        estilo.map("Treeview",
                   background=[("selected", c["sidebar_hover"])],
                   foreground=[("selected", "#ffffff")])
        estilo.configure("Treeview.Heading", background=c["sidebar_hover"],
                         foreground="#ffffff", padding=(8, 6))
        estilo.configure("TSeparator", background=c["border"])
    except tk.TclError:
        pass


def aplicar_tema_ventana(ventana: tk.Misc, tema: str) -> None:
    """Aplica un tema visual común sin tocar ninguna operación de la BD."""
    c = _tema_paleta(tema)
    ventana.configure(bg=c["bg"])
    _configurar_ttk_tema(ventana, c)

    def recorrer(widget: tk.Misc) -> None:
        try:
            clase = widget.winfo_class()
        except tk.TclError:
            return

        try:
            if clase in ("Frame", "Toplevel"):
                widget.configure(bg=c["bg"])
            elif clase == "Label":
                widget.configure(bg=c["bg"], fg=c["text"])
            elif clase == "Button":
                widget.configure(
                    bg=c["surface"], fg=c["text"],
                    activebackground=c["surface2"],
                    activeforeground=c["text"],
                )
            elif clase in ("Entry", "Spinbox"):
                widget.configure(
                    bg=c["surface"], fg=c["text"],
                    insertbackground=c["text"],
                    selectbackground=c["sidebar_hover"],
                    selectforeground="#ffffff",
                )
            elif clase == "Text":
                widget.configure(
                    bg=c["surface"], fg=c["text"],
                    insertbackground=c["text"],
                    selectbackground=c["sidebar_hover"],
                    selectforeground="#ffffff",
                )
            elif clase == "Listbox":
                widget.configure(
                    bg=c["surface"], fg=c["text"],
                    selectbackground=c["sidebar_hover"],
                    selectforeground="#ffffff",
                )
            elif clase in ("Checkbutton", "Radiobutton"):
                widget.configure(
                    bg=c["bg"], fg=c["text"],
                    activebackground=c["bg"],
                    activeforeground=c["text"],
                    selectcolor=c["surface"],
                )
            elif clase == "Labelframe":
                widget.configure(bg=c["bg"], fg=c["text"])
        except tk.TclError:
            pass

        try:
            for hijo in widget.winfo_children():
                recorrer(hijo)
        except tk.TclError:
            pass

    recorrer(ventana)

    # Algunas pantallas necesitan reforzar estilos ttk concretos (por ejemplo
    # DateEntry/Combobox) después de aplicar el tema global.
    try:
        hook = getattr(ventana, "_aplicar_tema_global", None)
        if callable(hook):
            hook(tema)
    except (AttributeError, tk.TclError):
        pass


def instalar_selector_tema(ventana: tk.Toplevel, navegador) -> None:
    """Agrega Oscuro/Claro a cualquier pantalla que no tenga selector propio."""
    if hasattr(ventana, "_selector_tema_global"):
        return
    if hasattr(ventana, "btn_tema"):
        return

    tema_actual = getattr(navegador, "tema", "claro")
    ventana._tema_global = tema_actual

    selector = tk.Frame(
        ventana, bg=_tema_paleta(tema_actual)["surface"],
        bd=0, highlightthickness=1,
        highlightbackground=_tema_paleta(tema_actual)["border"],
    )
    selector.place(relx=1.0, x=-18, y=12, anchor="ne")
    ventana._selector_tema_global = selector

    def actualizar() -> None:
        tema = ventana._tema_global
        c = _tema_paleta(tema)
        selector.configure(bg=c["surface"], highlightbackground=c["border"])
        boton_claro.configure(
            bg=c["surface"], fg=c["text"],
            activebackground=c["surface2"], activeforeground=c["text"],
        )
        boton_oscuro.configure(
            bg=c["sidebar_hover"] if tema == "oscuro" else c["surface"],
            fg="#ffffff" if tema == "oscuro" else c["muted"],
            activebackground=c["sidebar_hover"],
            activeforeground="#ffffff",
        )
        aplicar_tema_ventana(ventana, tema)

    def cambiar() -> None:
        ventana._tema_global = "oscuro" if ventana._tema_global == "claro" else "claro"
        navegador.tema = ventana._tema_global
        actualizar()

    boton_claro = tk.Button(
        selector, text="☀ Claro",
        command=lambda: (setattr(ventana, "_tema_global", "claro"),
                          setattr(navegador, "tema", "claro"), actualizar()),
        bd=0, relief="flat", padx=9, pady=5,
        font=("Segoe UI", 9, "bold"), cursor="hand2",
    )
    boton_claro.pack(side="left")

    boton_oscuro = tk.Button(
        selector, text="☾ Oscuro", command=cambiar,
        bd=0, relief="flat", padx=9, pady=5,
        font=("Segoe UI", 9, "bold"), cursor="hand2",
    )
    boton_oscuro.pack(side="left")

    actualizar()


class NavegadorPOS:
    """
    Controla el desplazamiento entre los módulos del POS.

    Las ventanas no se abren entre sí directamente.
    Todas solicitan la navegación a esta clase.
    """

    def __init__(
        self,
        menu_principal: tk.Tk,
    ) -> None:
        self.menu_principal = menu_principal
        self.ventana_actual: tk.Toplevel | None = None
        self.tema = "claro"

    def _puede_abandonar(
        self,
        ventana: tk.Misc | None,
    ) -> bool:
        if ventana is None:
            return True

        validar = getattr(
            ventana,
            "puede_abandonar",
            None,
        )

        if callable(validar):
            return bool(validar())

        return True

    def _abrir(
        self,
        *,
        origen: tk.Toplevel | None,
        fabrica: Callable[[], tk.Toplevel],
        contexto: dict[str, Any] | None = None,
    ) -> tk.Toplevel | None:
        if not self._puede_abandonar(origen):
            return None

        nueva_ventana = fabrica()

        nueva_ventana.protocol(
            "WM_DELETE_WINDOW",
            lambda:
                self.volver_menu(nueva_ventana),
        )

        # Todas las pantallas secundarias tienen selector Oscuro/Claro.
        instalar_selector_tema(nueva_ventana, self)

        if contexto:
            aplicar_contexto = getattr(
                nueva_ventana,
                "aplicar_contexto",
                None,
            )

            if callable(aplicar_contexto):
                datos = dict(contexto)

                nueva_ventana.after_idle(
                    lambda:
                        aplicar_contexto(**datos)
                )

        if (
            origen is not None
            and origen is not nueva_ventana
            and origen.winfo_exists()
        ):
            origen.destroy()

        self.ventana_actual = nueva_ventana

        nueva_ventana.lift()
        nueva_ventana.focus_force()

        return nueva_ventana

    def volver_menu(
        self,
        origen: tk.Toplevel | None = None,
    ) -> None:
        if not self._puede_abandonar(origen):
            return

        if (
            origen is not None
            and origen.winfo_exists()
        ):
            origen.destroy()

        self.ventana_actual = None

        self.menu_principal.deiconify()
        # Si el tema se cambió dentro de un módulo, sincronizar el Dashboard.
        try:
            if hasattr(self.menu_principal, "_tema") and self.menu_principal._tema != self.tema:
                self.menu_principal._tema = self.tema
                self.menu_principal._aplicar_tema()
        except (AttributeError, tk.TclError):
            pass
        self.menu_principal.lift()
        self.menu_principal.focus_force()

    def abrir_caja(
        self,
        origen: tk.Toplevel | None = None,
    ) -> tk.Toplevel | None:
        from ui.caja import VentanaCaja

        return self._abrir(
            origen=origen,
            fabrica=lambda: VentanaCaja(
                self.menu_principal,
                navegador=self,
            ),
        )

    def abrir_pedidos(
        self,
        origen: tk.Toplevel | None = None,
    ) -> tk.Toplevel | None:
        from ui.pedidos import VentanaPedidos

        return self._abrir(
            origen=origen,
            fabrica=lambda: VentanaPedidos(
                self.menu_principal,
                navegador=self,
            ),
        )

    def abrir_pedido(
        self,
        origen: tk.Toplevel | None = None,
    ) -> tk.Toplevel | None:
        from ui.pedido import VentanaPedido

        return self._abrir(
            origen=origen,
            fabrica=lambda: VentanaPedido(
                self.menu_principal,
                navegador=self,
            ),
        )

    def abrir_pedidos_proyectados(
        self,
        origen: tk.Toplevel | None = None,
    ) -> tk.Toplevel | None:
        from ui.pedidos_proyectados import (
            VentanaPedidosProyectados,
        )

        return self._abrir(
            origen=origen,
            fabrica=lambda:
                VentanaPedidosProyectados(
                    self.menu_principal,
                    navegador=self,
                ),
        )
    def abrir_planificacion(
        self,
        origen: tk.Toplevel | None = None,
        *,
        id_pedido: int | None = None,
    ) -> tk.Toplevel | None:
        from ui.planificacion import (
            VentanaPlanificacion,
        )

        return self._abrir(
            origen=origen,
            fabrica=lambda:
                VentanaPlanificacion(
                    self.menu_principal,
                    navegador=self,
                ),
            contexto={
                "id_pedido": id_pedido,
            },
        )

    def abrir_elaboracion(
        self,
        origen: tk.Toplevel | None = None,
        *,
        id_producto: int | None = None,
        fecha_elaboracion=None,
    ) -> tk.Toplevel | None:
        from ui.confirmar_elaboracion import (
            VentanaConfirmarElaboracion,
        )

        return self._abrir(
            origen=origen,
            fabrica=lambda:
                VentanaConfirmarElaboracion(
                    self.menu_principal,
                    navegador=self,
                ),
            contexto={
                "id_producto": id_producto,
                "fecha_elaboracion":
                    fecha_elaboracion,
            },
        )

    def abrir_salidas(
        self,
        origen: tk.Toplevel | None = None,
        *,
        id_pedido: int | None = None,
    ) -> tk.Toplevel | None:
        from ui.salida_pedido import (
            VentanaSalidaPedido,
        )

        return self._abrir(
            origen=origen,
            fabrica=lambda:
                VentanaSalidaPedido(
                    self.menu_principal,
                    navegador=self,
                ),
            contexto={
                "id_pedido": id_pedido,
            },
        )

    def abrir_cobros(
        self,
        origen: tk.Toplevel | None = None,
        *,
        id_cliente: int | None = None,
        id_venta: int | None = None,
    ) -> tk.Toplevel | None:
        from ui.cobros import VentanaCobros

        return self._abrir(
            origen=origen,
            fabrica=lambda:
                VentanaCobros(
                    self.menu_principal,
                    navegador=self,
                ),
            contexto={
                "id_cliente": id_cliente,
                "id_venta": id_venta,
            },
        )

    def abrir_caja_chica(
        self,
        origen: tk.Toplevel | None = None,
    ) -> tk.Toplevel | None:
        from ui.caja_chica import VentanaCajaChica

        return self._abrir(
            origen=origen,
            fabrica=lambda:
                VentanaCajaChica(
                    self.menu_principal,
                    navegador=self,
                ),
        )

    def abrir_cierre_caja(
        self,
        origen: tk.Toplevel | None = None,
    ) -> tk.Toplevel | None:
        from ui.cierre_caja import VentanaCierreCaja

        return self._abrir(
            origen=origen,
            fabrica=lambda:
                VentanaCierreCaja(
                    self.menu_principal,
                    navegador=self,
                ),
        )

    def abrir_stock(
        self,
        origen: tk.Toplevel | None = None,
    ) -> tk.Toplevel | None:
        from ui.stock import VentanaStock

        return self._abrir(
            origen=origen,
            fabrica=lambda:
                VentanaStock(
                    self.menu_principal,
                    navegador=self,
                ),
        )


    def abrir_reporte_pedidos(
        self,
        origen: tk.Toplevel | None = None,
    ) -> tk.Toplevel | None:
        from ui.reporte_pedidos import (
            VentanaReportePedidos,
        )

        return self._abrir(
            origen=origen,
            fabrica=lambda:
                VentanaReportePedidos(
                    self.menu_principal,
                    navegador=self,
                ),
        )

    def abrir_reporte_precios(
        self,
        origen: tk.Toplevel | None = None,
    ) -> tk.Toplevel | None:
        from ui.reporte_precios import (
            VentanaReportePrecios,
        )

        return self._abrir(
            origen=origen,
            fabrica=lambda:
                VentanaReportePrecios(
                    self.menu_principal,
                    navegador=self,
                ),
        )

def crear_barra_navegacion(
    *,
    ventana: tk.Toplevel,
    navegador,
    modulo_actual: str,
) -> ttk.Frame:
    """
    Crea una barra adaptable.

    El módulo actual se excluye para evitar abrir
    otra instancia de la misma ventana.
    """

    barra = ttk.Frame(
        ventana,
        padding=(8, 6),
    )
    barra.pack(
        side="top",
        fill="x",
    )

    opciones = (
        (
            "menu",
            "Menú",
            lambda:
                navegador.volver_menu(ventana),
        ),
        (
            "pedido",
            "Nuevo pedido",
            lambda:
                navegador.abrir_pedido(ventana),
        ),
        (
            "proyecciones",
            "Proyecciones",
            lambda:
                navegador.abrir_pedidos_proyectados(
                    ventana
                ),
        ),
        (
            "planificacion",
            "Planificación",
            lambda:
                navegador.abrir_planificacion(
                    ventana
                ),
        ),
        (
            "elaboracion",
            "Confirmar elaboración",
            lambda:
                navegador.abrir_elaboracion(
                    ventana
                ),
        ),
        (
            "salidas",
            "Salidas y entregas",
            lambda:
                navegador.abrir_salidas(
                    ventana
                ),
        ),
        (
            "cobros",
            "Cobros",
            lambda:
                navegador.abrir_cobros(
                    ventana
                ),
        ),
        (
            "caja_chica",
            "Caja chica",
            lambda:
                navegador.abrir_caja_chica(
                    ventana
                ),
        ),
    )

    # El módulo actual directamente no aparece.
    opciones_visibles = [
        opcion
        for opcion in opciones
        if opcion[0] != modulo_actual
    ]

    ancho_pantalla = (
        ventana.winfo_screenwidth()
    )

    # Monitor pequeño: hasta tres botones por fila.
    # Monitor grande: todos en una fila.
    columnas_por_fila = (
        3
        if ancho_pantalla < 1250
        else len(opciones_visibles)
    )

    for indice, (
        _codigo,
        texto,
        comando,
    ) in enumerate(opciones_visibles):
        fila = indice // columnas_por_fila
        columna = indice % columnas_por_fila

        ttk.Button(
            barra,
            text=texto,
            command=comando,
        ).grid(
            row=fila,
            column=columna,
            padx=4,
            pady=3,
            sticky="ew",
        )

    for columna in range(
        columnas_por_fila
    ):
        barra.columnconfigure(
            columna,
            weight=1,
            uniform="navegacion",
        )

    ttk.Separator(
        ventana,
        orient="horizontal",
    ).pack(
        side="top",
        fill="x",
    )

    return barra