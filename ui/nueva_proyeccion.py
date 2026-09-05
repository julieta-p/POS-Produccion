from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from tkinter import messagebox, ttk
from typing import Callable

from tkcalendar import DateEntry

from db.pedido_repository import (
    listar_clientes,
    listar_modalidades,
    listar_productos,
)

from db.proyeccion_repository import (
    crear_pedido_recurrente,
)

from ui.pedido import (
    ComboPredictivo,
    ControlHora,
    convertir_cantidad,
    formato_cantidad,
)

from ui.ventana_util import maximizar_ventana


@dataclass
class DetalleProyeccion:
    id_producto: int
    descripcion: str
    cantidad_sugerida: Decimal
    observaciones: str | None


class VentanaNuevaProyeccion(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        al_guardar: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)

        self._al_guardar = al_guardar

        self._clientes_por_texto: dict[str, int] = {}
        self._clientes_datos_por_texto: dict[str, dict] = {}
        self._productos_por_texto: dict[str, dict] = {}

        self._detalle: dict[
            int,
            DetalleProyeccion,
        ] = {}

        self.title("Nueva proyección de pedidos")
        self.resizable(True, True)

        maximizar_ventana(self)

        self._crear_interfaz()
        self._cargar_catalogos()
        self._inicializar()

        self.grab_set()


    # =========================================================
    # INTERFAZ
    # =========================================================

    def _crear_interfaz(self) -> None:
        contenedor = ttk.Frame(
            self,
            padding=(12, 8),
        )
        contenedor.pack(
            fill="both",
            expand=True,
        )

        contenedor.columnconfigure(0, weight=1)
        contenedor.rowconfigure(4, weight=1)

        ttk.Label(
            contenedor,
            text="Nueva proyección de pedidos",
            font=("Segoe UI", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 8),
        )

        ttk.Label(
            contenedor,
            text=(
                "Defina qué suele necesitar el cliente. "
                "Las cantidades podrán revisarse antes de "
                "generar cada pedido real."
            ),
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(0, 10),
        )

        self._crear_cabecera(contenedor)
        self._crear_recurrencia(contenedor)
        self._crear_productos(contenedor)
        self._crear_detalle(contenedor)
        self._crear_pie(contenedor)


    def _crear_cabecera(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Datos habituales",
            padding=10,
        )
        marco.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        marco.columnconfigure(0, weight=1)

        fila_cliente = ttk.Frame(marco)
        fila_cliente.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        fila_cliente.columnconfigure(0, weight=1)

        ttk.Label(
            fila_cliente,
            text="Cliente",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.cbo_cliente = ComboPredictivo(
            fila_cliente,
        )
        self.cbo_cliente.grid(
            row=1,
            column=0,
            padx=(0, 10),
            sticky="ew",
        )

        self.cbo_cliente.bind(
            "<<ComboboxSelected>>",
            self._actualizar_direccion_cliente,
        )

        ttk.Label(
            fila_cliente,
            text="Modalidad habitual",
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )

        self.cbo_modalidad = ttk.Combobox(
            fila_cliente,
            state="readonly",
            width=15,
        )
        self.cbo_modalidad.grid(
            row=1,
            column=1,
            sticky="w",
        )

        fila_entrega = ttk.Frame(marco)
        fila_entrega.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(8, 0),
        )

        fila_entrega.columnconfigure(
            0,
            weight=1,
        )

        ttk.Label(
            fila_entrega,
            text="Dirección habitual",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.txt_direccion = ttk.Entry(
            fila_entrega,
        )
        self.txt_direccion.grid(
            row=1,
            column=0,
            padx=(0, 10),
            sticky="ew",
        )

        ttk.Label(
            fila_entrega,
            text="Hora habitual",
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )

        self.hora_entrega = ControlHora(
            fila_entrega,
            hora_inicial=12,
            minuto_inicial=0,
            permitir_vacio=True,
        )
        self.hora_entrega.grid(
            row=1,
            column=1,
            sticky="w",
        )


    def _crear_recurrencia(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Repetición",
            padding=10,
        )
        marco.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        ttk.Label(
            marco,
            text="Desde",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.fecha_desde = DateEntry(
            marco,
            date_pattern="dd/mm/yyyy",
            locale="es_AR",
            firstweekday="monday",
            width=12,
        )
        self.fecha_desde.grid(
            row=1,
            column=0,
            padx=(0, 12),
            sticky="w",
        )

        ttk.Label(
            marco,
            text="Semanas",
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )

        self.var_semanas = tk.StringVar(
            value="4"
        )

        self.spn_semanas = ttk.Spinbox(
            marco,
            from_=1,
            to=52,
            width=6,
            justify="center",
            textvariable=self.var_semanas,
        )
        self.spn_semanas.grid(
            row=1,
            column=1,
            padx=(0, 18),
            sticky="w",
        )

        ttk.Label(
            marco,
            text="Repetir los días",
        ).grid(
            row=0,
            column=2,
            columnspan=7,
            sticky="w",
        )

        self._dias: dict[int, tk.BooleanVar] = {}

        nombres = (
            (1, "Lunes"),
            (2, "Martes"),
            (3, "Miércoles"),
            (4, "Jueves"),
            (5, "Viernes"),
            (6, "Sábado"),
            (7, "Domingo"),
        )

        for indice, (
            numero,
            nombre,
        ) in enumerate(nombres):
            variable = tk.BooleanVar(
                value=False
            )

            self._dias[numero] = variable

            ttk.Checkbutton(
                marco,
                text=nombre,
                variable=variable,
            ).grid(
                row=1,
                column=indice + 2,
                padx=(0, 10),
                sticky="w",
            )


    def _crear_productos(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Agregar producto proyectado",
            padding=10,
        )
        marco.grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        marco.columnconfigure(
            0,
            weight=1,
        )

        ttk.Label(
            marco,
            text="Producto",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.cbo_producto = ComboPredictivo(
            marco,
        )
        self.cbo_producto.grid(
            row=1,
            column=0,
            padx=(0, 8),
            sticky="ew",
        )

        ttk.Label(
            marco,
            text="Cantidad sugerida",
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )

        self.txt_cantidad = ttk.Entry(
            marco,
            width=14,
            justify="right",
        )
        self.txt_cantidad.grid(
            row=1,
            column=1,
            padx=(0, 8),
            sticky="w",
        )

        ttk.Label(
            marco,
            text="Observación",
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )

        self.txt_observacion_producto = ttk.Entry(
            marco,
            width=35,
        )
        self.txt_observacion_producto.grid(
            row=1,
            column=2,
            padx=(0, 8),
            sticky="ew",
        )

        ttk.Button(
            marco,
            text="Agregar producto",
            command=self._agregar_producto,
        ).grid(
            row=1,
            column=3,
            sticky="ew",
        )


    def _crear_detalle(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Productos proyectados",
            padding=8,
        )
        marco.grid(
            row=5,
            column=0,
            sticky="nsew",
            pady=(0, 8),
        )

        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(0, weight=1)

        columnas = (
            "producto",
            "cantidad",
            "observaciones",
        )

        self.grilla = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
            height=7,
        )

        self.grilla.heading(
            "producto",
            text="Producto",
        )

        self.grilla.heading(
            "cantidad",
            text="Cantidad sugerida",
        )

        self.grilla.heading(
            "observaciones",
            text="Observaciones",
        )

        self.grilla.column(
            "producto",
            width=400,
            anchor="w",
        )

        self.grilla.column(
            "cantidad",
            width=150,
            anchor="center",
        )

        self.grilla.column(
            "observaciones",
            width=400,
            anchor="w",
        )

        barra = ttk.Scrollbar(
            marco,
            orient="vertical",
            command=self.grilla.yview,
        )

        self.grilla.configure(
            yscrollcommand=barra.set,
        )

        self.grilla.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        barra.grid(
            row=0,
            column=1,
            sticky="ns",
        )


    def _crear_pie(
        self,
        parent: ttk.Frame,
    ) -> None:
        pie = ttk.Frame(parent)
        pie.grid(
            row=6,
            column=0,
            sticky="ew",
        )

        pie.columnconfigure(
            1,
            weight=1,
        )

        ttk.Button(
            pie,
            text="Quitar producto",
            command=self._quitar_producto,
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        ttk.Label(
            pie,
            text="Observaciones generales",
        ).grid(
            row=0,
            column=1,
            padx=(20, 8),
            sticky="e",
        )

        self.txt_observaciones = ttk.Entry(
            pie,
            width=45,
        )
        self.txt_observaciones.grid(
            row=0,
            column=2,
            padx=(0, 12),
            sticky="ew",
        )

        ttk.Button(
            pie,
            text="Crear proyección",
            command=self._guardar,
        ).grid(
            row=0,
            column=3,
            padx=(0, 8),
        )

        ttk.Button(
            pie,
            text="Cancelar",
            command=self.destroy,
        ).grid(
            row=0,
            column=4,
        )


    # =========================================================
    # CATÁLOGOS
    # =========================================================

    def _cargar_catalogos(self) -> None:
        try:
            clientes = listar_clientes()
            modalidades = listar_modalidades()
            productos = listar_productos()

        except Exception as error:
            messagebox.showerror(
                "Nueva proyección",
                "No se pudieron cargar los catálogos."
                f"\n\n{error}",
                parent=self,
            )
            self.destroy()
            return

        textos_clientes: list[str] = []

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

            self._clientes_datos_por_texto[
                texto
            ] = cliente

        self.cbo_cliente.establecer_valores(
            textos_clientes
        )

        self.cbo_modalidad.configure(
            values=modalidades
        )

        textos_productos: list[str] = []

        for producto in productos:
            texto = (
                f"{producto['id_producto']} - "
                f"{producto['descripcion']}"
            )

            textos_productos.append(texto)

            self._productos_por_texto[
                texto
            ] = producto

        self.cbo_producto.establecer_valores(
            textos_productos
        )


    def _inicializar(self) -> None:
        self.fecha_desde.set_date(
            date.today()
        )

        modalidades = (
            self.cbo_modalidad.cget(
                "values"
            )
        )

        if modalidades:
            self.cbo_modalidad.set(
                modalidades[0]
            )

        self.cbo_cliente.focus_set()


    # =========================================================
    # CLIENTE
    # =========================================================

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


    # =========================================================
    # PRODUCTOS
    # =========================================================

    def _agregar_producto(self) -> None:
        try:
            producto = (
                self._productos_por_texto.get(
                    self.cbo_producto.get()
                )
            )

            if not producto:
                raise ValueError(
                    "Debe seleccionar un producto."
                )

            cantidad = convertir_cantidad(
                self.txt_cantidad.get()
            )

            if cantidad <= 0:
                raise ValueError(
                    "La cantidad debe ser mayor que cero."
                )

            id_producto = int(
                producto["id_producto"]
            )

            existente = self._detalle.get(
                id_producto
            )

            if existente:
                cantidad += (
                    existente.cantidad_sugerida
                )

            detalle = DetalleProyeccion(
                id_producto=id_producto,
                descripcion=str(
                    producto["descripcion"]
                ),
                cantidad_sugerida=cantidad,
                observaciones=(
                    self.txt_observacion_producto
                    .get()
                    .strip()
                    or None
                ),
            )

            self._detalle[
                id_producto
            ] = detalle

            self._actualizar_grilla()
            self._limpiar_producto()

        except Exception as error:
            messagebox.showwarning(
                "Agregar producto",
                str(error),
                parent=self,
            )


    def _quitar_producto(self) -> None:
        seleccion = (
            self.grilla.selection()
        )

        if not seleccion:
            messagebox.showwarning(
                "Quitar producto",
                "Seleccione un producto.",
                parent=self,
            )
            return

        id_producto = int(
            seleccion[0]
        )

        self._detalle.pop(
            id_producto,
            None,
        )

        self._actualizar_grilla()


    def _actualizar_grilla(self) -> None:
        for item in self.grilla.get_children():
            self.grilla.delete(item)

        for detalle in self._detalle.values():
            self.grilla.insert(
                "",
                "end",
                iid=str(
                    detalle.id_producto
                ),
                values=(
                    detalle.descripcion,
                    formato_cantidad(
                        detalle.cantidad_sugerida
                    ),
                    detalle.observaciones or "",
                ),
            )


    def _limpiar_producto(self) -> None:
        self.cbo_producto.limpiar()

        self.txt_cantidad.delete(
            0,
            "end",
        )

        self.txt_observacion_producto.delete(
            0,
            "end",
        )

        self.cbo_producto.focus_set()


    # =========================================================
    # GUARDAR
    # =========================================================

    def _guardar(self) -> None:
        try:
            texto_cliente = (
                self.cbo_cliente.get()
            )

            if (
                texto_cliente
                not in self._clientes_por_texto
            ):
                raise ValueError(
                    "Debe seleccionar un cliente."
                )

            modalidad = (
                self.cbo_modalidad
                .get()
                .strip()
                .upper()
                or None
            )

            try:
                cantidad_semanas = int(
                    self.var_semanas.get()
                )
            except ValueError as error:
                raise ValueError(
                    "La cantidad de semanas no es válida."
                ) from error

            if not 1 <= cantidad_semanas <= 52:
                raise ValueError(
                    "La cantidad de semanas debe "
                    "estar entre 1 y 52."
                )

            dias = [
                numero
                for numero, variable
                in self._dias.items()
                if variable.get()
            ]

            if not dias:
                raise ValueError(
                    "Seleccione al menos un día."
                )

            if not self._detalle:
                raise ValueError(
                    "Debe agregar al menos un producto."
                )

            detalles = [
                {
                    "id_producto":
                        detalle.id_producto,

                    "cantidad_sugerida":
                        detalle.cantidad_sugerida,

                    "observaciones":
                        detalle.observaciones,
                }
                for detalle in self._detalle.values()
            ]

            resultado = crear_pedido_recurrente(
                id_cliente=
                    self._clientes_por_texto[
                        texto_cliente
                    ],

                modalidad_entrega=
                    modalidad,

                hora_entrega=
                    self.hora_entrega.obtener_hora(),

                direccion_entrega=(
                    self.txt_direccion
                    .get()
                    .strip()
                    or None
                ),

                fecha_desde=
                    self.fecha_desde.get_date(),

                cantidad_semanas=
                    cantidad_semanas,

                dias=dias,

                detalles=detalles,

                observaciones=(
                    self.txt_observaciones
                    .get()
                    .strip()
                    or None
                ),
            )

        except Exception as error:
            messagebox.showerror(
                "Nueva proyección",
                "No se pudo crear la proyección."
                f"\n\n{error}",
                parent=self,
            )
            return

        messagebox.showinfo(
            "Nueva proyección",
            (
                "Proyección creada correctamente."
                "\n\n"
                f"Proyección: "
                f"{resultado['id_pedido_recurrente']}\n"
                f"Semanas: "
                f"{resultado['cantidad_semanas']}\n"
                f"Días por semana: "
                f"{resultado['cantidad_dias']}\n"
                f"Ocurrencias generadas: "
                f"{resultado['cantidad_ocurrencias']}"
            ),
            parent=self,
        )

        if self._al_guardar:
            self._al_guardar()

        self.destroy()