from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk
from typing import Any, Callable
from pathlib import Path
from tkcalendar import DateEntry
from ui.ventana_util import maximizar_ventana


from db.pedido_repository import (
    agregar_cliente,
    guardar_pedido,
    listar_clientes,
    listar_modalidades,
    listar_productos,
)
import unicodedata

@dataclass
class DetallePedido:
    id_producto: int
    descripcion: str
    cantidad: Decimal
    tipo_precio: str
    precio_unitario: Decimal
    descuento: Decimal
    observaciones: str | None

    @property
    def subtotal(self) -> Decimal:
        subtotal = (
            self.cantidad * self.precio_unitario
            - self.descuento
        )

        return max(subtotal, Decimal("0"))


def convertir_decimal(
    texto: str,
    *,
    decimales: int = 2,
) -> Decimal:
    valor = texto.strip().replace(" ", "")

    if not valor:
        return Decimal("0")

    if "," in valor and "." in valor:
        valor = valor.replace(".", "").replace(",", ".")

    elif "," in valor:
        valor = valor.replace(",", ".")

    try:
        numero = Decimal(valor)

    except InvalidOperation as error:
        raise ValueError(
            f"El valor '{texto}' no es un número válido."
        ) from error

    cuantizador = (
        Decimal("0.001")
        if decimales == 3
        else Decimal("0.01")
    )

    return numero.quantize(cuantizador)


def formato_decimal(
    valor: Decimal,
    *,
    decimales: int = 2,
) -> str:
    formato = (
        f"{valor:,.3f}"
        if decimales == 3
        else f"{valor:,.2f}"
    )

    return (
        formato
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def formato_cantidad(valor: Any) -> str:
    """Muestra cantidades de producto sin decimales."""
    numero = Decimal(str(valor or 0))

    if numero != numero.to_integral_value():
        raise ValueError(
            f"La cantidad '{valor}' no es un número entero."
        )

    return str(int(numero))


def convertir_cantidad(texto: str) -> Decimal:
    """Convierte una cantidad ingresada y exige un número entero."""
    if not texto.strip():
        raise ValueError(
            "Debe indicar una cantidad."
        )

    cantidad = convertir_decimal(
        texto,
        decimales=3,
    )

    if cantidad != cantidad.to_integral_value():
        raise ValueError(
            "La cantidad debe ser un número entero."
        )

    return cantidad.quantize(Decimal("1"))


def formato_moneda(valor: Decimal) -> str:
    return f"$ {formato_decimal(valor)}"

class ControlHora(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        hora_inicial: int = 12,
        minuto_inicial: int = 0,
        permitir_vacio: bool = True,
    ) -> None:
        super().__init__(parent)

        self._permitir_vacio = permitir_vacio

        self.hora = tk.StringVar(
            value=f"{hora_inicial:02d}"
        )

        self.minuto = tk.StringVar(
            value=f"{minuto_inicial:02d}"
        )

        self.sin_hora = tk.BooleanVar(
            value=permitir_vacio
        )

        self.spn_hora = ttk.Spinbox(
            self,
            from_=0,
            to=23,
            increment=1,
            wrap=True,
            width=3,
            justify="center",
            format="%02.0f",
            textvariable=self.hora,
        )
        self.spn_hora.pack(side="left")

        ttk.Label(
            self,
            text=":",
            font=("Segoe UI", 11, "bold"),
        ).pack(
            side="left",
            padx=3,
        )

        self.spn_minuto = ttk.Spinbox(
            self,
            from_=0,
            to=59,
            increment=5,
            wrap=True,
            width=3,
            justify="center",
            format="%02.0f",
            textvariable=self.minuto,
        )
        self.spn_minuto.pack(side="left")

        if permitir_vacio:
            self.chk_sin_hora = ttk.Checkbutton(
                self,
                text="Sin hora",
                variable=self.sin_hora,
                command=self._actualizar_estado,
            )
            self.chk_sin_hora.pack(
                side="left",
                padx=(10, 0),
            )

        self._actualizar_estado()

    def _actualizar_estado(self) -> None:
        deshabilitado = (
            self._permitir_vacio
            and self.sin_hora.get()
        )

        estado = (
            "disabled"
            if deshabilitado
            else "normal"
        )

        self.spn_hora.configure(state=estado)
        self.spn_minuto.configure(state=estado)

    def obtener_hora(self) -> time | None:
        if (
            self._permitir_vacio
            and self.sin_hora.get()
        ):
            return None

        try:
            hora = int(self.hora.get())
            minuto = int(self.minuto.get())

        except ValueError as error:
            raise ValueError(
                "La hora de entrega no es válida."
            ) from error

        if not 0 <= hora <= 23:
            raise ValueError(
                "La hora debe estar entre 00 y 23."
            )

        if not 0 <= minuto <= 59:
            raise ValueError(
                "Los minutos deben estar entre 00 y 59."
            )

        return time(
            hour=hora,
            minute=minuto,
        )

    def establecer_hora(
        self,
        valor: time | None,
    ) -> None:
        if valor is None:
            if self._permitir_vacio:
                self.sin_hora.set(True)
                self._actualizar_estado()
            return

        self.hora.set(f"{valor.hour:02d}")
        self.minuto.set(f"{valor.minute:02d}")

        if self._permitir_vacio:
            self.sin_hora.set(False)

        self._actualizar_estado()
def normalizar_busqueda(texto: str) -> str:
    texto_normalizado = unicodedata.normalize(
        "NFKD",
        texto,
    )

    return "".join(
        caracter
        for caracter in texto_normalizado
        if not unicodedata.combining(caracter)
    ).casefold().strip()


class ComboPredictivo(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        max_resultados: int = 8,
        **opciones,
    ) -> None:
        
        super().__init__(parent)

        opciones.pop("state", None)

        self._todos_los_valores: list[str] = []
        self._valores_filtrados: list[str] = []

        self._max_resultados = max_resultados
        self._actualizando = False

        self._texto = tk.StringVar()

        self.columnconfigure(
            0,
            weight=1,
        )

        self.entrada = ttk.Entry(
            self,
            textvariable=self._texto,
            **opciones,
        )
        self.entrada.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        self.boton_lista = ttk.Button(
            self,
            text="▼",
            width=3,
            style="Pedido.TButton",
            command=self._alternar_lista,
        )
        self.boton_lista.grid(
            row=0,
            column=1,
            padx=(3, 0),
        )

        self._crear_lista_emergente()

        self._texto.trace_add(
            "write",
            self._al_escribir,
        )

        self.entrada.bind(
            "<Down>",
            self._mover_abajo,
        )

        self.entrada.bind(
            "<Up>",
            self._mover_arriba,
        )

        self.entrada.bind(
            "<Return>",
            self._confirmar_seleccion,
        )

        self.entrada.bind(
            "<Escape>",
            self._cancelar,
        )

        self.entrada.bind(
            "<FocusOut>",
            self._programar_ocultamiento,
        )

    def _crear_lista_emergente(self) -> None:
        self._ventana_lista = tk.Toplevel(self)

        self._ventana_lista.withdraw()
        self._ventana_lista.overrideredirect(True)
        self._ventana_lista.transient(
            self.winfo_toplevel()
        )

        marco = ttk.Frame(
            self._ventana_lista,
            borderwidth=1,
            relief="solid",
        )
        marco.pack(
            fill="both",
            expand=True,
        )

        marco.columnconfigure(
            0,
            weight=1,
        )
        marco.rowconfigure(
            0,
            weight=1,
        )

        self.lista = tk.Listbox(
            marco,
            exportselection=False,
            activestyle="dotbox",
            borderwidth=0,
            highlightthickness=0,
        )
        self.lista.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        barra = ttk.Scrollbar(
            marco,
            orient="vertical",
            command=self.lista.yview,
        )
        barra.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.lista.configure(
            yscrollcommand=barra.set
        )

        self.lista.bind(
            "<ButtonRelease-1>",
            self._seleccionar_con_mouse,
        )

        self.lista.bind(
            "<Double-Button-1>",
            self._seleccionar_con_mouse,
        )

  
    def get(self) -> str:
        return self._texto.get()

    def set(self, valor: str) -> None:
        self._actualizando = True

        try:
            self._texto.set(valor)

        finally:
            self._actualizando = False

        self._ocultar_lista()

    def limpiar(self) -> None:
        self.set("")
        self._valores_filtrados = list(
            self._todos_los_valores
        )

    def focus_set(self) -> None:
        self.entrada.focus_set()

    def icursor(self, posicion) -> None:
        self.entrada.icursor(posicion)

    def _al_escribir(self, *_argumentos) -> None:
        if self._actualizando:
            return

        texto = normalizar_busqueda(
            self._texto.get()
        )

        if not texto:
            self._valores_filtrados = []
            self._ocultar_lista()
            return

        terminos = texto.split()

        self._valores_filtrados = [
            valor
            for valor in self._todos_los_valores
            if all(
                termino
                in normalizar_busqueda(valor)
                for termino in terminos
            )
        ]

        if self._valores_filtrados:
            self._mostrar_lista()

        else:
            self._ocultar_lista()

    def _mostrar_lista(self) -> None:
        self.lista.delete(
            0,
            tk.END,
        )

        for valor in self._valores_filtrados:
            self.lista.insert(
                tk.END,
                valor,
            )

        cantidad_visible = min(
            len(self._valores_filtrados),
            self._max_resultados,
        )

        self.lista.configure(
            height=max(cantidad_visible, 1)
        )

        if self._valores_filtrados:
            self.lista.selection_clear(
                0,
                tk.END,
            )
            self.lista.selection_set(0)
            self.lista.activate(0)

        self.update_idletasks()
        self._ventana_lista.update_idletasks()

        ancho = max(
            self.winfo_width(),
            300,
        )

        alto = (
            self._ventana_lista
            .winfo_reqheight()
        )

        x = self.winfo_rootx()

        y = (
            self.winfo_rooty()
            + self.winfo_height()
        )

        ancho_pantalla = (
            self.winfo_screenwidth()
        )

        alto_pantalla = (
            self.winfo_screenheight()
        )

        if x + ancho > ancho_pantalla:
            x = max(
                ancho_pantalla - ancho - 10,
                0,
            )

        if y + alto > alto_pantalla:
            y = max(
                self.winfo_rooty() - alto,
                0,
            )

        self._ventana_lista.geometry(
            f"{ancho}x{alto}+{x}+{y}"
        )

        self._ventana_lista.deiconify()
        self._ventana_lista.lift()

        # El foco permanece en el cuadro de escritura.
        self.entrada.focus_set()
        self.entrada.icursor(tk.END)

    def _ocultar_lista(self) -> None:
        if hasattr(
            self,
            "_ventana_lista",
        ):
            self._ventana_lista.withdraw()

    def _alternar_lista(self) -> None:
        if self._ventana_lista.winfo_viewable():
            self._ocultar_lista()
            return

        texto = normalizar_busqueda(
            self.get()
        )

        if texto:
            terminos = texto.split()

            self._valores_filtrados = [
                valor
                for valor in self._todos_los_valores
                if all(
                    termino
                    in normalizar_busqueda(valor)
                    for termino in terminos
                )
            ]

        else:
            self._valores_filtrados = list(
                self._todos_los_valores
            )

        if self._valores_filtrados:
            self._mostrar_lista()

        self.entrada.focus_set()

    def _mover_abajo(
        self,
        _evento=None,
    ) -> str:
        if not self._ventana_lista.winfo_viewable():
            if not self._valores_filtrados:
                self._valores_filtrados = list(
                    self._todos_los_valores
                )

            self._mostrar_lista()
            return "break"

        self._mover_seleccion(1)
        return "break"

    def _mover_arriba(
        self,
        _evento=None,
    ) -> str:
        if self._ventana_lista.winfo_viewable():
            self._mover_seleccion(-1)

        return "break"

    def _mover_seleccion(
        self,
        desplazamiento: int,
    ) -> None:
        cantidad = self.lista.size()

        if cantidad == 0:
            return

        seleccion = self.lista.curselection()

        indice_actual = (
            seleccion[0]
            if seleccion
            else 0
        )

        nuevo_indice = max(
            0,
            min(
                indice_actual + desplazamiento,
                cantidad - 1,
            ),
        )

        self.lista.selection_clear(
            0,
            tk.END,
        )

        self.lista.selection_set(
            nuevo_indice
        )

        self.lista.activate(
            nuevo_indice
        )

        self.lista.see(
            nuevo_indice
        )

    def _confirmar_seleccion(
        self,
        _evento=None,
    ) -> str:
        seleccion = self.lista.curselection()

        if (
            self._ventana_lista.winfo_viewable()
            and seleccion
        ):
            self._seleccionar_indice(
                seleccion[0]
            )

        elif self._valores_filtrados:
            self._seleccionar_indice(0)

        return "break"

    def _seleccionar_con_mouse(
        self,
        _evento=None,
    ) -> None:
        seleccion = self.lista.curselection()

        if seleccion:
            self._seleccionar_indice(
                seleccion[0]
            )

    def _seleccionar_indice(
        self,
        indice: int,
    ) -> None:
        valor = self.lista.get(indice)

        self._actualizando = True

        try:
            self._texto.set(valor)

        finally:
            self._actualizando = False

        self._ocultar_lista()

        self.entrada.focus_set()
        self.entrada.icursor(tk.END)

        self.event_generate(
            "<<ComboboxSelected>>"
        )

    def _cancelar(
        self,
        _evento=None,
    ) -> str:
        if self._ventana_lista.winfo_viewable():
            self._ocultar_lista()

        else:
            self.limpiar()

        return "break"

    def _programar_ocultamiento(
        self,
        _evento=None,
    ) -> None:
        self.after(
            150,
            self._ocultar_si_perdio_foco,
        )

    def _ocultar_si_perdio_foco(self) -> None:
        foco = self.focus_get()

        if foco is self.entrada:
            return

        if foco is self.lista:
            return

        self._ocultar_lista()
        
    def establecer_valores(
        self,
        valores: list[str],
    ) -> None:
        self._todos_los_valores = list(valores)
        self._valores_filtrados = list(valores)

        self.lista.delete(0, tk.END)
        self._ocultar_lista()

    def limpiar(self) -> None:
        self._actualizando = True

        try:
            self._texto.set("")

        finally:
            self._actualizando = False

        self._valores_filtrados = list(
            self._todos_los_valores
        )

        self.lista.delete(0, tk.END)
        self._ocultar_lista()

    def _filtrar(
        self,
        evento: tk.Event,
    ) -> None:
        teclas_sin_filtro = {
            "Up",
            "Down",
            "Left",
            "Right",
            "Return",
            "Escape",
            "Tab",
            "Shift_L",
            "Shift_R",
            "Control_L",
            "Control_R",
            "Alt_L",
            "Alt_R",
            "Home",
            "End",
        }

        if evento.keysym in teclas_sin_filtro:
            return

        texto_actual = self.get()

        # Guardamos la posición del cursor para que
        # configure(values=...) no la modifique.
        posicion_cursor = self.index(tk.INSERT)

        texto_normalizado = normalizar_busqueda(
            texto_actual
        )

        if not texto_normalizado:
            coincidencias = list(
                self._todos_los_valores
            )

        else:
            terminos = texto_normalizado.split()

            coincidencias = [
                valor
                for valor in self._todos_los_valores
                if all(
                    termino
                    in normalizar_busqueda(valor)
                    for termino in terminos
                )
            ]

        self._valores_filtrados = coincidencias

        self.configure(
            values=coincidencias,
        )

        # Conservamos exactamente lo escrito y dejamos
        # el cursor donde estaba.
        self.set(texto_actual)
        self.icursor(posicion_cursor)

    def _abrir_lista(self) -> None:
        if self.focus_get() != self:
            return

        try:
            self.tk.call(
                "ttk::combobox::Post",
                self._w,
            )

        except tk.TclError:
            pass

    def _seleccionar_primero(
        self,
        _evento=None,
    ) -> str:
        texto_actual = self.get()

        if texto_actual in self._todos_los_valores:
            self.event_generate(
                "<<ComboboxSelected>>"
            )
            return "break"

        if self._valores_filtrados:
            self.set(
                self._valores_filtrados[0]
            )

            self.configure(
                values=self._todos_los_valores,
            )

            self.event_generate(
                "<<ComboboxSelected>>"
            )

            self.icursor("end")

        return "break"

    def _limpiar_con_escape(
        self,
        _evento=None,
    ) -> str:
        self.limpiar()
        return "break"
class VentanaPedido(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        al_guardar: Callable[[int], None] | None = None,
        navegador=None,
    ) -> None:
        super().__init__(parent)

        self.navegador = navegador
        self._al_guardar = al_guardar

        self._clientes_por_texto: dict[str, int] = {}
        self._clientes_datos_por_texto: dict[
            str,
            dict
        ] = {}
        self._productos_por_texto: dict[str, dict] = {}
        self._detalle: dict[int, DetallePedido] = {}

        self.title("Nuevo pedido")
        # self.transient(parent)
        self.resizable(True, True)
        maximizar_ventana(self)

        self._crear_interfaz()
        self._cargar_catalogos()
        self._inicializar_formulario()
        

    # ------------------------------------------------------------------
    # INTERFAZ MODERNA
    # ------------------------------------------------------------------
    def _colores(self) -> dict[str, str]:
        if getattr(self, "_tema", "claro") == "oscuro":
            return {
                "bg": "#15171b", "surface": "#20242a", "surface2": "#292e35",
                "border": "#3b414a", "text": "#f3f4f6", "muted": "#aeb5bf",
                "sidebar": "#321019", "sidebar_hover": "#4a1723", "gold": "#d5a63a",
                "burgundy": "#c33b5c", "burgundy_dark": "#982a45", "white": "#ffffff",
                "input": "#252a31",
            }
        return {
            "bg": "#f3f1ef", "surface": "#ffffff", "surface2": "#faf8f7",
            "border": "#ddd7d4", "text": "#252328", "muted": "#6d6870",
            "sidebar": "#3a111b", "sidebar_hover": "#511522", "gold": "#c99624",
            "burgundy": "#b93657", "burgundy_dark": "#8e2440", "white": "#ffffff",
            "input": "#ffffff",
        }

    def _configurar_estilos(self) -> None:
        c = self._colores()
        estilo = ttk.Style(self)
        try:
            estilo.configure("Pedido.TFrame", background=c["bg"])
            estilo.configure("Pedido.Surface.TFrame", background=c["surface"])
            estilo.configure("TEntry", fieldbackground=c["input"], foreground=c["text"],
                             insertcolor=c["text"], padding=(8, 6))
            estilo.configure("Pedido.TEntry", fieldbackground=c["input"], foreground=c["text"],
                             insertcolor=c["text"], padding=(9, 7))
            estilo.configure("Pedido.TCombobox", fieldbackground=c["input"], background=c["input"],
                             foreground=c["text"], padding=(8, 6))
            estilo.map("Pedido.TCombobox", fieldbackground=[("readonly", c["input"]), ("disabled", c["surface2"])],
                       foreground=[("readonly", c["text"]), ("disabled", c["muted"])])
            estilo.configure("Pedido.TButton", background=c["surface2"], foreground=c["text"], padding=(6, 5))
            estilo.map("Pedido.TButton", background=[("active", c["border"]), ("pressed", c["border"])],
                       foreground=[("active", c["text"]), ("pressed", c["text"])])
            estilo.configure("Pedido.TSpinbox", fieldbackground=c["input"], background=c["input"],
                             foreground=c["text"], padding=(5, 5))
            estilo.configure("TFrame", background=c["bg"])
            estilo.configure("TLabel", background=c["bg"], foreground=c["text"])
            estilo.configure("TCheckbutton", background=c["surface"], foreground=c["text"])
            estilo.configure("TLabelframe", background=c["surface"], foreground=c["text"])
            estilo.configure("TLabelframe.Label", background=c["surface"], foreground=c["burgundy"])
            estilo.configure("Treeview", background=c["input"], fieldbackground=c["input"],
                             foreground=c["text"], rowheight=23)
            estilo.map("Treeview", background=[("selected", c["burgundy_dark"])],
                       foreground=[("selected", "#ffffff")])
            estilo.configure("Treeview.Heading", background=c["burgundy"], foreground="#ffffff",
                             padding=(9, 7), font=("Segoe UI", 9, "bold"))
            estilo.configure("TSeparator", background=c["border"])
            estilo.configure("TSpinbox", fieldbackground=c["input"], background=c["input"],
                             foreground=c["text"])
        except tk.TclError:
            pass

    def _crear_interfaz(self) -> None:
        self._tema = getattr(self.navegador, "tema", "claro")
        self._configurar_estilos()

        raiz = tk.Frame(self, bg=self._colores()["bg"])
        raiz.pack(fill="both", expand=True)
        raiz.columnconfigure(1, weight=1)
        raiz.rowconfigure(0, weight=1)
        self._raiz = raiz

        self._crear_sidebar(raiz)

        contenido = tk.Frame(raiz, bg=self._colores()["bg"])
        contenido.grid(row=0, column=1, sticky="nsew", padx=(22, 22), pady=(10, 9))
        contenido.columnconfigure(0, weight=1)
        contenido.rowconfigure(3, weight=0, minsize=145)
        self._contenido = contenido

        # Encabezado: título + selector de tema, sin barra superior adicional.
        encabezado = tk.Frame(contenido, bg=self._colores()["bg"])
        encabezado.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        encabezado.columnconfigure(0, weight=1)

        titulo_box = tk.Frame(encabezado, bg=self._colores()["bg"])
        titulo_box.grid(row=0, column=0, sticky="w")
        self.lbl_titulo = tk.Label(titulo_box, text="Nuevo pedido", font=("Segoe UI", 23, "bold"),
                 bg=self._colores()["bg"], fg=self._colores()["burgundy"], anchor="w")
        self.lbl_titulo.pack(anchor="w")
        self.lbl_subtitulo = tk.Label(titulo_box, text="Completá los datos, agregá los productos y confirmá el pedido.",
                 font=("Segoe UI", 10), bg=self._colores()["bg"], fg=self._colores()["muted"], anchor="w")
        self.lbl_subtitulo.pack(anchor="w", pady=(2, 0))

        self.btn_tema = tk.Button(
            encabezado, text="☾  Modo oscuro", command=self._alternar_tema,
            font=("Segoe UI", 9, "bold"), bd=0, relief="flat", padx=13, pady=7,
            cursor="hand2", highlightthickness=1,
        )
        self.btn_tema.grid(row=0, column=1, sticky="e", padx=(15, 0))

        self._crear_cabecera(contenido)
        self._crear_carga_producto(contenido)
        self._crear_detalle(contenido)
        self._crear_pie(contenido)
        self._aplicar_tema()

    def _crear_sidebar(self, parent: tk.Misc) -> None:
        c = self._colores()
        sidebar = tk.Frame(parent, bg=c["sidebar"], width=255)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        self.sidebar = sidebar

        self._logo_img_pedido = None
        logo_box = tk.Frame(sidebar, bg="#fff9f9", bd=0)
        logo_box.pack(fill="x", padx=14, pady=(16, 18))
        self.logo_box = logo_box

        ruta_logo = Path(__file__).resolve().parent.parent / "assets" / "logo_dona_elina.png"
        try:
            if ruta_logo.exists():
                self._logo_img_pedido = tk.PhotoImage(file=str(ruta_logo))
                if self._logo_img_pedido.width() > 215:
                    factor = max(1, self._logo_img_pedido.width() // 215)
                    self._logo_img_pedido = self._logo_img_pedido.subsample(factor, factor)
                self.logo_label = tk.Label(logo_box, image=self._logo_img_pedido, bg="#fff9f9", bd=0)
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
        self._sidebar_button("＋", "Nuevo pedido", self._ir_nuevo_pedido)
        self._sidebar_button("☷", "Lista de precios", self._abrir_reporte_precios)
        self._sidebar_button("▰", "Salidas y Entregas", self._abrir_salidas)
        self._sidebar_button("⚙", "Configuración", lambda: None)
        self._linea_sidebar()
        self._titulo_sidebar("MENÚ PRINCIPAL")
        self._sidebar_button("⌂", "Dashboard", lambda: self.navegador.volver_menu(self))
        self._sidebar_button("▣", "Caja", lambda: self.navegador.abrir_caja(self))
        self._sidebar_button("🛒", "Pedidos", lambda: self._volver_pedidos(), selected=True)
        self._sidebar_button("▰", "Reparto", lambda: None)
        self._sidebar_button("▤", "Cobros", lambda: self.navegador.abrir_cobros(self))
        self._sidebar_button("▥", "Reportes", lambda: self.navegador.abrir_reporte_pedidos(self))
        self._sidebar_button("⚙", "Configuración", lambda: None)
        self._linea_sidebar()
        self._sidebar_button("⇥", "Salir", self._salir)

        self.sidebar_footer = tk.Label(sidebar, text="Doña Elina - Sistema de Gestión\nVersión 1.0.0",
                 font=("Segoe UI", 8), bg=c["sidebar"], fg=c["gold"], justify="left")
        self.sidebar_footer.pack(side="bottom", anchor="w", padx=22, pady=(0, 14))

    def _titulo_sidebar(self, texto: str) -> None:
        c = self._colores()
        etiqueta = tk.Label(self.sidebar, text=texto, font=("Segoe UI", 9, "bold"),
                 bg=c["sidebar"], fg=c["gold"], anchor="w")
        etiqueta.pack(fill="x", padx=22, pady=(2, 7))
        if not hasattr(self, "_sidebar_labels"):
            self._sidebar_labels = []
        self._sidebar_labels.append((etiqueta, c["gold"]))
        self._linea_sidebar()

    def _linea_sidebar(self) -> None:
        c = self._colores()
        linea = tk.Frame(self.sidebar, bg=c["gold"], height=1)
        linea.pack(fill="x", padx=20, pady=(0, 10))
        if not hasattr(self, "_sidebar_lines"):
            self._sidebar_lines = []
        self._sidebar_lines.append(linea)

    def _sidebar_button(self, icono: str, texto: str, comando, selected: bool = False) -> None:
        c = self._colores()
        bg = c["sidebar_hover"] if selected else c["sidebar"]
        boton = tk.Button(self.sidebar, text=f"{icono}   {texto}", command=comando,
                          font=("Segoe UI", 9, "bold"), anchor="w", bd=0, relief="flat",
                          padx=12, pady=6, cursor="hand2", bg=bg, fg="#ffffff",
                          activebackground=c["sidebar_hover"], activeforeground="#ffffff",
                          highlightthickness=1 if selected else 0,
                          highlightbackground=c["burgundy"] if selected else c["sidebar"])
        boton.pack(fill="x", padx=12, pady=2)
        def entrar(_e):
            if not selected:
                boton.configure(bg=c["sidebar_hover"])
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
        self.navegador.tema = self._tema
        self._configurar_estilos()
        self._aplicar_tema()

    def _aplicar_tema(self) -> None:
        c = self._colores()
        try:
            self.configure(bg=c["bg"])
            self._raiz.configure(bg=c["bg"])
            self._contenido.configure(bg=c["bg"])
        except tk.TclError:
            return

        for widget in (getattr(self, "sidebar", None),):
            if widget:
                widget.configure(bg=c["sidebar"])
        if hasattr(self, "logo_box"):
            self.logo_box.configure(bg="#fff9f9")
        if hasattr(self, "logo_label"):
            self.logo_label.configure(bg="#fff9f9")

        # Actualiza los widgets tk de la pantalla sin tocar el logo.
        def recorrer(widget):
            for hijo in widget.winfo_children():
                if hijo is getattr(self, "logo_box", None) or hijo is getattr(self, "sidebar", None):
                    continue
                try:
                    clase = hijo.winfo_class()
                    if clase == "Frame":
                        hijo.configure(bg=c["bg"])
                    elif clase == "Label":
                        hijo.configure(bg=c["bg"], fg=c["text"])
                    elif clase == "Button":
                        # Los botones de sidebar se actualizan por separado.
                        if hijo in [x[0] for x in getattr(self, "_sidebar_buttons", [])]:
                            pass
                        else:
                            texto = str(hijo.cget("text"))
                            es_acento = ("Agregar producto" in texto or "Guardar pedido" in texto)
                            hijo.configure(
                                bg=c["burgundy"] if es_acento else c["surface2"],
                                fg="#ffffff" if es_acento else c["text"],
                                activebackground=c["burgundy_dark"] if es_acento else c["border"],
                                activeforeground="#ffffff" if es_acento else c["text"],
                            )
                    elif clase in ("LabelFrame", "Labelframe"):
                        hijo.configure(bg=c["surface"], fg=c["burgundy"])
                    elif clase == "Text":
                        hijo.configure(bg=c["input"], fg=c["text"], insertbackground=c["text"])
                except tk.TclError:
                    pass
                try:
                    recorrer(hijo)
                except tk.TclError:
                    pass
        try:
            recorrer(self._contenido)
        except tk.TclError:
            pass

        # El encabezado conserva su jerarquía tipográfica.
        try:
            self.lbl_titulo.configure(bg=c["bg"], fg=c["burgundy"])
            self.lbl_subtitulo.configure(bg=c["bg"], fg=c["muted"])
        except (AttributeError, tk.TclError):
            pass

        # El bloque final del total conserva su superficie y jerarquía.
        if hasattr(self, "total_box"):
            try:
                self.total_box.configure(bg=c["surface2"], highlightbackground=c["border"])
                self.total_caption.configure(bg=c["surface2"], fg=c["muted"])
                self.lbl_total.configure(bg=c["surface2"], fg=c["burgundy"])
            except tk.TclError:
                pass

        # La barra lateral siempre mantiene su identidad visual.
        for etiqueta, _color in getattr(self, "_sidebar_labels", []):
            try:
                etiqueta.configure(bg=c["sidebar"], fg=c["gold"])
            except tk.TclError:
                pass
        for linea in getattr(self, "_sidebar_lines", []):
            try:
                linea.configure(bg=c["gold"])
            except tk.TclError:
                pass
        try:
            self.sidebar_footer.configure(bg=c["sidebar"], fg=c["gold"])
        except (AttributeError, tk.TclError):
            pass

        for boton, selected in getattr(self, "_sidebar_buttons", []):
            try:
                boton.configure(
                    bg=c["sidebar_hover"] if selected else c["sidebar"],
                    fg="#ffffff", activebackground=c["sidebar_hover"], activeforeground="#ffffff",
                    highlightbackground=c["burgundy"] if selected else c["sidebar"],
                )
            except tk.TclError:
                pass

        if hasattr(self, "btn_tema"):
            self.btn_tema.configure(
                text="☾  Modo oscuro" if self._tema == "claro" else "☀  Modo claro",
                bg=c["surface"], fg=c["text"], activebackground=c["surface2"],
                activeforeground=c["text"], highlightbackground=c["border"],
            )

        # Etiquetas de secciones que son ttk quedan a cargo del estilo TLabel/LabelFrame.

    def _volver_pedidos(self) -> None:
        if self.navegador is not None:
            self.navegador.abrir_pedidos(origen=self)

    def _ir_nuevo_pedido(self) -> None:
        self.lift()
        self.focus_force()

    def _abrir_reporte_precios(self) -> None:
        if self.navegador is not None:
            self.navegador.abrir_reporte_precios(origen=self)

    def _abrir_stock(self) -> None:
        if self.navegador is not None:
            self.navegador.abrir_stock(origen=self)

    def _abrir_salidas(self) -> None:
        if self.navegador is not None:
            self.navegador.abrir_salidas(origen=self)

    def _salir(self) -> None:
        if self.navegador is not None:
            self.navegador.volver_menu(self)
        else:
            self.destroy()

    def _crear_cabecera(self, parent: tk.Misc) -> None:
        c = self._colores()
        marco = tk.LabelFrame(parent, text="  Datos del pedido  ",
                              font=("Segoe UI", 10, "bold"), bg=c["surface"], fg=c["burgundy"],
                              bd=1, relief="solid", padx=10, pady=5)
        marco.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        marco.columnconfigure(0, weight=3)
        marco.columnconfigure(1, weight=1)
        marco.columnconfigure(2, weight=1)
        marco.columnconfigure(3, weight=1)

        def label(texto, row, col, **kw):
            return tk.Label(marco, text=texto, font=("Segoe UI", 9, "bold"),
                            bg=c["surface"], fg=c["text"], **kw).grid(row=row, column=col, sticky="w", **kw.get("grid", {}))

        tk.Label(marco, text="Cliente", font=("Segoe UI", 9, "bold"), bg=c["surface"], fg=c["text"]).grid(row=0, column=0, sticky="w", pady=(0, 2))
        tk.Label(marco, text="Modalidad", font=("Segoe UI", 9, "bold"), bg=c["surface"], fg=c["text"]).grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(0, 2))
        tk.Label(marco, text="Fecha de entrega", font=("Segoe UI", 9, "bold"), bg=c["surface"], fg=c["text"]).grid(row=2, column=0, sticky="w", pady=(3, 2))
        tk.Label(marco, text="Hora de entrega", font=("Segoe UI", 9, "bold"), bg=c["surface"], fg=c["text"]).grid(row=2, column=1, sticky="w", padx=(12, 0), pady=(3, 2))
        tk.Label(marco, text="Fecha de elaboración", font=("Segoe UI", 9, "bold"), bg=c["surface"], fg=c["text"]).grid(row=2, column=2, sticky="w", padx=(12, 0), pady=(3, 2))
        tk.Label(marco, text="Importe de envío", font=("Segoe UI", 9, "bold"), bg=c["surface"], fg=c["text"]).grid(row=2, column=3, sticky="w", padx=(12, 0), pady=(5, 2))

        cliente_wrap = tk.Frame(marco, bg=c["surface"])
        cliente_wrap.grid(row=1, column=0, sticky="ew")
        cliente_wrap.columnconfigure(0, weight=1)
        self.cbo_cliente = ComboPredictivo(cliente_wrap, state="readonly")
        self.cbo_cliente.grid(row=0, column=0, sticky="ew")
        tk.Button(cliente_wrap, text="＋ Nuevo cliente", command=self._nuevo_cliente,
                  font=("Segoe UI", 9, "bold"), bg=c["surface2"], fg=c["text"], bd=0,
                  relief="flat", padx=10, pady=6, cursor="hand2",
                  activebackground=c["border"]).grid(row=0, column=1, padx=(8, 0))

        self.cbo_modalidad = ttk.Combobox(marco, state="readonly", style="Pedido.TCombobox")
        self.cbo_modalidad.grid(row=1, column=1, sticky="ew", padx=(12, 0))

        self.txt_fecha_entrega = DateEntry(marco, date_pattern="dd/mm/yyyy", locale="es_AR",
                                           firstweekday="monday", width=14, style="Pedido.TEntry")
        self.txt_fecha_entrega.grid(row=3, column=0, sticky="ew")
        self.txt_fecha_entrega.bind("<<DateEntrySelected>>", self._sugerir_fecha_elaboracion)

        self.hora_entrega = ControlHora(fila_fechas if False else marco, hora_inicial=12, minuto_inicial=0, permitir_vacio=True)
        self.hora_entrega.configure(style="Pedido.TFrame")
        self.hora_entrega.grid(row=3, column=1, sticky="w", padx=(12, 0))

        self.txt_fecha_elaboracion = DateEntry(marco, date_pattern="dd/mm/yyyy", locale="es_AR",
                                               firstweekday="monday", width=14, style="Pedido.TEntry")
        self.txt_fecha_elaboracion.grid(row=3, column=2, sticky="ew", padx=(12, 0))

        self.txt_importe_envio = ttk.Entry(marco, justify="right", style="Pedido.TEntry")
        self.txt_importe_envio.grid(row=3, column=3, sticky="ew", padx=(12, 0))
        self.txt_importe_envio.bind("<KeyRelease>", lambda _e: self._actualizar_grilla())

        self.cbo_cliente.bind("<<ComboboxSelected>>", self._actualizar_direccion_cliente)
        self.cbo_modalidad.bind("<<ComboboxSelected>>", self._sugerir_fecha_elaboracion)

        tk.Label(marco, text="Dirección de entrega", font=("Segoe UI", 9, "bold"), bg=c["surface"], fg=c["text"]).grid(row=4, column=0, sticky="w", pady=(3, 2))
        tk.Label(marco, text="Confirmación", font=("Segoe UI", 9, "bold"), bg=c["surface"], fg=c["text"]).grid(row=4, column=2, sticky="w", padx=(12, 0), pady=(3, 2))

        self.txt_direccion = ttk.Entry(marco, style="Pedido.TEntry")
        self.txt_direccion.grid(row=5, column=0, columnspan=2, sticky="ew")
        self.requiere_confirmacion = tk.BooleanVar(value=False)
        ttk.Checkbutton(marco, text="Requiere confirmación", variable=self.requiere_confirmacion).grid(row=5, column=2, sticky="w", padx=(12, 0))

        tk.Label(marco, text="Observaciones", font=("Segoe UI", 9, "bold"), bg=c["surface"], fg=c["text"]).grid(row=4, column=3, sticky="w", padx=(12, 0), pady=(3, 2))
        self.txt_observaciones = tk.Text(marco, height=2, width=28, wrap="word", font=("Segoe UI", 9),
                                         bg=c["input"], fg=c["text"], insertbackground=c["text"],
                                         relief="solid", bd=1, highlightthickness=1,
                                         highlightbackground=c["border"], highlightcolor=c["burgundy"])
        self.txt_observaciones.grid(row=5, column=3, sticky="ew", padx=(12, 0))

    def _crear_carga_producto(self, parent: tk.Misc) -> None:
        c = self._colores()
        marco = tk.LabelFrame(parent, text="  Agregar productos  ",
                              font=("Segoe UI", 10, "bold"), bg=c["surface"], fg=c["burgundy"],
                              bd=1, relief="solid", padx=10, pady=5)
        marco.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        marco.columnconfigure(0, weight=4)
        marco.columnconfigure(1, weight=1)
        marco.columnconfigure(2, weight=1)
        marco.columnconfigure(3, weight=1)
        marco.columnconfigure(4, weight=0)

        etiquetas = [("Producto",0), ("Cantidad",1), ("Tipo de precio",2), ("Precio unitario",3), ("Descuento",4)]
        for texto, col in etiquetas:
            tk.Label(marco, text=texto, font=("Segoe UI", 9, "bold"), bg=c["surface"], fg=c["text"]).grid(row=0, column=col, sticky="w", padx=(0 if col == 0 else 10, 0), pady=(0, 2))

        self.cbo_producto = ComboPredictivo(marco, state="readonly")
        self.cbo_producto.grid(row=1, column=0, sticky="ew")
        self.cbo_producto.bind("<<ComboboxSelected>>", self._actualizar_precio)

        self.txt_cantidad = ttk.Entry(marco, justify="right", style="Pedido.TEntry")
        self.txt_cantidad.grid(row=1, column=1, sticky="ew", padx=(10, 0))

        self.cbo_tipo_precio = ttk.Combobox(marco, state="readonly", values=("MENOR", "MAYOR", "ESPECIAL"), style="Pedido.TCombobox")
        self.cbo_tipo_precio.grid(row=1, column=2, sticky="ew", padx=(10, 0))
        self.cbo_tipo_precio.bind("<<ComboboxSelected>>", self._actualizar_precio)

        self.txt_precio = ttk.Entry(marco, justify="right", style="Pedido.TEntry")
        self.txt_precio.grid(row=1, column=3, sticky="ew", padx=(10, 0))

        self.txt_descuento = ttk.Entry(marco, justify="right", style="Pedido.TEntry")
        self.txt_descuento.grid(row=1, column=4, sticky="ew", padx=(10, 0))
        self.txt_descuento.bind("<KeyRelease>", lambda _e: self._actualizar_grilla())

        tk.Button(marco, text="＋  Agregar producto", command=self._agregar_producto,
                  font=("Segoe UI", 9, "bold"), bg=c["burgundy"], fg="#ffffff", bd=0,
                  relief="flat", padx=15, pady=7, cursor="hand2",
                  activebackground=c["burgundy_dark"], activeforeground="#ffffff").grid(
                      row=1, column=5, padx=(12, 0), sticky="e")

        tk.Label(marco, text="Observación del producto", font=("Segoe UI", 9, "bold"),
                 bg=c["surface"], fg=c["muted"]).grid(row=2, column=0, columnspan=2, sticky="w", pady=(3, 2))
        self.txt_observacion_producto = ttk.Entry(marco, style="Pedido.TEntry")
        self.txt_observacion_producto.grid(row=3, column=0, columnspan=4, sticky="ew")

    def _crear_detalle(self, parent: tk.Misc) -> None:
        c = self._colores()
        marco = tk.LabelFrame(parent, text="  Detalle del pedido  ",
                              font=("Segoe UI", 10, "bold"), bg=c["surface"], fg=c["burgundy"],
                              bd=1, relief="solid", padx=8, pady=5)
        marco.grid(row=3, column=0, sticky="nsew", pady=(0, 5))
        marco.grid_propagate(False)
        marco.configure(height=145)
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(0, weight=1)

        columnas = ("producto", "cantidad", "tipo", "precio", "descuento", "subtotal")
        self.grilla = ttk.Treeview(marco, columns=columnas, show="headings", selectmode="browse", height=6)
        self.grilla.bind("<Delete>", self._quitar_producto_tecla)
        self.grilla.bind("<BackSpace>", self._quitar_producto_tecla)
        self.grilla.bind("<<TreeviewSelect>>", self._guardar_seleccion_detalle)
        self._producto_seleccionado_id = None
        titulos = {"producto":"Producto", "cantidad":"Cantidad", "tipo":"Tipo", "precio":"Precio unit.", "descuento":"Descuento", "subtotal":"Subtotal"}
        for columna, titulo in titulos.items():
            self.grilla.heading(columna, text=titulo)
        self.grilla.column("producto", width=330, minwidth=220, anchor="w", stretch=True)
        self.grilla.column("cantidad", width=85, minwidth=70, anchor="center", stretch=False)
        self.grilla.column("tipo", width=100, minwidth=85, anchor="center", stretch=False)
        for columna in ("precio", "descuento", "subtotal"):
            self.grilla.column(columna, width=120, minwidth=100, anchor="e", stretch=False)
        barra = ttk.Scrollbar(marco, orient="vertical", command=self.grilla.yview)
        self.grilla.configure(yscrollcommand=barra.set)
        self.grilla.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")

        # La ayuda se mantiene fuera de la grilla para no quitarle altura
        # a las filas del detalle. En pantallas de 768 px, ese espacio
        # reducido podía dejar la primera fila prácticamente oculta.
        self.lbl_ayuda_detalle = tk.Label(
            marco,
            text="Seleccioná una fila para quitarla.",
            font=("Segoe UI", 8),
            bg=c["surface"],
            fg=c["muted"],
            anchor="w",
        )
        self.lbl_ayuda_detalle.grid(row=1, column=0, sticky="w", pady=(1, 0))

        # Aseguramos una altura mínima real para el área de filas.
        marco.rowconfigure(0, weight=1, minsize=105)

    def _crear_pie(self, parent: tk.Misc) -> None:
        c = self._colores()
        pie = tk.Frame(parent, bg=c["surface"], bd=0, highlightthickness=1, highlightbackground=c["border"], padx=10, pady=6)
        pie.grid(row=4, column=0, sticky="ew")
        pie.columnconfigure(1, weight=1)

        tk.Button(pie, text="−  Quitar producto", command=self._quitar_producto,
                  font=("Segoe UI", 9, "bold"), bg=c["surface2"], fg=c["text"], bd=0,
                  relief="flat", padx=10, pady=4, cursor="hand2",
                  activebackground=c["border"]).grid(row=0, column=0, sticky="w")

        total_box = tk.Frame(pie, bg=c["surface2"], bd=0, highlightthickness=1, highlightbackground=c["border"], padx=14, pady=3)
        total_box.grid(row=0, column=1, sticky="e", padx=15)
        self.total_box = total_box
        self.total_caption = tk.Label(total_box, text="TOTAL DEL PEDIDO", font=("Segoe UI", 8, "bold"), bg=c["surface2"], fg=c["muted"])
        self.total_caption.pack(anchor="e")
        self.total_texto = tk.StringVar(value="Total: $ 0,00")
        self.lbl_total = tk.Label(total_box, textvariable=self.total_texto, font=("Segoe UI", 16, "bold"), bg=c["surface2"], fg=c["burgundy"])
        self.lbl_total.pack(anchor="e")

        tk.Button(pie, text="Cancelar", command=self.destroy,
                  font=("Segoe UI", 9, "bold"), bg=c["surface2"], fg=c["text"], bd=0,
                  relief="flat", padx=12, pady=4, cursor="hand2",
                  activebackground=c["border"]).grid(row=0, column=2, padx=(0, 8))
        tk.Button(pie, text="✓  Guardar pedido", command=self._guardar,
                  font=("Segoe UI", 9, "bold"), bg=c["burgundy"], fg="#ffffff", bd=0,
                  relief="flat", padx=15, pady=4, cursor="hand2",
                  activebackground=c["burgundy_dark"], activeforeground="#ffffff").grid(row=0, column=3)

    def _cargar_clientes(
        self,
        id_seleccionar: int | None = None,
    ) -> None:
        clientes = listar_clientes()

        self._clientes_por_texto.clear()
        self._clientes_datos_por_texto.clear()

        textos_clientes: list[str] = []
        texto_seleccionado = None

        for cliente in clientes:
            id_cliente = int(
                cliente["id_cliente"]
            )

            texto = (
                f"{id_cliente} - "
                f"{cliente['nombre']}"
            )

            textos_clientes.append(texto)

            self._clientes_por_texto[
                texto
            ] = id_cliente

            # NUEVO:
            self._clientes_datos_por_texto[
                texto
            ] = cliente

            if id_cliente == id_seleccionar:
                texto_seleccionado = texto

        self.cbo_cliente.establecer_valores(
            textos_clientes
        )

        if texto_seleccionado is not None:
            self.cbo_cliente.set(
                texto_seleccionado
            )

            # Esto también resuelve el caso
            # de + Nuevo cliente auto-seleccionado.
            self._actualizar_direccion_cliente()

    def _cargar_catalogos(self) -> None:
        try:
            self._cargar_clientes()
            modalidades = listar_modalidades()
            productos = listar_productos()

        except Exception as error:
            messagebox.showerror(
                "Nuevo pedido",
                "No se pudieron cargar los catálogos."
                f"\n\n{error}",
                parent=self,
            )
            self.destroy()
            return

        
        self.cbo_modalidad.configure(
            values=modalidades
        )

        textos_productos: list[str] = []

        for producto in productos:
            texto = (
                f"{producto['id_producto']} - "
                f"{producto['descripcion']} "
                f"| Stock: {producto['stock_actual']}"
            )

            textos_productos.append(texto)
            self._productos_por_texto[texto] = producto

        self.cbo_producto.establecer_valores(
            textos_productos
        )
    def _nuevo_cliente(self) -> None:
        ventana = tk.Toplevel(self)

        ventana.title("Nuevo cliente")
        ventana.transient(self)
        ventana.resizable(False, False)
        ventana.grab_set()

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

        ttk.Label(
            marco,
            text="Nuevo cliente",
            font=("Segoe UI", 14, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 12),
        )

        ttk.Label(
            marco,
            text=(
                "Verifique primero que el cliente "
                "no exista en la búsqueda."
            ),
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 12),
        )

        campos = (
            ("Nombre *", "nombre"),
            ("Dirección", "direccion"),
            ("Localidad", "localidad"),
            ("Teléfono", "telefono"),
            ("Celular", "celular"),
        )

        entradas: dict[str, ttk.Entry] = {}

        for fila, (
            etiqueta,
            campo,
        ) in enumerate(
            campos,
            start=2,
        ):
            ttk.Label(
                marco,
                text=etiqueta,
            ).grid(
                row=fila,
                column=0,
                padx=(0, 10),
                pady=4,
                sticky="w",
            )

            entrada = ttk.Entry(
                marco,
                width=42,
            )
            entrada.grid(
                row=fila,
                column=1,
                pady=4,
                sticky="ew",
            )

            entradas[campo] = entrada

        acciones = ttk.Frame(marco)
        acciones.grid(
            row=7,
            column=0,
            columnspan=2,
            sticky="e",
            pady=(14, 0),
        )

    def guardar() -> None:
        nombre = (
            entradas["nombre"]
            .get()
            .strip()
        )

        if not nombre:
            messagebox.showwarning(
                "Nuevo cliente",
                "Debe indicar el nombre.",
                parent=ventana,
            )

            entradas[
                "nombre"
            ].focus_set()

            return

        try:
            id_cliente = agregar_cliente(
                nombre=nombre,
                direccion=(
                    entradas["direccion"]
                    .get()
                    .strip()
                    or None
                ),
                localidad=(
                    entradas["localidad"]
                    .get()
                    .strip()
                    or None
                ),
                telefono=(
                    entradas["telefono"]
                    .get()
                    .strip()
                    or None
                    ),
                    celular=(
                    entradas["celular"]
                    .get()
                    .strip()
                    or None
                ),
            )

            self._cargar_clientes(
                id_cliente
            )

        except Exception as error:
            messagebox.showerror(
                "Nuevo cliente",
                (
                    "No se pudo registrar "
                    "el cliente."
                    f"\n\n{error}"
                ),
                parent=ventana,
            )
            return

        ventana.destroy()

        messagebox.showinfo(
            "Nuevo cliente",
            (
                "Cliente registrado "
                "correctamente."
            ),
        parent=self,
        )

        self.cbo_cliente.focus_set()

        ttk.Button(
            acciones,
            text="Cancelar",
            command=ventana.destroy,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            acciones,
            text="Guardar cliente",
            command=guardar,
        ).pack(
            side="left",
        )

        entradas["nombre"].focus_set()

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
    def _inicializar_formulario(self) -> None:
        hoy = date.today()

        self.txt_fecha_entrega.set_date(hoy)
        self.txt_fecha_elaboracion.set_date(hoy)
        self.txt_importe_envio.insert(0, "0,00")
        self.txt_descuento.insert(0, "0,00")
        self.cbo_tipo_precio.set("MAYOR")

        modalidades = self.cbo_modalidad.cget("values")

        if modalidades:
            self.cbo_modalidad.set(modalidades[0])
            self._sugerir_fecha_elaboracion()

        self.cbo_cliente.focus_set()
    def _actualizar_direccion_cliente(
        self,
        _evento=None,
    ) -> None:
        cliente = (
            self._clientes_datos_por_texto.get(
                self.cbo_cliente.get()
            )
        )

        self.txt_direccion.delete(
            0,
            "end",
        )

        if not cliente:
            return

        direccion = str(
            cliente.get("direccion")
            or ""
        ).strip()

        if direccion:
            self.txt_direccion.insert(
                0,
                direccion,
            )

    def _sugerir_fecha_elaboracion(
        self,
        _evento=None,
    ) -> None:
        fecha_entrega = (
            self.txt_fecha_entrega.get_date()
        )

        modalidad = (
            self.cbo_modalidad.get()
            .strip()
            .upper()
        )

        if modalidad == "REPARTO":
            fecha_sugerida = (
                fecha_entrega - timedelta(days=1)
            )
        else:
            fecha_sugerida = fecha_entrega

        self.txt_fecha_elaboracion.set_date(
            fecha_sugerida
        )

    def _actualizar_precio(self, _evento=None) -> None:
        producto = self._productos_por_texto.get(
            self.cbo_producto.get()
        )

        if not producto:
            return

        tipo = self.cbo_tipo_precio.get().upper()

        if tipo == "MENOR":
            precio = Decimal(
                str(producto["precio_menor"] or 0)
            )

        elif tipo == "MAYOR":
            precio = Decimal(
                str(producto["precio_mayor"] or 0)
            )

        else:
            self.txt_precio.configure(state="normal")
            self.txt_precio.focus_set()
            return

        self.txt_precio.configure(state="normal")
        self.txt_precio.delete(0, "end")
        self.txt_precio.insert(
            0,
            formato_decimal(precio),
        )
        self.txt_precio.configure(state="readonly")

    def _resolver_producto_seleccionado(self) -> dict[str, Any] | None:
        """Resuelve el producto aunque el ComboPredictivo no conserve el texto exacto."""
        texto = self.cbo_producto.get().strip()
        if not texto:
            return None

        producto = self._productos_por_texto.get(texto)
        if producto:
            return producto

        # El formato del catálogo es: "ID - Descripción | Stock: X".
        try:
            id_texto = texto.split("-", 1)[0].strip()
            id_producto = int(id_texto)
        except (ValueError, TypeError):
            id_producto = None

        if id_producto is not None:
            for datos in self._productos_por_texto.values():
                try:
                    if int(datos["id_producto"]) == id_producto:
                        return datos
                except (KeyError, TypeError, ValueError):
                    continue

        # Último intento: coincidencia normalizada por descripción.
        buscado = normalizar_busqueda(texto)
        for texto_catalogo, datos in self._productos_por_texto.items():
            if normalizar_busqueda(texto_catalogo) == buscado:
                return datos

        return None

    def _agregar_producto(self) -> None:
        try:
            producto = self._resolver_producto_seleccionado()

            if not producto:
                raise ValueError(
                    "Debe seleccionar un producto de la lista."
                )

            cantidad = convertir_cantidad(
                self.txt_cantidad.get()
            )

            if cantidad <= 0:
                raise ValueError(
                    "La cantidad debe ser mayor que cero."
                )

            tipo_precio = (
                self.cbo_tipo_precio.get()
                .strip()
                .upper()
            )

            if tipo_precio not in (
                "MENOR",
                "MAYOR",
                "ESPECIAL",
            ):
                raise ValueError(
                    "Debe seleccionar un tipo de precio."
                )

            # Si el evento de selección no llegó a cargar el precio, lo
            # calculamos aquí para que Agregar producto sea autosuficiente.
            texto_precio = self.txt_precio.get().strip()
            if not texto_precio and tipo_precio in ("MENOR", "MAYOR"):
                campo = "precio_menor" if tipo_precio == "MENOR" else "precio_mayor"
                precio_catalogo = Decimal(str(producto.get(campo) or 0))
                self.txt_precio.configure(state="normal")
                self.txt_precio.delete(0, "end")
                self.txt_precio.insert(0, formato_decimal(precio_catalogo))
                self.txt_precio.configure(state="readonly")

            precio = convertir_decimal(
                self.txt_precio.get()
            )

            if precio <= 0:
                raise ValueError(
                    "El precio unitario debe ser mayor que cero."
                )

            descuento = convertir_decimal(
                self.txt_descuento.get()
            )

            if descuento < 0:
                raise ValueError(
                    "El descuento no puede ser negativo."
                )

            id_producto = int(producto["id_producto"])
            existente = self._detalle.get(id_producto)

            if existente:
                cantidad += existente.cantidad

            detalle = DetallePedido(
                id_producto=id_producto,
                descripcion=str(producto["descripcion"]),
                cantidad=cantidad,
                tipo_precio=tipo_precio,
                precio_unitario=precio,
                descuento=descuento,
                observaciones=(
                    self.txt_observacion_producto
                    .get()
                    .strip()
                    or None
                ),
            )

            # Primero guardamos el detalle y actualizamos la tabla.
            # El refresco ocurre antes de limpiar los campos de carga.
            self._detalle[id_producto] = detalle
            self._producto_seleccionado_id = id_producto
            self._actualizar_grilla(seleccionar_id=id_producto)
            self.update_idletasks()

            # Reforzamos la selección después de que Tk haya terminado
            # de dibujar la tabla, evitando que el refresco visual la deje vacía.
            self.after_idle(
                lambda: self._seleccionar_detalle(id_producto)
            )

            self._limpiar_producto()

        except Exception as error:
            messagebox.showwarning(
                "Agregar producto",
                str(error),
                parent=self,
            )

    def _seleccionar_detalle(self, id_producto: int) -> None:
        """Deja visible y seleccionada una línea recién agregada."""
        try:
            iid = str(id_producto)
            if iid in self.grilla.get_children():
                self.grilla.selection_set(iid)
                self.grilla.focus(iid)
                self.grilla.see(iid)
                self._producto_seleccionado_id = id_producto
        except tk.TclError:
            pass

    def _guardar_seleccion_detalle(self, _evento=None) -> None:
        seleccion = self.grilla.selection()
        self._producto_seleccionado_id = (
            int(seleccion[0]) if seleccion else None
        )

    def _quitar_producto_tecla(self, _evento=None) -> str:
        self._quitar_producto()
        return "break"

    def _quitar_producto(self) -> None:
        seleccion = self.grilla.selection()

        # Usamos también la última selección registrada para que el botón
        # siga funcionando aunque el foco haya pasado momentáneamente a otro widget.
        id_producto = None
        if seleccion:
            id_producto = int(seleccion[0])
        elif self._producto_seleccionado_id in self._detalle:
            id_producto = self._producto_seleccionado_id
        elif len(self._detalle) == 1:
            # Si solo hay un producto, lo dejamos seleccionado automáticamente.
            id_producto = next(iter(self._detalle))

        if id_producto is None:
            messagebox.showwarning(
                "Quitar producto",
                "Seleccioná un producto de la tabla para quitarlo.",
                parent=self,
            )
            return

        self._detalle.pop(id_producto, None)
        self._producto_seleccionado_id = None
        self._actualizar_grilla()

    def _actualizar_grilla(self, seleccionar_id: int | None = None) -> None:
        for item in self.grilla.get_children():
            self.grilla.delete(item)

        total = Decimal("0")

        ultimo_iid = None
        for detalle in self._detalle.values():
            total += detalle.subtotal

            iid = str(detalle.id_producto)
            ultimo_iid = iid
            self.grilla.insert(
                "",
                "end",
                iid=iid,
                values=(
                    detalle.descripcion,
                    formato_cantidad(
                        detalle.cantidad
                    ),
                    detalle.tipo_precio,
                    formato_moneda(
                        detalle.precio_unitario
                    ),
                    formato_moneda(
                        detalle.descuento
                    ),
                    formato_moneda(
                        detalle.subtotal
                    ),
                ),
            )

        # Dejamos visible y seleccionada la última línea agregada.
        objetivo = seleccionar_id
        if objetivo is None and self._producto_seleccionado_id in self._detalle:
            objetivo = self._producto_seleccionado_id
        if objetivo is None and ultimo_iid is not None:
            objetivo = int(ultimo_iid)

        if objetivo is not None and str(objetivo) in self.grilla.get_children():
            iid_objetivo = str(objetivo)
            self.grilla.selection_set(iid_objetivo)
            self.grilla.focus(iid_objetivo)
            self.grilla.see(iid_objetivo)
            self._producto_seleccionado_id = int(objetivo)

        importe_envio = Decimal("0")

        try:
            importe_envio = convertir_decimal(
                self.txt_importe_envio.get()
            )
        except ValueError:
            pass

        total += importe_envio

        self.total_texto.set(
            f"Total: {formato_moneda(total)}"
        )

    def _limpiar_producto(self) -> None:
        self.cbo_producto.limpiar()

        self.txt_cantidad.delete(0, "end")

        self.cbo_tipo_precio.set("MAYOR")

        self.txt_precio.configure(state="normal")
        self.txt_precio.delete(0, "end")

        self.txt_descuento.delete(0, "end")
        self.txt_descuento.insert(0, "0,00")

        self.txt_observacion_producto.delete(
            0,
            "end",
        )

        self.cbo_producto.focus_set()

    def _obtener_observaciones(self) -> str:
        widget = self.txt_observaciones
        if isinstance(widget, tk.Text):
            return widget.get("1.0", "end-1c").strip()
        return widget.get().strip()

    def _guardar(self) -> None:
        try:
            texto_cliente = self.cbo_cliente.get()

            if texto_cliente not in self._clientes_por_texto:
                raise ValueError(
                    "Debe seleccionar un cliente."
                )

            modalidad = self.cbo_modalidad.get().strip()

            if not modalidad:
                raise ValueError(
                    "Debe seleccionar una modalidad."
                )

            fecha_entrega = (
                self.txt_fecha_entrega.get_date()
                )            

            fecha_elaboracion = (
                self.txt_fecha_elaboracion.get_date()
                )

            hora_entrega = (
                self.hora_entrega.obtener_hora()
                )

            importe_envio = convertir_decimal(
                self.txt_importe_envio.get()
                )

            detalle = [
                {
                    "id_producto": item.id_producto,
                    "cantidad": item.cantidad,
                    "tipo_precio": item.tipo_precio,
                    "precio_unitario":
                        item.precio_unitario,
                    "descuento": item.descuento,
                    "observaciones":
                        item.observaciones,
                }
                for item in self._detalle.values()
            ]

            id_pedido = guardar_pedido(
                id_cliente=self._clientes_por_texto[
                    texto_cliente
                ],
                modalidad_entrega=modalidad,
                fecha_entrega=fecha_entrega,
                hora_entrega=hora_entrega,
                fecha_elaboracion=fecha_elaboracion,
                requiere_confirmacion=(
                    self.requiere_confirmacion.get()
                ),
                direccion_entrega=(
                    self.txt_direccion.get().strip()
                    or None
                ),
                importe_envio=importe_envio,
                observaciones=(
                    self._obtener_observaciones()
                    or None
                ),
                detalle=detalle,
            )

        except Exception as error:
            messagebox.showerror(
                "Guardar pedido",
                "No se pudo guardar el pedido."
                f"\n\n{error}",
                parent=self,
            )
            return

        messagebox.showinfo(
            "Guardar pedido",
            "Pedido guardado correctamente."
            f"\n\nNúmero de pedido: {id_pedido}",
            parent=self,
        )

        if self._al_guardar:
            self._al_guardar(id_pedido)

        self.destroy()

    def _centrar(self, parent: tk.Misc) -> None:
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

        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    def _ajustar_tamano_inicial(
        self,
    ) -> None:
        ancho_pantalla = (
            self.winfo_screenwidth()
        )

        alto_pantalla = (
            self.winfo_screenheight()
        )

        # Aproximadamente 92 % del ancho
        # y 88 % del alto disponible.
        ancho = int(
            ancho_pantalla * 0.92
        )

        alto = int(
            alto_pantalla * 0.88
        )

        # Nunca superar físicamente la pantalla.
        ancho = min(
            ancho,
            ancho_pantalla - 30,
        )

        alto = min(
            alto,
            alto_pantalla - 70,
        )

        # Mínimos razonables, pero sin obligar
        # a una pantalla pequeña a superar su tamaño.
        ancho_minimo = min(
            800,
            ancho,
        )

        alto_minimo = min(
            540,
            alto,
        )

        self.minsize(
            ancho_minimo,
            alto_minimo,
        )

        x = max(
            (ancho_pantalla - ancho) // 2,
            0,
        )

        y = max(
            (alto_pantalla - alto) // 2 - 10,
            0,
        )

        self.geometry(
            f"{ancho}x{alto}+{x}+{y}"
        )