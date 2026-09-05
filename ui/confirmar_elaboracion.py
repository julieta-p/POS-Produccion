from __future__ import annotations

import tkinter as tk
from datetime import date, timedelta
from decimal import Decimal
from tkinter import messagebox, ttk
from typing import Any
from ui.ventana_util import maximizar_ventana

from tkcalendar import DateEntry

from db.elaboracion_repository import (
    confirmar_elaboracion,
    listar_elaboraciones_pendientes,
)
from ui.pedido import (
    convertir_cantidad,
    formato_cantidad,
)
from ui.navegacion import crear_barra_navegacion

def numero(valor: Any) -> Decimal:
    if valor is None:
        return Decimal("0")

    return Decimal(str(valor))


def fecha_texto(valor: Any) -> str:
    if valor is None:
        return ""

    return valor.strftime("%d/%m/%Y")


class VentanaConfirmarElaboracion(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        navegador=None,
    ) -> None:
        super().__init__(parent)

        self.navegador = navegador

        self._filas: dict[
            str,
            dict[str, Any],
        ] = {}

        self._seleccion: (
            dict[str, Any] | None
        ) = None

        self._ancho_pantalla = (
            self.winfo_screenwidth()
        )

        self._alto_pantalla = (
            self.winfo_screenheight()
        )

        self._pantalla_compacta = (
            self._ancho_pantalla < 1050
            or self._alto_pantalla < 700
        )

        self.title("Confirmar elaboración")
        # self.transient(parent)
        self.resizable(True, True)

        # self._ajustar_tamano_inicial()
        maximizar_ventana(self)

        if self.navegador is not None:
            crear_barra_navegacion(
                ventana=self,
                navegador=self.navegador,
                modulo_actual="elaboracion",
            )

        self._crear_interfaz()

        self._seleccionar_semana_actual(
            actualizar=False
        )

        self._actualizar()
    def _ajustar_tamano_inicial(self) -> None:
        ancho = int(
            self._ancho_pantalla * 0.90
        )

        alto_disponible = max(
            self._alto_pantalla - 70,
            500,
        )

        alto = int(
            alto_disponible * 0.92
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
            760,
            ancho,
        )

        alto_minimo = min(
            500,
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

        # La grilla ocupa todo el espacio vertical sobrante.
        contenedor.rowconfigure(
            3,
            weight=1,
        )

        ttk.Label(
            contenedor,
            text="Confirmar elaboración",
            font=("Segoe UI", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 6),
        )

        ttk.Label(
            contenedor,
            text=(
                "Ingrese la cantidad realmente obtenida. "
                "Si supera lo planificado, el excedente "
                "quedará disponible en stock."
            ),
            justify="left",
            wraplength=(
                720
                if self._pantalla_compacta
                else 1000
            ),
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        self._crear_filtros(contenedor)
        self._crear_grilla(contenedor)
        self._crear_confirmacion(contenedor)

    def _crear_filtros(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Período",
            padding=10,
        )
        marco.grid(
            row=2,
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
        )
        self.fecha_desde.grid(
            row=1,
            column=0,
            padx=(0, 8),
            sticky="w",
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
        )
        self.fecha_hasta.grid(
            row=1,
            column=1,
            sticky="w",
        )

        self.fecha_desde.bind(
            "<<DateEntrySelected>>",
            self._sincronizar_fecha_hasta,
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
        )

    def _sincronizar_fecha_hasta(
        self,
        _evento=None,
    ) -> None:
        self.fecha_hasta.set_date(
            self.fecha_desde.get_date()
        )
        
    def _crear_grilla(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Elaboraciones pendientes",
            padding=8,
        )
        marco.grid(
            row=3,
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
            "fecha",
            "producto",
            "planificado",
            "producido",
            "pendiente",
        )

        self.grilla = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
            height=10,
        )

        titulos = {
            "fecha": "Fecha",
            "producto": "Producto",
            "planificado": "Planificado",
            "producido": "Ya producido",
            "pendiente": "Pendiente",
        }

        for columna, titulo in titulos.items():
            self.grilla.heading(
                columna,
                text=titulo,
            )

        self.grilla.column(
            "fecha",
            width=105,
            minwidth=85,
            anchor="center",
            stretch=False,
        )

        self.grilla.column(
            "producto",
            width=380,
            minwidth=180,
            anchor="w",
            stretch=True,
        )

        for columna in (
            "planificado",
            "producido",
            "pendiente",
        ):
            self.grilla.column(
                columna,
                width=120,
                minwidth=90,
                anchor="e",
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
            self._seleccionar,
        )
    def _crear_confirmacion(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Resultado real",
            padding=10,
        )
        marco.grid(
            row=4,
            column=0,
            sticky="ew",
        )

        marco.columnconfigure(
            0,
            weight=1,
        )

        marco.columnconfigure(
            1,
            weight=4,
        )

        ttk.Label(
            marco,
            text="Cantidad obtenida",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        ttk.Label(
            marco,
            text="Observaciones",
        ).grid(
            row=0,
            column=1,
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

        self.txt_observaciones = ttk.Entry(
            marco,
        )
        self.txt_observaciones.grid(
            row=1,
            column=1,
            sticky="ew",
        )

        acciones = ttk.Frame(marco)
        acciones.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="e",
            pady=(8, 0),
        )

        self.btn_confirmar = ttk.Button(
            acciones,
            text="Confirmar elaboración",
            command=self._confirmar,
            state="disabled",
        )
        self.btn_confirmar.pack(
            side="right",
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
            self._actualizar()

    def _actualizar(self) -> None:
        fecha_desde = self.fecha_desde.get_date()
        fecha_hasta = self.fecha_hasta.get_date()

        if fecha_desde > fecha_hasta:
            messagebox.showwarning(
                "Confirmar elaboración",
                "La fecha desde no puede ser posterior "
                "a la fecha hasta.",
                parent=self,
            )
            return

        try:
            filas = listar_elaboraciones_pendientes(
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
            )

        except Exception as error:
            messagebox.showerror(
                "Confirmar elaboración",
                "No se pudieron recuperar "
                "las elaboraciones."
                f"\n\n{error}",
                parent=self,
            )
            return

        self._filas.clear()

        for item in self.grilla.get_children():
            self.grilla.delete(item)

        for indice, fila in enumerate(filas):
            iid = (
                f"{fila['fecha_elaboracion']}"
                f"-{fila['id_producto']}"
                f"-{indice}"
            )

            self._filas[iid] = fila

            self.grilla.insert(
                "",
                "end",
                iid=iid,
                values=(
                    fecha_texto(
                        fila["fecha_elaboracion"]
                    ),
                    fila["descripcion_producto"],
                    formato_cantidad(
                        fila["cantidad_planificada"]
                    ),
                    formato_cantidad(
                        fila["cantidad_producida"]
                    ),
                    formato_cantidad(
                        fila["cantidad_pendiente"]
                    ),
                ),
            )

        self._limpiar_seleccion()

    def _seleccionar(
        self,
        _evento=None,
    ) -> None:
        seleccion = self.grilla.selection()

        if not seleccion:
            self._limpiar_seleccion()
            return

        self._seleccion = self._filas[
            seleccion[0]
        ]

        self.txt_cantidad.delete(0, "end")

        self.txt_observaciones.delete(
            0,
            "end",
        )

        self.btn_confirmar.configure(
            state="normal"
        )

    def _confirmar(self) -> None:
        if not self._seleccion:
            return

        try:
            cantidad = convertir_cantidad(
                self.txt_cantidad.get()
            )

            if cantidad <= 0:
                raise ValueError(
                    "La cantidad debe ser mayor que cero."
                )

        except Exception as error:
            messagebox.showwarning(
                "Confirmar elaboración",
                f"Cantidad inválida.\n\n{error}",
                parent=self,
            )
            return

        pendiente = numero(
            self._seleccion[
                "cantidad_pendiente"
            ]
        )

        diferencia = cantidad - pendiente

        mensaje = (
            f"Producto: "
            f"{self._seleccion['descripcion_producto']}\n"
            f"Planificado pendiente: "
            f"{formato_cantidad(pendiente)}\n"
            f"Cantidad obtenida: "
            f"{formato_cantidad(cantidad)}"
        )

        if diferencia > 0:
            mensaje += (
                "\n"
                f"Excedente estimado: "
                f"{formato_cantidad(diferencia)}"
            )

        mensaje += "\n\n¿Confirmar la elaboración?"

        if not messagebox.askyesno(
            "Confirmar elaboración",
            mensaje,
            parent=self,
        ):
            return

        try:
            resultado = confirmar_elaboracion(
                fecha_elaboracion=(
                    self._seleccion[
                        "fecha_elaboracion"
                    ]
                ),
                id_producto=int(
                    self._seleccion[
                        "id_producto"
                    ]
                ),
                cantidad_obtenida=cantidad,
                observaciones=(
                    self.txt_observaciones
                    .get()
                    .strip()
                    or None
                ),
            )

        except Exception as error:
            messagebox.showerror(
                "Confirmar elaboración",
                "No se pudo confirmar "
                "la elaboración."
                f"\n\n{error}",
                parent=self,
            )
            return

        messagebox.showinfo(
            "Elaboración confirmada",
            f"Elaboración: "
            f"{resultado['id_elaboracion']}\n"
            f"Cantidad obtenida: "
            f"{formato_cantidad(resultado['cantidad_obtenida'])}\n"
            f"Aplicada a pedidos: "
            f"{formato_cantidad(resultado['cantidad_aplicada_plan'])}\n"
            f"Excedente libre: "
            f"{formato_cantidad(resultado['cantidad_excedente'])}",
            parent=self,
        )

        self._actualizar()

    def _limpiar_seleccion(self) -> None:
        self._seleccion = None

        self.txt_cantidad.delete(0, "end")
        self.txt_observaciones.delete(
            0,
            "end",
        )

        self.btn_confirmar.configure(
            state="disabled"
        )

    