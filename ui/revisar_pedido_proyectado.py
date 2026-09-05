from __future__ import annotations

import tkinter as tk

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from tkinter import messagebox, ttk
from typing import Any, Callable

from tkcalendar import DateEntry

from db.pedido_repository import (
    listar_modalidades,
    listar_productos,
)

from db.proyeccion_repository import (
    generar_pedido_desde_proyeccion,
)

from ui.pedido import (
    ComboPredictivo,
    ControlHora,
    convertir_cantidad,
    convertir_decimal,
    formato_cantidad,
    formato_decimal,
    formato_moneda,
)

from ui.ventana_util import maximizar_ventana


@dataclass
class DetalleRevision:
    id_producto: int
    descripcion: str
    cantidad: Decimal
    tipo_precio: str
    precio_unitario: Decimal
    descuento: Decimal
    observaciones: str | None

    @property
    def subtotal(self) -> Decimal:
        valor = (
            self.cantidad
            * self.precio_unitario
            - self.descuento
        )

        return max(
            valor,
            Decimal("0"),
        )


class VentanaRevisarPedidoProyectado(
    tk.Toplevel
):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        cabecera: dict[str, Any],
        detalles: list[dict[str, Any]],
        al_guardar: (
            Callable[[int], None]
            | None
        ) = None,
    ) -> None:
        super().__init__(parent)

        self._cabecera = dict(cabecera)
        self._detalles_proyectados = [
            dict(item)
            for item in detalles
        ]

        self._al_guardar = al_guardar

        self._productos_por_texto: dict[
            str,
            dict[str, Any],
        ] = {}

        self._productos_por_id: dict[
            int,
            dict[str, Any],
        ] = {}

        self._texto_producto_por_id: dict[
            int,
            str,
        ] = {}

        self._detalle: dict[
            int,
            DetalleRevision,
        ] = {}

        self.title(
            "Revisar pedido proyectado"
        )

        self.resizable(
            True,
            True,
        )

        maximizar_ventana(self)

        self._crear_interfaz()

        if not self._cargar_catalogos():
            return

        self._cargar_proyeccion()

        self.grab_set()


    # =========================================================
    # INTERFAZ
    # =========================================================

    def _crear_interfaz(
        self,
    ) -> None:

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
            4,
            weight=1,
        )


        ttk.Label(
            contenedor,
            text="Revisar pedido proyectado",
            font=(
                "Segoe UI",
                18,
                "bold",
            ),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 4),
        )


        ttk.Label(
            contenedor,
            text=(
                "Confirme los datos con el cliente. "
                "Puede modificar cantidades, agregar o "
                "quitar productos antes de generar "
                "el pedido real."
            ),
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(0, 10),
        )


        self._crear_cabecera(
            contenedor
        )

        self._crear_carga_producto(
            contenedor
        )

        self._crear_detalle(
            contenedor
        )

        self._crear_pie(
            contenedor
        )


    # =========================================================
    # CABECERA
    # =========================================================

    def _crear_cabecera(
        self,
        parent: ttk.Frame,
    ) -> None:

        marco = ttk.LabelFrame(
            parent,
            text="Pedido confirmado",
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


        # -----------------------------------------------------
        # Cliente 
        # -----------------------------------------------------

        fila_cliente = ttk.Frame(marco)

        fila_cliente.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        ttk.Label(
            fila_cliente,
            text="Cliente",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.lbl_cliente = ttk.Label(
            fila_cliente,
            text="",
            font=("Segoe UI", 11, "bold"),
        )

        self.lbl_cliente.grid(
            row=1,
            column=0,
            sticky="w",
        )

        # -----------------------------------------------------
        # Fechas + hora + Modalidad
        # -----------------------------------------------------

        fila_fechas = ttk.Frame(
            marco
        )

        fila_fechas.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(8, 0),
        )


        ttk.Label(
            fila_fechas,
            text="Fecha de entrega",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )


        self.txt_fecha_entrega = (
            DateEntry(
                fila_fechas,
                date_pattern="dd/mm/yyyy",
                locale="es_AR",
                firstweekday="monday",
                width=12,
            )
        )

        self.txt_fecha_entrega.grid(
            row=1,
            column=0,
            padx=(0, 10),
            sticky="w",
        )

        self.txt_fecha_entrega.bind(
            "<<DateEntrySelected>>",
            self._sugerir_fecha_elaboracion,
        )


        ttk.Label(
            fila_fechas,
            text="Hora de entrega",
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )


        self.hora_entrega = ControlHora(
            fila_fechas,
            hora_inicial=12,
            minuto_inicial=0,
            permitir_vacio=True,
        )

        self.hora_entrega.grid(
            row=1,
            column=1,
            padx=(0, 10),
            sticky="w",
        )


        ttk.Label(
            fila_fechas,
            text="Fecha de elaboración",
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )


        self.txt_fecha_elaboracion = (
            DateEntry(
                fila_fechas,
                date_pattern="dd/mm/yyyy",
                locale="es_AR",
                firstweekday="monday",
                width=12,
            )
        )

        self.txt_fecha_elaboracion.grid(
            row=1,
            column=2,
            sticky="w",
        )

        ttk.Label(
            fila_fechas,
            text="Modalidad",
        ).grid(
            row=0,
            column=3,
            padx=(10, 0),
            sticky="w",
        )

        self.cbo_modalidad = ttk.Combobox(
            fila_fechas,
            state="readonly",
            width=15,
        )

        self.cbo_modalidad.grid(
            row=1,
            column=3,
            padx=(10, 0),
            sticky="w",
        )

        self.cbo_modalidad.bind(
            "<<ComboboxSelected>>",
            self._sugerir_fecha_elaboracion,
        )


        # -----------------------------------------------------
        # Entrega
        # -----------------------------------------------------

        fila_entrega = ttk.Frame(
            marco
        )

        fila_entrega.grid(
            row=2,
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
            text="Dirección de entrega",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )


        self.txt_direccion = ttk.Entry(
            fila_entrega
        )

        self.txt_direccion.grid(
            row=1,
            column=0,
            padx=(0, 10),
            sticky="ew",
        )


        self.requiere_confirmacion = (
            tk.BooleanVar(
                value=False
            )
        )


        ttk.Checkbutton(
            fila_entrega,
            text="Requiere confirmación",
            variable=self.requiere_confirmacion,
        ).grid(
            row=1,
            column=1,
            padx=(12,0),
            sticky="w",
        )

        ttk.Label(
            marco,
            text="Observaciones del pedido",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            pady=(8, 0),
        )


        self.txt_observaciones = ttk.Entry(
            marco
        )

        self.txt_observaciones.grid(
            row=4,
            column=0,
            sticky="ew",
        )


    # =========================================================
    # CARGA PRODUCTO
    # =========================================================

    def _crear_carga_producto(
        self,
        parent: ttk.Frame,
    ) -> None:

        marco = ttk.LabelFrame(
            parent,
            text="Agregar o modificar producto",
            padding=10,
        )

        marco.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        marco.columnconfigure(
            0,
            weight=1,
        )


        # -----------------------------------------------------
        # Producto + cantidad + tipo
        # -----------------------------------------------------

        fila_producto = ttk.Frame(
            marco
        )

        fila_producto.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        fila_producto.columnconfigure(
            0,
            weight=1,
        )


        ttk.Label(
            fila_producto,
            text="Producto",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )


        self.cbo_producto = ComboPredictivo(
            fila_producto,
        )

        self.cbo_producto.grid(
            row=1,
            column=0,
            padx=(0, 8),
            sticky="ew",
        )

        self.cbo_producto.bind(
            "<<ComboboxSelected>>",
            self._actualizar_precio,
        )


        ttk.Label(
            fila_producto,
            text="Cantidad",
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )


        self.txt_cantidad = ttk.Entry(
            fila_producto,
            justify="right",
            width=12,
        )

        self.txt_cantidad.grid(
            row=1,
            column=1,
            padx=(0, 8),
            sticky="w",
        )


        ttk.Label(
            fila_producto,
            text="Tipo de precio",
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )


        self.cbo_tipo_precio = ttk.Combobox(
            fila_producto,
            state="readonly",
            width=14,
            values=(
                "MENOR",
                "MAYOR",
                "ESPECIAL",
            ),
        )

        self.cbo_tipo_precio.grid(
            row=1,
            column=2,
            sticky="w",
        )

        self.cbo_tipo_precio.bind(
            "<<ComboboxSelected>>",
            self._actualizar_precio,
        )


        # -----------------------------------------------------
        # Precio + descuento + observación
        # -----------------------------------------------------

        fila_importes = ttk.Frame(
            marco
        )

        fila_importes.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(8, 0),
        )

        fila_importes.columnconfigure(
            2,
            weight=1,
        )


        ttk.Label(
            fila_importes,
            text="Precio unitario",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )


        self.txt_precio = ttk.Entry(
            fila_importes,
            justify="right",
            width=14,
        )

        self.txt_precio.grid(
            row=1,
            column=0,
            padx=(0, 8),
            sticky="w",
        )


        ttk.Label(
            fila_importes,
            text="Descuento",
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )


        self.txt_descuento = ttk.Entry(
            fila_importes,
            justify="right",
            width=14,
        )

        self.txt_descuento.grid(
            row=1,
            column=1,
            padx=(0, 8),
            sticky="w",
        )


        ttk.Label(
            fila_importes,
            text="Observación del producto",
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )


        self.txt_observacion_producto = (
            ttk.Entry(
                fila_importes
            )
        )

        self.txt_observacion_producto.grid(
            row=1,
            column=2,
            padx=(0, 8),
            sticky="ew",
        )


        ttk.Button(
            fila_importes,
            text="Agregar / actualizar",
            command=self._agregar_producto,
        ).grid(
            row=1,
            column=3,
            sticky="ew",
        )


    # =========================================================
    # DETALLE
    # =========================================================

    def _crear_detalle(
        self,
        parent: ttk.Frame,
    ) -> None:

        marco = ttk.Frame(
            parent
        )

        marco.grid(
            row=4,
            column=0,
            sticky="nsew",
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
            "cantidad",
            "tipo",
            "descuento",
            "observaciones",
        )

        self.grilla = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
            height=8,
        )

        titulos = {
            "producto": "Producto",
            "cantidad": "Cantidad",
            "tipo": "Tipo",
            "descuento": "Descuento",
            "observaciones": "Observaciones",
        }

        for columna, titulo in titulos.items():
            self.grilla.heading(
                columna,
                text=titulo,
            )

        self.grilla.column(
            "producto",
            width=380,
            anchor="w",
            stretch=True,
        )

        self.grilla.column(
            "cantidad",
            width=100,
            anchor="center",
        )

        self.grilla.column(
            "tipo",
            width=100,
            anchor="center",
        )

        self.grilla.column(
            "descuento",
            width=110,
            anchor="center",
        )

        self.grilla.column(
            "observaciones",
            width=400,
            anchor="w",
            stretch=True,
        )

        barra_vertical = ttk.Scrollbar(
            marco,
            orient="vertical",
            command=self.grilla.yview,
        )

        self.grilla.configure(
            yscrollcommand=
                barra_vertical.set,
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

        self.grilla.bind(
            "<Double-Button-1>",
            self._editar_producto_seleccionado,
        )


    # =========================================================
    # PIE
    # =========================================================

    def _crear_pie(
        self,
        parent: ttk.Frame,
    ) -> None:

        pie = ttk.Frame(
            parent
        )

        pie.grid(
            row=5,
            column=0,
            sticky="ew",
            pady=(8, 0),
        )

        pie.columnconfigure(
            2,
            weight=1,
        )


        ttk.Button(
            pie,
            text="Modificar seleccionado",
            command=
                self._editar_producto_seleccionado,
        ).grid(
            row=0,
            column=0,
            padx=(0, 8),
            sticky="w",
        )


        ttk.Button(
            pie,
            text="Quitar producto",
            command=self._quitar_producto,
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )

        pie.columnconfigure(
            2,
            weight=1,
        )

        ttk.Button(
            pie,
            text="Cancelar",
            command=self.destroy,
        ).grid(
            row=0,
            column=3,
            padx=(0, 8),
        )


        ttk.Button(
            pie,
            text="Generar pedido",
            command=self._guardar,
        ).grid(
            row=0,
            column=4,
        )


    # =========================================================
    # CATÁLOGOS
    # =========================================================

    def _cargar_catalogos(
        self,
    ) -> bool:

        try:
            modalidades = (
                listar_modalidades()
            )

            productos = (
                listar_productos()
            )

        except Exception as error:
            messagebox.showerror(
                "Revisar pedido",
                (
                    "No se pudieron cargar "
                    "los catálogos."
                    f"\n\n{error}"
                ),
                parent=self,
            )

            self.destroy()
            return False


        self.cbo_modalidad.configure(
            values=modalidades
        )


        textos: list[str] = []


        for producto in productos:

            id_producto = int(
                producto[
                    "id_producto"
                ]
            )


            texto = (
                f"{id_producto} - "
                f"{producto['descripcion']} "
            
            )


            textos.append(
                texto
            )


            self._productos_por_texto[
                texto
            ] = producto


            self._productos_por_id[
                id_producto
            ] = producto


            self._texto_producto_por_id[
                id_producto
            ] = texto


        self.cbo_producto.establecer_valores(
            textos
        )

        return True


    # =========================================================
    # CARGAR PROYECCIÓN
    # =========================================================

    def _cargar_proyeccion(
        self,
    ) -> None:

        cliente = str(
            self._cabecera.get(
                "cliente"
            )
            or ""
        )


        self.lbl_cliente.configure(
            text=cliente
        )


        modalidad = str(
            self._cabecera.get(
                "modalidad_entrega"
            )
            or ""
        ).strip().upper()


        if modalidad:
            self.cbo_modalidad.set(
                modalidad
            )

        else:
            valores = (
                self.cbo_modalidad.cget(
                    "values"
                )
            )

            if valores:
                self.cbo_modalidad.set(
                    valores[0]
                )


        fecha_entrega = (
            self._cabecera.get(
                "fecha_entrega_proyectada"
            )
        )


        if fecha_entrega is None:
            fecha_entrega = date.today()


        self.txt_fecha_entrega.set_date(
            fecha_entrega
        )


        hora = (
            self._cabecera.get(
                "hora_entrega_sugerida"
            )
        )


        self.hora_entrega.establecer_hora(
            hora
        )


        direccion = str(
            self._cabecera.get(
                "direccion_entrega_sugerida"
            )
            or ""
        )


        self.txt_direccion.delete(
            0,
            "end",
        )


        if direccion:
            self.txt_direccion.insert(
                0,
                direccion,
            )

        observaciones = str(
            self._cabecera.get(
                "observaciones_ocurrencia"
            )
            or ""
        ).strip()


        if observaciones:
            self.txt_observaciones.insert(
                0,
                observaciones,
            )


        # -----------------------------------------------------
        # Productos sugeridos
        # -----------------------------------------------------

        for fila in (
            self._detalles_proyectados
        ):

            id_producto = int(
                fila[
                    "id_producto"
                ]
            )


            cantidad = Decimal(
                str(
                    fila[
                        "cantidad_sugerida"
                    ]
                )
            )


            producto_actual = (
                self._productos_por_id.get(
                    id_producto
                )
            )


            descripcion = str(
                fila.get(
                    "producto"
                )
                or (
                    producto_actual[
                        "descripcion"
                    ]
                    if producto_actual
                    else (
                        f"Producto "
                        f"{id_producto}"
                    )
                )
            )


            precio = Decimal("0")


            if producto_actual:
                precio = Decimal(
                    str(
                        producto_actual.get(
                            "precio_mayor"
                        )
                        or 0
                    )
                )


            self._detalle[
                id_producto
            ] = DetalleRevision(
                id_producto=
                    id_producto,

                descripcion=
                    descripcion,

                cantidad=
                    cantidad,

                tipo_precio=
                    "MAYOR",

                precio_unitario=
                    precio,

                descuento=
                    Decimal("0"),

                observaciones=(
                    str(
                        fila.get(
                            "observaciones_producto"
                        )
                        or ""
                    ).strip()
                    or None
                ),
            )


        self.cbo_tipo_precio.set(
            "MAYOR"
        )


        self.txt_descuento.insert(
            0,
            "0,00",
        )


        self._sugerir_fecha_elaboracion()

        self._actualizar_grilla()


    # =========================================================
    # FECHA ELABORACIÓN
    # =========================================================

    def _sugerir_fecha_elaboracion(
        self,
        _evento=None,
    ) -> None:

        fecha_entrega = (
            self.txt_fecha_entrega
            .get_date()
        )


        modalidad = (
            self.cbo_modalidad
            .get()
            .strip()
            .upper()
        )


        if modalidad == "REPARTO":
            fecha = (
                fecha_entrega
                - timedelta(days=1)
            )

        else:
            fecha = fecha_entrega


        self.txt_fecha_elaboracion.set_date(
            fecha
        )


    # =========================================================
    # PRECIO
    # =========================================================

    def _actualizar_precio(
        self,
        _evento=None,
    ) -> None:

        producto = (
            self._productos_por_texto.get(
                self.cbo_producto.get()
            )
        )


        if not producto:
            return


        tipo = (
            self.cbo_tipo_precio
            .get()
            .strip()
            .upper()
        )


        if tipo == "ESPECIAL":
            self.txt_precio.configure(
                state="normal"
            )

            return


        if tipo == "MENOR":
            precio = Decimal(
                str(
                    producto.get(
                        "precio_menor"
                    )
                    or 0
                )
            )

        elif tipo == "MAYOR":
            precio = Decimal(
                str(
                    producto.get(
                        "precio_mayor"
                    )
                    or 0
                )
            )

        else:
            return


        self.txt_precio.configure(
            state="normal"
        )

        self.txt_precio.delete(
            0,
            "end",
        )

        self.txt_precio.insert(
            0,
            formato_decimal(
                precio
            ),
        )

        self.txt_precio.configure(
            state="readonly"
        )


    # =========================================================
    # AGREGAR / ACTUALIZAR
    # =========================================================

    def _agregar_producto(
        self,
    ) -> None:

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
                    "La cantidad debe ser "
                    "mayor que cero."
                )


            tipo_precio = (
                self.cbo_tipo_precio
                .get()
                .strip()
                .upper()
            )


            if tipo_precio not in (
                "MENOR",
                "MAYOR",
                "ESPECIAL",
            ):
                raise ValueError(
                    "Debe seleccionar "
                    "un tipo de precio."
                )


            precio = convertir_decimal(
                self.txt_precio.get()
            )


            if precio <= 0:
                raise ValueError(
                    "El precio unitario debe "
                    "ser mayor que cero."
                )


            descuento = convertir_decimal(
                self.txt_descuento.get()
            )


            if descuento < 0:
                raise ValueError(
                    "El descuento no puede "
                    "ser negativo."
                )


            id_producto = int(
                producto[
                    "id_producto"
                ]
            )


            self._detalle[
                id_producto
            ] = DetalleRevision(
                id_producto=
                    id_producto,

                descripcion=
                    str(
                        producto[
                            "descripcion"
                        ]
                    ),

                cantidad=
                    cantidad,

                tipo_precio=
                    tipo_precio,

                precio_unitario=
                    precio,

                descuento=
                    descuento,

                observaciones=(
                    self
                    .txt_observacion_producto
                    .get()
                    .strip()
                    or None
                ),
            )


            self._actualizar_grilla()

            self._limpiar_producto()


        except Exception as error:
            messagebox.showwarning(
                "Producto",
                str(error),
                parent=self,
            )


    # =========================================================
    # EDITAR EXISTENTE
    # =========================================================

    def _editar_producto_seleccionado(
        self,
        _evento=None,
    ) -> None:

        seleccion = (
            self.grilla.selection()
        )


        if not seleccion:
            messagebox.showwarning(
                "Editar producto",
                "Seleccione un producto.",
                parent=self,
            )
            return


        id_producto = int(
            seleccion[0]
        )


        detalle = (
            self._detalle.get(
                id_producto
            )
        )


        if detalle is None:
            return


        texto_producto = (
            self._texto_producto_por_id.get(
                id_producto
            )
        )


        if texto_producto is None:
            messagebox.showwarning(
                "Editar producto",
                (
                    "El producto proyectado ya "
                    "no está disponible en el "
                    "catálogo activo.\n\n"
                    "Puede quitarlo y agregar "
                    "otro producto."
                ),
                parent=self,
            )
            return


        self.cbo_producto.set(
            texto_producto
        )


        self.txt_cantidad.delete(
            0,
            "end",
        )

        self.txt_cantidad.insert(
            0,
            formato_cantidad(
                detalle.cantidad
            ),
        )


        self.cbo_tipo_precio.set(
            detalle.tipo_precio
        )


        self.txt_precio.configure(
            state="normal"
        )

        self.txt_precio.delete(
            0,
            "end",
        )

        self.txt_precio.insert(
            0,
            formato_decimal(
                detalle.precio_unitario
            ),
        )


        if (
            detalle.tipo_precio
            != "ESPECIAL"
        ):
            self.txt_precio.configure(
                state="readonly"
            )


        self.txt_descuento.delete(
            0,
            "end",
        )

        self.txt_descuento.insert(
            0,
            formato_decimal(
                detalle.descuento
            ),
        )


        self.txt_observacion_producto.delete(
            0,
            "end",
        )


        if detalle.observaciones:
            self.txt_observacion_producto.insert(
                0,
                detalle.observaciones,
            )


        self.txt_cantidad.focus_set()
        self.txt_cantidad.selection_range (
            0,
            "end",
        )


    # =========================================================
    # QUITAR
    # =========================================================

    def _quitar_producto(
        self,
    ) -> None:

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


    # =========================================================
    # GRILLA
    # =========================================================

    def _actualizar_grilla(
        self,
    ) -> None:

        for item in (
            self.grilla.get_children()
        ):
            self.grilla.delete(
                item
            )

        for detalle in (
            self._detalle.values()
        ):

            self.grilla.insert(
                "",
                "end",
                iid=str(
                    detalle.id_producto
                ),
                values=(
                    detalle.descripcion,

                    formato_cantidad(
                        detalle.cantidad
                    ),

                    detalle.tipo_precio,

                    formato_decimal(
                        detalle.descuento
                    ),

                    detalle.observaciones
                    or "",
                ),
            )

    # =========================================================
    # LIMPIAR PRODUCTO
    # =========================================================

    def _limpiar_producto(
        self,
    ) -> None:

        self.cbo_producto.limpiar()


        self.txt_cantidad.delete(
            0,
            "end",
        )


        self.cbo_tipo_precio.set(
            "MAYOR"
        )


        self.txt_precio.configure(
            state="normal"
        )

        self.txt_precio.delete(
            0,
            "end",
        )


        self.txt_descuento.delete(
            0,
            "end",
        )

        self.txt_descuento.insert(
            0,
            "0,00",
        )


        self.txt_observacion_producto.delete(
            0,
            "end",
        )


        self.cbo_producto.focus_set()


    # =========================================================
    # GENERAR PEDIDO
    # =========================================================

    def _guardar(
        self,
    ) -> None:

        try:
            if not self._detalle:
                raise ValueError(
                    "El pedido debe contener "
                    "al menos un producto."
                )


            modalidad = (
                self.cbo_modalidad
                .get()
                .strip()
                .upper()
            )


            if not modalidad:
                raise ValueError(
                    "Debe seleccionar "
                    "una modalidad."
                )


            fecha_entrega = (
                self.txt_fecha_entrega
                .get_date()
            )


            fecha_elaboracion = (
                self.txt_fecha_elaboracion
                .get_date()
            )


            hora_entrega = (
                self.hora_entrega
                .obtener_hora()
            )

            importe_envio=Decimal("0")

            detalle_json = []


            for detalle in (
                self._detalle.values()
            ):

                if (
                    detalle.cantidad
                    <= 0
                ):
                    raise ValueError(
                        (
                            f"La cantidad de "
                            f"{detalle.descripcion} "
                            f"no es válida."
                        )
                    )


                if (
                    detalle.precio_unitario
                    <= 0
                ):
                    raise ValueError(
                        (
                            f"El producto "
                            f"{detalle.descripcion} "
                            f"no tiene un precio "
                            f"válido."
                        )
                    )


                detalle_json.append(
                    {
                        "id_producto":
                            detalle.id_producto,

                        "cantidad":
                            detalle.cantidad,

                        "tipo_precio":
                            detalle.tipo_precio,

                        "precio_unitario":
                            detalle.precio_unitario,

                        "descuento":
                            detalle.descuento,

                        "observaciones":
                            detalle.observaciones,
                    }
                )


            id_ocurrencia = int(
                self._cabecera[
                    "id_pedido_recurrente_ocurrencia"
                ]
            )


            resultado = (
                generar_pedido_desde_proyeccion(
                    id_ocurrencia=
                        id_ocurrencia,

                    modalidad_entrega=
                        modalidad,

                    fecha_entrega=
                        fecha_entrega,

                    hora_entrega=
                        hora_entrega,

                    fecha_elaboracion=
                        fecha_elaboracion,

                    requiere_confirmacion=
                        self.requiere_confirmacion
                        .get(),

                    direccion_entrega=(
                        self.txt_direccion
                        .get()
                        .strip()
                        or None
                    ),

                    importe_envio=
                        importe_envio,

                    detalles=
                        detalle_json,

                    observaciones=(
                        self.txt_observaciones
                        .get()
                        .strip()
                        or None
                    ),
                )
            )


            id_pedido = int(
                resultado[
                    "id_pedido"
                ]
            )


        except Exception as error:

            messagebox.showerror(
                "Generar pedido",
                (
                    "No se pudo generar "
                    "el pedido."
                    f"\n\n{error}"
                ),
                parent=self,
            )

            return


        messagebox.showinfo(
            "Pedido generado",
            (
                "Pedido generado "
                "correctamente."
                "\n\n"
                f"Número de pedido: "
                f"{id_pedido}"
            ),
            parent=self,
        )


        if self._al_guardar:
            self._al_guardar(
                id_pedido
            )


        self.destroy()