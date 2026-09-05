from __future__ import annotations

import tkinter as tk
from datetime import datetime
from decimal import Decimal
from tkinter import messagebox, ttk
from typing import Any
from ui.ventana_util import maximizar_ventana

from db.cobro_repository import (
    ErrorCobro,
    listar_clientes_con_saldo,
    listar_medios_pago,
    listar_ventas_pendientes,
    obtener_caja_abierta,
    registrar_cobro,
)
from ui.pedido import (
    convertir_decimal,
    formato_decimal,
)

from ui.estado_cuenta import (
    VentanaEstadoCuenta,
)
from typing import TYPE_CHECKING

from ui.navegacion import (
    crear_barra_navegacion,
)

if TYPE_CHECKING:
    from ui.navegacion import NavegadorPOS


def numero(valor: Any) -> Decimal:
    if valor is None:
        return Decimal("0")

    return Decimal(str(valor))


def fecha_hora_texto(valor: Any) -> str:
    if valor is None:
        return ""

    if isinstance(valor, datetime):
        return valor.strftime(
            "%d/%m/%Y %H:%M"
        )

    return str(valor)


class VentanaCobros(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        navegador=None,
    ) -> None:
        super().__init__(parent)

        self.navegador = navegador

        self._id_venta_contexto: int | None = None
        self._caja: dict[str, Any] | None = None

        self._clientes: dict[
            str,
            dict[str, Any],
        ] = {}

        self._ventas: dict[
            str,
            dict[str, Any],
        ] = {}

        self._aplicaciones: dict[
            int,
            Decimal,
        ] = {}

        self._catalogo_medios: dict[
            str,
            dict[str, Any],
        ] = {}

        self._medios_cobro: dict[
            str,
            dict[str, Any],
        ] = {}

        self._contador_medios = 0

        self._cliente_seleccionado: (
            dict[str, Any] | None
        ) = None

        self._ancho_pantalla = (
            self.winfo_screenwidth()
        )
        self._alto_pantalla = (
            self.winfo_screenheight()
        )

        self._pantalla_compacta = (
            self._ancho_pantalla < 1450
            or self._alto_pantalla < 800
        )

        self.title("Cobros y cuenta corriente")
        # self.transient(parent)
        self.resizable(True, True)

        # self._configurar_estilos()
        # self._ajustar_tamano_inicial()
        maximizar_ventana(self)

        if self.navegador is not None:
            crear_barra_navegacion(
                ventana=self,
                navegador=self.navegador,
                modulo_actual="cobros",
            )

        self._crear_interfaz()

        if not self._cargar_caja():
            self.after_idle(self.destroy)
            return

        self._cargar_catalogo_medios()
        self._actualizar_clientes()
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

        try:
            self.state("zoomed")

        except tk.TclError:
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


    def _importe_cobro_declarado(self) -> Decimal:
        texto = self.txt_importe_cobro.get().strip()

        if not texto:
            return Decimal("0")

        return convertir_decimal(
            texto,
            decimales=2,
        )


    def _completar_saldo_cliente(self) -> None:
        if not self._cliente_seleccionado:
            return

        saldo = numero(
            self._cliente_seleccionado["saldo"]
        )

        self.txt_importe_cobro.delete(0, "end")
        self.txt_importe_cobro.insert(
            0,
            formato_decimal(
                saldo,
                decimales=2,
            ),
        )

        self._actualizar_resumen()

    def _configurar_estilos(self) -> None:
        estilo = ttk.Style(self)

        tamano_fuente = (
            10
            if self._pantalla_compacta
            else 11
        )

        alto_fila = (
            26
            if self._pantalla_compacta
            else 30
        )

        padding_boton = (
            (7, 4)
            if self._pantalla_compacta
            else (10, 6)
        )

        estilo.configure(
            ".",
            font=(
                "Segoe UI",
                tamano_fuente,
            ),
        )

        estilo.configure(
            "TButton",
            font=(
                "Segoe UI",
                tamano_fuente,
                "bold",
            ),
            padding=padding_boton,
        )

        estilo.configure(
            "TEntry",
            padding=(5, 4),
        )

        estilo.configure(
            "TCombobox",
            padding=(5, 4),
        )

        estilo.configure(
            "TCheckbutton",
            font=(
                "Segoe UI",
                tamano_fuente,
            ),
        )

        estilo.configure(
            "TLabelframe.Label",
            font=(
                "Segoe UI",
                tamano_fuente,
                "bold",
            ),
        )

        estilo.configure(
            "Treeview",
            font=(
                "Segoe UI",
                tamano_fuente,
            ),
            rowheight=alto_fila,
        )

        estilo.configure(
            "Treeview.Heading",
            font=(
                "Segoe UI",
                tamano_fuente,
                "bold",
            ),
        )

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
            text="Cobros y cuenta corriente",
            font=("Segoe UI", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 4),
        )

        self.texto_caja = tk.StringVar(
            value="Comprobando caja..."
        )

        ttk.Label(
            contenedor,
            textvariable=self.texto_caja,
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(0, 8),
        )

        if self._pantalla_compacta:
            self._crear_interfaz_compacta(
                contenedor
            )

        else:
            self._crear_interfaz_amplia(
                contenedor
            )

        self._cambiar_modo_aplicacion()
    def _crear_interfaz_compacta(
        self,
        parent: ttk.Frame,
    ) -> None:
        self.pestanas = ttk.Notebook(
            parent
        )
        self.pestanas.grid(
            row=2,
            column=0,
            sticky="nsew",
        )

        pestana_cuentas = ttk.Frame(
            self.pestanas,
            padding=8,
        )

        pestana_cobro = ttk.Frame(
            self.pestanas,
            padding=8,
        )

        self.pestanas.add(
            pestana_cuentas,
            text="Cuentas pendientes",
        )

        self.pestanas.add(
            pestana_cobro,
            text="Registrar cobro",
        )

        pestana_cuentas.columnconfigure(
            0,
            weight=1,
        )
        pestana_cuentas.rowconfigure(
            0,
            weight=1,
        )

        panel_izquierdo = ttk.Frame(
            pestana_cuentas
        )
        panel_izquierdo.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        panel_izquierdo.columnconfigure(
            0,
            weight=1,
        )
        panel_izquierdo.rowconfigure(
            1,
            weight=1,
        )

        self._crear_busqueda(
            panel_izquierdo
        )

        self._crear_panel_cuentas(
            panel_izquierdo
        )

        pestana_cobro.columnconfigure(
            0,
            weight=1,
        )

        panel_derecho = ttk.Frame(
            pestana_cobro
        )
        panel_derecho.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        panel_derecho.columnconfigure(
            0,
            weight=1,
        )

        self._crear_panel_aplicacion(
            panel_derecho
        )

        self._crear_panel_medios(
            panel_derecho
        )

        self._crear_confirmacion(
            panel_derecho
        )
    def _crear_interfaz_amplia(
        self,
        parent: ttk.Frame,
    ) -> None:
        cuerpo = ttk.Frame(parent)
        cuerpo.grid(
            row=2,
            column=0,
            sticky="nsew",
        )

        cuerpo.columnconfigure(
            0,
            weight=3,
        )

        cuerpo.columnconfigure(
            1,
            weight=2,
        )

        cuerpo.rowconfigure(
            0,
            weight=1,
        )

        panel_izquierdo = ttk.Frame(
            cuerpo
        )
        panel_izquierdo.grid(
            row=0,
            column=0,
            padx=(0, 8),
            sticky="nsew",
        )

        panel_izquierdo.columnconfigure(
            0,
            weight=1,
        )

        panel_izquierdo.rowconfigure(
            1,
            weight=1,
        )

        self._crear_busqueda(
            panel_izquierdo
        )

        self._crear_panel_cuentas(
            panel_izquierdo
        )

        panel_derecho = ttk.Frame(
            cuerpo
        )
        panel_derecho.grid(
            row=0,
            column=1,
            padx=(8, 0),
            sticky="nsew",
        )

        panel_derecho.columnconfigure(
            0,
            weight=1,
        )

        self._crear_panel_aplicacion(
            panel_derecho
        )

        self._crear_panel_medios(
            panel_derecho
        )

        self._crear_confirmacion(
            panel_derecho
        )
    def _crear_busqueda(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Buscar cliente",
            padding=10,
        )
        marco.pack(
            fill="x",
            pady=(0, 8),
        )

        marco.columnconfigure(
            0,
            weight=1,
        )

        self.txt_busqueda = ttk.Entry(
            marco,
        )
        self.txt_busqueda.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        acciones = ttk.Frame(marco)
        acciones.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(8, 0),
        )

        ttk.Button(
            acciones,
            text="Buscar",
            command=self._actualizar_clientes,
        ).pack(
            side="left",
        )

        ttk.Button(
            acciones,
            text="Mostrar todos",
            command=self._limpiar_busqueda,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        self.btn_estado_cuenta = ttk.Button(
            acciones,
            text="Estado de cuenta",
            command=self._abrir_estado_cuenta,
            state="disabled",
        )
        self.btn_estado_cuenta.pack(
            side="right",
        )

        self.txt_busqueda.bind(
            "<Return>",
            lambda _evento:
                self._actualizar_clientes(),
        )

    def _crear_panel_cuentas(
        self,
        parent: ttk.Frame,
    ) -> None:
        panel = ttk.Frame(parent)
        panel.pack(
            fill="both",
            expand=True,
            pady=(0, 10),
        )

        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=2)
        panel.rowconfigure(0, weight=1)

        self._crear_grilla_clientes(panel)
        self._crear_grilla_ventas(panel)

    def _crear_grilla_clientes(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Clientes con saldo",
            padding=8,
        )
        marco.grid(
            row=0,
            column=0,
            padx=(0, 6),
            sticky="nsew",
        )

        columnas = (
            "cliente",
            "saldo",
        )

        self.grilla_clientes = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
            height=6,
        )

        self.grilla_clientes.heading(
            "cliente",
            text="Cliente",
        )
        self.grilla_clientes.heading(
            "saldo",
            text="Saldo",
        )

        self.grilla_clientes.column(
            "cliente",
            width=260,
            anchor="w",
        )
        self.grilla_clientes.column(
            "saldo",
            width=115,
            anchor="e",
        )

        barra = ttk.Scrollbar(
            marco,
            orient="vertical",
            command=self.grilla_clientes.yview,
        )

        self.grilla_clientes.configure(
            yscrollcommand=barra.set,
        )

        self.grilla_clientes.pack(
            side="left",
            fill="both",
            expand=True,
        )

        barra.pack(
            side="right",
            fill="y",
        )

        self.grilla_clientes.bind(
            "<<TreeviewSelect>>",
            self._seleccionar_cliente,
        )

    def _crear_grilla_ventas(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Ventas pendientes",
            padding=8,
        )
        marco.grid(
            row=0,
            column=1,
            padx=(6, 0),
            sticky="nsew",
        )

        columnas = (
            "venta",
            "fecha",
            "total",
            "cobrado",
            "saldo",
            "aplicar",
        )

        self.grilla_ventas = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
            height=6,
        )

        titulos = {
            "venta": "Venta",
            "fecha": "Fecha",
            "total": "Total",
            "cobrado": "Cobrado",
            "saldo": "Saldo",
            "aplicar": "Aplicar",
        }

        anchos = {
            "venta": 70,
            "fecha": 135,
            "total": 100,
            "cobrado": 100,
            "saldo": 100,
            "aplicar": 100,
        }

        for columna in columnas:
            self.grilla_ventas.heading(
                columna,
                text=titulos[columna],
            )

            self.grilla_ventas.column(
                columna,
                width=anchos[columna],
                anchor=(
                    "center"
                    if columna in ("venta", "fecha")
                    else "e"
                ),
            )

        barra = ttk.Scrollbar(
            marco,
            orient="vertical",
            command=self.grilla_ventas.yview,
        )

        self.grilla_ventas.configure(
            yscrollcommand=barra.set,
        )

        self.grilla_ventas.pack(
            side="left",
            fill="both",
            expand=True,
        )

        barra.pack(
            side="right",
            fill="y",
        )

        self.grilla_ventas.bind(
            "<<TreeviewSelect>>",
            self._seleccionar_venta,
        )

    def _crear_panel_aplicacion(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Aplicación a ventas",
            padding=10,
        )
        marco.pack(
            fill="x",
            pady=(0, 8),
        )

        marco.columnconfigure(
            0,
            weight=1,
        )

        self.aplicacion_automatica = (
            tk.BooleanVar(value=True)
        )

        ttk.Checkbutton(
            marco,
            text=(
                "Aplicar automáticamente a las "
                "ventas más antiguas"
            ),
            variable=self.aplicacion_automatica,
            command=self._cambiar_modo_aplicacion,
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 8),
        )

        ttk.Label(
            marco,
            text=(
                "Importe para la venta "
                "seleccionada"
            ),
        ).grid(
            row=1,
            column=0,
            sticky="w",
        )

        self.txt_importe_aplicar = ttk.Entry(
            marco,
            justify="right",
        )
        self.txt_importe_aplicar.grid(
            row=2,
            column=0,
            sticky="ew",
        )

        acciones = ttk.Frame(marco)
        acciones.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(8, 0),
        )

        for columna in range(3):
            acciones.columnconfigure(
                columna,
                weight=1,
                uniform="aplicacion",
            )

        self.btn_aplicar_importe = ttk.Button(
            acciones,
            text="Aplicar importe",
            command=self._aplicar_importe_venta,
        )
        self.btn_aplicar_importe.grid(
            row=0,
            column=0,
            padx=(0, 4),
            sticky="ew",
        )

        self.btn_aplicar_saldo = ttk.Button(
            acciones,
            text="Aplicar saldo completo",
            command=self._aplicar_saldo_completo,
        )
        self.btn_aplicar_saldo.grid(
            row=0,
            column=1,
            padx=4,
            sticky="ew",
        )

        self.btn_vaciar_aplicaciones = ttk.Button(
            acciones,
            text="Vaciar aplicaciones",
            command=self._vaciar_aplicaciones,
        )
        self.btn_vaciar_aplicaciones.grid(
            row=0,
            column=2,
            padx=(4, 0),
            sticky="ew",
        )

    def _crear_panel_medios(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Medios de pago",
            padding=10,
        )
        marco.pack(
            fill="both",
            expand=True,
            pady=(0, 8),
        )

        marco.columnconfigure(
            0,
            weight=2,
        )
        marco.columnconfigure(
            1,
            weight=1,
        )
        marco.columnconfigure(
            2,
            weight=2,
        )
        marco.rowconfigure(
            4,
            weight=1,
        )

        ttk.Label(
            marco,
            text="Medio",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.cbo_medio = ttk.Combobox(
            marco,
            state="readonly",
        )
        self.cbo_medio.grid(
            row=1,
            column=0,
            padx=(0, 8),
            sticky="ew",
        )

        ttk.Label(
            marco,
            text="Importe",
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )

        self.txt_importe_medio = ttk.Entry(
            marco,
            justify="right",
        )
        self.txt_importe_medio.grid(
            row=1,
            column=1,
            padx=(0, 8),
            sticky="ew",
        )

        ttk.Label(
            marco,
            text="Número de comprobante",
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )

        self.txt_referencia = ttk.Entry(
            marco,
        )
        self.txt_referencia.grid(
            row=1,
            column=2,
            sticky="ew",
        )

        acciones = ttk.Frame(marco)
        acciones.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="e",
            pady=(8, 0),
        )

        ttk.Button(
            acciones,
            text="Agregar medio",
            command=self._agregar_medio,
        ).pack(
            side="left",
        )

        ttk.Button(
            acciones,
            text="Quitar seleccionado",
            command=self._quitar_medio,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        columnas = (
            "medio",
            "importe",
            "referencia",
        )

        self.grilla_medios = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
            height=(
                3
                if self._pantalla_compacta
                else 4
            ),
        )

        self.grilla_medios.heading(
            "medio",
            text="Medio de pago",
        )
        self.grilla_medios.heading(
            "importe",
            text="Importe",
        )
        self.grilla_medios.heading(
            "referencia",
            text="Referencia",
        )

        self.grilla_medios.column(
            "medio",
            width=200,
            minwidth=130,
            anchor="w",
            stretch=True,
        )
        self.grilla_medios.column(
            "importe",
            width=120,
            minwidth=90,
            anchor="e",
            stretch=False,
        )
        self.grilla_medios.column(
            "referencia",
            width=280,
            minwidth=130,
            anchor="w",
            stretch=True,
        )

        barra_vertical = ttk.Scrollbar(
            marco,
            orient="vertical",
            command=self.grilla_medios.yview,
        )

        barra_horizontal = ttk.Scrollbar(
            marco,
            orient="horizontal",
            command=self.grilla_medios.xview,
        )

        self.grilla_medios.configure(
            yscrollcommand=barra_vertical.set,
            xscrollcommand=barra_horizontal.set,
        )

        self.grilla_medios.grid(
            row=4,
            column=0,
            columnspan=3,
            sticky="nsew",
            pady=(8, 0),
        )

        barra_vertical.grid(
            row=4,
            column=3,
            sticky="ns",
            pady=(8, 0),
        )

        barra_horizontal.grid(
            row=5,
            column=0,
            columnspan=3,
            sticky="ew",
        )
    def _crear_confirmacion(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Confirmar cobro",
            padding=10,
        )
        marco.pack(fill="x")

        ttk.Label(
            marco,
            text="Importe que paga el cliente",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.txt_importe_cobro = ttk.Entry(
            marco,
            width=22,
            justify="right",
            font=("Segoe UI", 14, "bold"),
        )
        self.txt_importe_cobro.grid(
            row=1,
            column=0,
            padx=(0, 8),
            sticky="w",
        )

        ttk.Button(
            marco,
            text="Completar saldo",
            command=self._completar_saldo_cliente,
        ).grid(
            row=1,
            column=1,
            padx=(10, 12),
            sticky="w",
        )

        self.texto_resumen = tk.StringVar(
            value=(
                "Importe declarado: $0,00 · "
                "Medios cargados: $0,00"
            )
        )

        ttk.Label(
            marco,
            textvariable=self.texto_resumen,
            font=("Segoe UI", 10, "bold"),
            justify="left",
            wraplength=(
                850
                if self._pantalla_compacta
                else 500
)
        ).grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(12, 12),
        )

        ttk.Label(
            marco,
            text="Observaciones",
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
        )

        self.txt_observaciones = ttk.Entry(
            marco,
            width=75,
        )
        self.txt_observaciones.grid(
            row=4,
            column=0,
            columnspan=2,
            padx=(0, 10),
            sticky="ew",
        )

        self.btn_confirmar = ttk.Button(
            marco,
            text="Registrar cobro",
            command=self._confirmar_cobro,
            state="disabled",
        )
        self.btn_confirmar.grid(
            row=4,
            column=2,
        )

        marco.columnconfigure(0, weight=1)

        self.txt_importe_cobro.bind(
            "<KeyRelease>",
            lambda _evento: self._actualizar_resumen(),
        )

    def _cargar_caja(self) -> bool:
        try:
            self._caja = obtener_caja_abierta()

        except Exception as error:
            messagebox.showerror(
                "Cobros",
                "No se pudo consultar la caja."
                f"\n\n{error}",
                parent=self,
            )
            return False

        if not self._caja:
            messagebox.showwarning(
                "Cobros",
                "No hay una sesión de caja abierta.",
                parent=self,
            )
            return False

        self.texto_caja.set(
            f"Caja: {self._caja['caja']} · "
            f"Sesión: {self._caja['id_caja_sesion']} · "
            f"Apertura: "
            f"{fecha_hora_texto(self._caja['fecha_apertura'])}"
        )

        return True

    def _cargar_catalogo_medios(self) -> None:
        try:
            filas = listar_medios_pago()

        except Exception as error:
            messagebox.showerror(
                "Cobros",
                "No se pudieron recuperar "
                "los medios de pago."
                f"\n\n{error}",
                parent=self,
            )
            return

        self._catalogo_medios.clear()

        valores: list[str] = []

        for fila in filas:
            texto = (
                f"{fila['descripcion']} "
                f"({fila['codigo']})"
            )

            valores.append(texto)
            self._catalogo_medios[texto] = fila

        self.cbo_medio.configure(
            values=valores
        )

        if valores:
            self.cbo_medio.set(
                valores[0]
            )

    def _actualizar_clientes(
        self,
        *,
        conservar_id: int | None = None,
    ) -> None:
        busqueda = (
            self.txt_busqueda.get().strip()
            or None
        )

        try:
            filas = listar_clientes_con_saldo(
                busqueda
            )

        except Exception as error:
            messagebox.showerror(
                "Cobros",
                "No se pudieron recuperar "
                "las cuentas corrientes."
                f"\n\n{error}",
                parent=self,
            )
            return

        self._clientes.clear()

        for item in self.grilla_clientes.get_children():
            self.grilla_clientes.delete(item)

        item_a_seleccionar = None

        for indice, fila in enumerate(filas):
            iid = (
                f"cliente-"
                f"{fila['id_cliente']}-"
                f"{indice}"
            )

            self._clientes[iid] = fila

            self.grilla_clientes.insert(
                "",
                "end",
                iid=iid,
                values=(
                    fila["nombre"],
                    "$"
                    + formato_decimal(
                        numero(fila["saldo"]),
                        decimales=2,
                    ),
                ),
            )

            if (
                conservar_id is not None
                and int(fila["id_cliente"])
                == conservar_id
            ):
                item_a_seleccionar = iid

        if item_a_seleccionar:
            self.grilla_clientes.selection_set(
                item_a_seleccionar
            )
            self.grilla_clientes.focus(
                item_a_seleccionar
            )
            self.grilla_clientes.see(
                item_a_seleccionar
            )
            self._seleccionar_cliente()

        else:
            self._limpiar_cliente()

    def _limpiar_busqueda(self) -> None:
        self.txt_busqueda.delete(
            0,
            "end",
        )
        self._actualizar_clientes()

    def _seleccionar_cliente(
        self,
        _evento=None,
    ) -> None:
        seleccion = (
            self.grilla_clientes.selection()
        )

        if not seleccion:
            self._limpiar_cliente()
            return

        self._cliente_seleccionado = (
            self._clientes[seleccion[0]]
        )
        self.btn_estado_cuenta.configure(
            state="normal"
        )
        self.txt_importe_cobro.delete(
            0,
            "end",
)
        self.txt_importe_cobro.insert(
            0,
            formato_decimal(
                numero(
                    self._cliente_seleccionado[
                        "saldo"
                    ]
                ),
                decimales=2,
            ),
)

        self._aplicaciones.clear()
        self._medios_cobro.clear()

        self._recargar_medios()
        self._cargar_ventas(
            int(
                self._cliente_seleccionado[
                    "id_cliente"
                ]
            )
        )

        
    def _cargar_ventas(
        self,
        id_cliente: int,
    ) -> None:
        try:
            filas = listar_ventas_pendientes(
                id_cliente
            )

        except Exception as error:
            messagebox.showerror(
                "Cobros",
                "No se pudieron recuperar "
                "las ventas pendientes."
                f"\n\n{error}",
                parent=self,
            )
            return

        self._ventas.clear()

        for indice, fila in enumerate(filas):
            iid = (
                f"venta-"
                f"{fila['id_venta']}-"
                f"{indice}"
            )

            self._ventas[iid] = fila

        self._recargar_ventas()
        if self._id_venta_contexto is not None:
            self._seleccionar_venta_por_id(
                self._id_venta_contexto
            )

            self._id_venta_contexto = None

    def _recargar_ventas(self) -> None:
        seleccion_anterior = (
            self.grilla_ventas.selection()
        )

        iid_anterior = (
            seleccion_anterior[0]
            if seleccion_anterior
            else None
        )

        for item in self.grilla_ventas.get_children():
            self.grilla_ventas.delete(item)

        for iid, fila in self._ventas.items():
            id_venta = int(
                fila["id_venta"]
            )

            importe_aplicar = (
                self._aplicaciones.get(
                    id_venta,
                    Decimal("0"),
                )
            )

            aplicar_texto = (
                "FIFO"
                if self.aplicacion_automatica.get()
                else formato_decimal(
                    importe_aplicar,
                    decimales=2,
                )
            )

            self.grilla_ventas.insert(
                "",
                "end",
                iid=iid,
                values=(
                    id_venta,
                    fecha_hora_texto(
                        fila["fecha_hora"]
                    ),
                    "$"
                    + formato_decimal(
                        numero(fila["total"]),
                        decimales=2,
                    ),
                    "$"
                    + formato_decimal(
                        numero(
                            fila["importe_cobrado"]
                        ),
                        decimales=2,
                    ),
                    "$"
                    + formato_decimal(
                        numero(
                            fila["saldo_pendiente"]
                        ),
                        decimales=2,
                    ),
                    aplicar_texto,
                ),
            )

        if (
            iid_anterior
            and iid_anterior in self._ventas
        ):
            self.grilla_ventas.selection_set(
                iid_anterior
            )

    def _seleccionar_venta(
        self,
        _evento=None,
    ) -> None:
        seleccion = (
            self.grilla_ventas.selection()
        )

        if not seleccion:
            return

        fila = self._ventas[
            seleccion[0]
        ]

        id_venta = int(
            fila["id_venta"]
        )

        importe = self._aplicaciones.get(
            id_venta,
            numero(
                fila["saldo_pendiente"]
            ),
        )

        self.txt_importe_aplicar.delete(
            0,
            "end",
        )
        self.txt_importe_aplicar.insert(
            0,
            formato_decimal(
                importe,
                decimales=2,
            ),
        )

    def _cambiar_modo_aplicacion(self) -> None:
        estado = (
            "disabled"
            if self.aplicacion_automatica.get()
            else "normal"
        )

        self.txt_importe_aplicar.configure(
            state=estado
        )
        self.btn_aplicar_importe.configure(
            state=estado
        )
        self.btn_aplicar_saldo.configure(
            state=estado
        )
        self.btn_vaciar_aplicaciones.configure(
            state=estado
        )

        self._recargar_ventas()
        self._actualizar_resumen()

    def _aplicar_importe_venta(self) -> None:
        seleccion = (
            self.grilla_ventas.selection()
        )

        if not seleccion:
            messagebox.showinfo(
                "Cobros",
                "Seleccione una venta.",
                parent=self,
            )
            return

        fila = self._ventas[
            seleccion[0]
        ]

        try:
            importe = convertir_decimal(
                self.txt_importe_aplicar.get(),
                decimales=2,
            )

        except Exception as error:
            messagebox.showwarning(
                "Cobros",
                f"Importe inválido.\n\n{error}",
                parent=self,
            )
            return

        saldo = numero(
            fila["saldo_pendiente"]
        )

        if importe < 0:
            messagebox.showwarning(
                "Cobros",
                "El importe no puede ser negativo.",
                parent=self,
            )
            return

        if importe > saldo:
            messagebox.showwarning(
                "Cobros",
                "El importe supera el saldo "
                "de la venta.",
                parent=self,
            )
            return

        id_venta = int(
            fila["id_venta"]
        )

        if importe == 0:
            self._aplicaciones.pop(
                id_venta,
                None,
            )
        else:
            self._aplicaciones[
                id_venta
            ] = importe

        self._recargar_ventas()
        self._actualizar_resumen()

    def _aplicar_saldo_completo(self) -> None:
        seleccion = (
            self.grilla_ventas.selection()
        )

        if not seleccion:
            messagebox.showinfo(
                "Cobros",
                "Seleccione una venta.",
                parent=self,
            )
            return

        fila = self._ventas[
            seleccion[0]
        ]

        self._aplicaciones[
            int(fila["id_venta"])
        ] = numero(
            fila["saldo_pendiente"]
        )

        self._recargar_ventas()
        self._actualizar_resumen()

    def _vaciar_aplicaciones(self) -> None:
        self._aplicaciones.clear()
        self._recargar_ventas()
        self._actualizar_resumen()

    def _agregar_medio(self) -> None:
        texto_medio = self.cbo_medio.get()

        if texto_medio not in self._catalogo_medios:
            messagebox.showwarning(
                "Cobros",
                "Seleccione un medio de pago.",
                parent=self,
            )
            return

        medio = self._catalogo_medios[
            texto_medio
        ]

        try:
            texto_importe = (
                self.txt_importe_medio
                .get()
                .strip()
            )

            if texto_importe:
                importe = convertir_decimal(
                    texto_importe,
                    decimales=2,
                )
            else:
                importe_declarado = (
                    self._importe_cobro_declarado()
                )

                importe = (
                    importe_declarado
                    - self._total_medios()
                )

            if importe <= 0:
                raise ValueError(
                    "El importe debe ser mayor que cero."
                )

        except Exception as error:
            messagebox.showwarning(
                "Cobros",
                f"Importe inválido.\n\n{error}",
                parent=self,
            )
            return

        referencia = (
            self.txt_referencia.get().strip()
            or None
        )

        if (
            bool(medio["requiere_referencia"])
            and not referencia
        ):
            messagebox.showwarning(
                "Cobros",
                "Este medio de pago requiere "
                "una referencia.",
                parent=self,
            )
            return

        self._contador_medios += 1

        iid = (
            f"medio-{self._contador_medios}"
        )

        self._medios_cobro[iid] = {
            "id_medio_pago":
                int(medio["id_medio_pago"]),

            "descripcion":
                medio["descripcion"],

            "importe":
                importe,

            "referencia":
                referencia,
        }

        self.txt_importe_medio.delete(
            0,
            "end",
        )
        self.txt_referencia.delete(
            0,
            "end",
        )

        self._recargar_medios()
        self._actualizar_resumen()

    def _quitar_medio(self) -> None:
        seleccion = (
            self.grilla_medios.selection()
        )

        if not seleccion:
            return

        self._medios_cobro.pop(
            seleccion[0],
            None,
        )

        self._recargar_medios()
        self._actualizar_resumen()

    def _recargar_medios(self) -> None:
        for item in self.grilla_medios.get_children():
            self.grilla_medios.delete(item)

        for iid, medio in self._medios_cobro.items():
            self.grilla_medios.insert(
                "",
                "end",
                iid=iid,
                values=(
                    medio["descripcion"],
                    "$"
                    + formato_decimal(
                        numero(medio["importe"]),
                        decimales=2,
                    ),
                    medio["referencia"] or "",
                ),
            )

        self._sincronizar_importe_con_medios()

    def _total_medios(self) -> Decimal:
        return sum(
            (
                numero(medio["importe"])
                for medio
                in self._medios_cobro.values()
            ),
            Decimal("0"),
        )

    def _total_aplicado_manual(self) -> Decimal:
        return sum(
            self._aplicaciones.values(),
            Decimal("0"),
        )

    def _actualizar_resumen(self) -> None:
        try:
            importe_declarado = (
                self._importe_cobro_declarado()
            )
        except Exception:
            importe_declarado = Decimal("0")

        total_medios = self._total_medios()
        diferencia = importe_declarado - total_medios

        if self.aplicacion_automatica.get():
            detalle_aplicacion = (
                "Aplicación automática FIFO"
            )
        else:
            aplicado = (
                self._total_aplicado_manual()
            )

            detalle_aplicacion = (
                f"Aplicado: "
                f"${formato_decimal(aplicado, decimales=2)}"
            )

        self.texto_resumen.set(
            f"Importe declarado: "
            f"${formato_decimal(importe_declarado, decimales=2)} · "
            f"Medios cargados: "
            f"${formato_decimal(total_medios, decimales=2)} · "
            f"Diferencia: "
            f"${formato_decimal(diferencia, decimales=2)} · "
            f"{detalle_aplicacion}"
        )

        self._actualizar_estado_boton_confirmar()

    def _confirmar_cobro(self) -> None:
        if not self._cliente_seleccionado:
            return

        if not self._caja:
            return

        if not self._medios_cobro:
            messagebox.showwarning(
                "Cobros",
                "Debe agregar al menos "
                "un medio de pago.",
                parent=self,
            )
            return

      
        try:
            importe_declarado = (
                self._importe_cobro_declarado()
            )

        except ErrorCobro as error:
            messagebox.showwarning(
                "Cobros",
                str(error),
                parent=self,
            )
            return

        except Exception as error:
            messagebox.showerror(
                "Cobros",
                "No se pudo registrar el cobro."
                f"\n\n{error}",
                parent=self,
            )
            return

        if importe_declarado <= 0:
            messagebox.showwarning(
                "Cobros",
                "Indique cuánto paga el cliente.",
                parent=self,
            )
            return

        total_medios = self._total_medios()

        if total_medios != importe_declarado:
            diferencia = (
                importe_declarado
                - total_medios
            )

            messagebox.showwarning(
                "Cobros",
                "La suma de los medios de pago no coincide "
                "con el importe entregado.\n\n"
                f"Importe entregado: "
                f"${formato_decimal(importe_declarado, decimales=2)}\n"
                f"Medios cargados: "
                f"${formato_decimal(total_medios, decimales=2)}\n"
                f"Diferencia: "
                f"${formato_decimal(diferencia, decimales=2)}",
                parent=self,
            )
            return

        aplicaciones: list[
            dict[str, Any]
        ] = []

        if not self.aplicacion_automatica.get():
            total_aplicado = (
                self._total_aplicado_manual()
            )

            if total_aplicado > total_medios:
                messagebox.showwarning(
                    "Cobros",
                    "El importe aplicado a ventas "
                    "supera el total cobrado.",
                    parent=self,
                )
                return

            aplicaciones = [
                {
                    "id_venta": id_venta,
                    "importe": importe,
                }
                for id_venta, importe
                in self._aplicaciones.items()
                if importe > 0
            ]

        cliente = (
            self._cliente_seleccionado[
                "nombre"
            ]
        )

        modo = (
            "Automático FIFO"
            if self.aplicacion_automatica.get()
            else "Manual"
        )

        confirmar = messagebox.askyesno(
            "Confirmar cobro",
            f"Cliente: {cliente}\n"
            f"Total: "
            f"${formato_decimal(total_medios, decimales=2)}\n"
            f"Aplicación: {modo}"
            "\n\n¿Registrar el cobro?",
            parent=self,
        )

        if not confirmar:
            return

        try:
            resultado = registrar_cobro(
                id_cliente=int(
                    self._cliente_seleccionado[
                        "id_cliente"
                    ]
                ),
                id_caja_sesion=int(
                    self._caja[
                        "id_caja_sesion"
                    ]
                ),
                medios_pago=list(
                    self._medios_cobro.values()
                ),
                aplicaciones=aplicaciones,
                aplicar_automaticamente=(
                    self.aplicacion_automatica.get()
                ),
                observaciones=(
                    self.txt_observaciones
                    .get()
                    .strip()
                    or None
                ),
            )

        except Exception as error:
            messagebox.showerror(
                "Cobros",
                "No se pudo registrar el cobro."
                f"\n\n{error}",
                parent=self,
            )
            return

        messagebox.showinfo(
            "Cobro registrado",
            f"Cobro: {resultado['id_cobro']}\n"
            f"Importe: "
            f"${formato_decimal(numero(resultado['importe_total']), decimales=2)}\n"
            f"Aplicado: "
            f"${formato_decimal(numero(resultado['importe_aplicado']), decimales=2)}\n"
            f"Sin aplicar: "
            f"${formato_decimal(numero(resultado['importe_no_aplicado']), decimales=2)}\n"
            f"Saldo del cliente: "
            f"${formato_decimal(numero(resultado['saldo_cliente']), decimales=2)}\n"
            f"Estado: "
            f"{resultado['estado_cuenta']}",
            parent=self,
        )

        id_cliente = int(
            self._cliente_seleccionado[
                "id_cliente"
            ]
        )

        self._actualizar_clientes(
            conservar_id=id_cliente
        )

    def _limpiar_cliente(self) -> None:
        self._cliente_seleccionado = None
        self._ventas.clear()
        self._aplicaciones.clear()
        self._medios_cobro.clear()

        self.txt_importe_aplicar.delete(
            0,
            "end",
        )
        self.txt_importe_medio.delete(
            0,
            "end",
        )
        self.txt_referencia.delete(
            0,
            "end",
        )
        self.txt_observaciones.delete(
            0,
            "end",
        )

        for item in self.grilla_ventas.get_children():
            self.grilla_ventas.delete(item)

        self._recargar_medios()
        self._actualizar_resumen()

        self.btn_confirmar.configure(
            state="disabled"
        )
        self.btn_estado_cuenta.configure(
            state="disabled"
        )

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
    def _sincronizar_importe_con_medios(
        self,
    ) -> None:
        total_medios = self._total_medios()

        self.txt_importe_cobro.delete(
            0,
            "end",
        )

        self.txt_importe_cobro.insert(
            0,
            formato_decimal(
                total_medios,
                decimales=2,
            ),
        )
    def _actualizar_estado_boton_confirmar(
        self,
    ) -> None:
        if not hasattr(self, "btn_confirmar"):
            return

        try:
            importe_declarado = (
                self._importe_cobro_declarado()
            )
        except Exception:
            importe_declarado = Decimal("0")

        total_medios = self._total_medios()

        habilitado = (
            self._cliente_seleccionado is not None
            and self._caja is not None
            and bool(self._medios_cobro)
            and importe_declarado > 0
            and total_medios > 0
            and importe_declarado == total_medios
        )

        self.btn_confirmar.configure(
            state=(
                "normal"
                if habilitado
                else "disabled"
            )
        )
    def _abrir_estado_cuenta(self) -> None:
        if not self._cliente_seleccionado:
            messagebox.showinfo(
                "Estado de cuenta",
                "Seleccione un cliente.",
                parent=self,
            )
            return

        VentanaEstadoCuenta(
            self,
            self._cliente_seleccionado,
        )
    def aplicar_contexto(
        self,
        *,
        id_cliente: int | None = None,
        id_venta: int | None = None,
        **_contexto,
    ) -> None:
        self._id_venta_contexto = id_venta

        if id_cliente is not None:
            self._actualizar_clientes(
                conservar_id=id_cliente
        )
    def _seleccionar_venta_por_id(
        self,
        id_venta: int,
    ) -> None:
        for iid, fila in self._ventas.items():
            if int(fila["id_venta"]) != id_venta:
                continue

            self.grilla_ventas.selection_set(
                iid
            )
            self.grilla_ventas.focus(
                iid
            )
            self.grilla_ventas.see(
                iid
            )

            self._seleccionar_venta()
            return