from __future__ import annotations

import tkinter as tk
from datetime import date, timedelta
from decimal import Decimal
from tkinter import messagebox, ttk
from typing import Any
from ui.ventana_util import maximizar_ventana

from tkcalendar import DateEntry

from db.planificacion_repository import (
    asignar_stock,
    buscar_contexto_pedido,
    guardar_plan_producto,
    listar_detalles_grupo,
    listar_planificacion_productos,
    listar_planes_grupo,
)
from ui.navegacion import crear_barra_navegacion
from ui.pedido import convertir_cantidad, formato_cantidad
from ui.reporte_planificacion import VentanaReportePlanificacion


class VentanaPlanificacion(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        navegador=None,
    ) -> None:
        super().__init__(parent)

        self.navegador = navegador

        self._filas_grupo: dict[str, dict[str, Any]] = {}
        self._filas_detalle: dict[str, dict[str, Any]] = {}

        self._seleccion_grupo: dict[str, Any] | None = None
        self._seleccion_detalle: dict[str, Any] | None = None

        self.title("Planificación de elaboración")
        # self.transient(parent)
        self.resizable(True, True)

        self._pantalla_compacta = (
            self.winfo_screenwidth() < 1250
        )

        # self._ajustar_tamano_inicial()
        maximizar_ventana(self)

        if self.navegador is not None:
            crear_barra_navegacion(
                ventana=self,
                navegador=self.navegador,
                modulo_actual="planificacion",
            )

        self._crear_interfaz()
        self._inicializar_filtros()
        self._actualizar()

    def _ajustar_tamano_inicial(self) -> None:
        ancho_pantalla = self.winfo_screenwidth()
        alto_pantalla = self.winfo_screenheight()

        ancho = int(ancho_pantalla * 0.94)

        alto_disponible = max(
            alto_pantalla - 80,
            500,
        )
        alto = int(alto_disponible * 0.96)

        ancho = min(
            ancho,
            ancho_pantalla - 20,
        )
        alto = min(
            alto,
            alto_pantalla - 60,
        )

        self.minsize(
            min(860, ancho),
            min(620, alto),
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

    def _abrir_reporte(self) -> None:
        VentanaReportePlanificacion(self)

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

        contenedor.rowconfigure(2, weight=3)
        contenedor.rowconfigure(3, weight=2)
        contenedor.rowconfigure(5, weight=1)

        ttk.Label(
            contenedor,
            text="Planificación de elaboración",
            font=("Segoe UI", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 8),
        )

        self._crear_filtros(contenedor)
        self._crear_grilla_productos(contenedor)
        self._crear_grilla_detalles(contenedor)
        self._crear_panel_acciones(contenedor)
        self._crear_grilla_planes(contenedor)

    def _crear_filtros(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Filtros de elaboración",
            padding=10,
        )
        marco.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        marco.columnconfigure(0, weight=1)

        campos = ttk.Frame(marco)
        campos.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        campos.columnconfigure(0, weight=0)
        campos.columnconfigure(1, weight=0)
        campos.columnconfigure(2, weight=0)
        campos.columnconfigure(3, weight=1)

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
            sticky="ew",
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
            padx=(0, 8),
            sticky="ew",
        )

        ttk.Label(
            campos,
            text="Modalidad",
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )
        self.fecha_desde.bind(
            "<<DateEntrySelected>>",
            self._sincronizar_fecha_hasta,
        )       

        self.cbo_modalidad = ttk.Combobox(
            campos,
            state="readonly",
            width=14,
            values=(
                "TODAS",
                "MOSTRADOR",
                "REPARTO",
            ),
        )
        self.cbo_modalidad.grid(
            row=1,
            column=2,
            padx=(0, 12),
            sticky="w",
        )

        self.solo_pendientes = tk.BooleanVar(
            value=True
        )

        ttk.Checkbutton(
            campos,
            text="Sólo pendientes",
            variable=self.solo_pendientes,
        ).grid(
            row=1,
            column=3,
            sticky="w",
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
            text="Actualizar",
            command=self._actualizar,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            acciones,
            text="Reporte de elaboración",
            command=self._abrir_reporte,
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

    def _crear_grilla_productos(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Necesidad de elaboración por producto",
            padding=8,
        )
        marco.grid(
            row=2,
            column=0,
            sticky="nsew",
            pady=(0, 8),
        )

        marco.rowconfigure(0, weight=1)
        marco.columnconfigure(0, weight=1)

        columnas = (
            "fecha",
            "producto",
            "pedidos",
            "cantidad",
            "stock",
            "asignado_stock",
            "planificado",
            "pendiente",
            "primera_entrega",
            "ultima_entrega",
        )

        self.grilla = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
            height=8,
        )

        titulos = {
            "fecha": "Elaboración",
            "producto": "Producto",
            "pedidos": "Pedidos",
            "cantidad": "Pedido total",
            "stock": "Stock actual",
            "asignado_stock": "Desde stock",
            "planificado": "Planificado",
            "pendiente": "A elaborar",
            "primera_entrega": "Primera entrega",
            "ultima_entrega": "Última entrega",
        }

        anchos = {
            "fecha": 100,
            "producto": 280,
            "pedidos": 75,
            "cantidad": 105,
            "stock": 95,
            "asignado_stock": 100,
            "planificado": 100,
            "pendiente": 105,
            "primera_entrega": 105,
            "ultima_entrega": 105,
        }

        for columna in columnas:
            self.grilla.heading(
                columna,
                text=titulos[columna],
            )
            self.grilla.column(
                columna,
                width=anchos[columna],
                minwidth=(
                    180
                    if columna == "producto"
                    else 75
                ),
                anchor=(
                    "w"
                    if columna == "producto"
                    else "center"
                ),
                stretch=(columna == "producto"),
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
            self._seleccionar_grupo,
        )

    def _crear_grilla_detalles(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Pedidos incluidos en el producto seleccionado",
            padding=8,
        )
        marco.grid(
            row=3,
            column=0,
            sticky="nsew",
            pady=(0, 8),
        )

        marco.rowconfigure(0, weight=1)
        marco.columnconfigure(0, weight=1)

        columnas = (
            "pedido",
            "entrega",
            "hora",
            "modalidad",
            "cliente",
            "cantidad",
            "desde_stock",
            "planificado",
            "pendiente",
        )

        self.grilla_detalles = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
            height=5,
        )

        titulos = {
            "pedido": "Pedido",
            "entrega": "Entrega",
            "hora": "Hora",
            "modalidad": "Modalidad",
            "cliente": "Cliente",
            "cantidad": "Pedido",
            "desde_stock": "Desde stock",
            "planificado": "Planificado",
            "pendiente": "Pendiente",
        }

        anchos = {
            "pedido": 70,
            "entrega": 95,
            "hora": 70,
            "modalidad": 95,
            "cliente": 260,
            "cantidad": 90,
            "desde_stock": 95,
            "planificado": 95,
            "pendiente": 95,
        }

        for columna in columnas:
            self.grilla_detalles.heading(
                columna,
                text=titulos[columna],
            )
            self.grilla_detalles.column(
                columna,
                width=anchos[columna],
                minwidth=(
                    170
                    if columna == "cliente"
                    else 65
                ),
                anchor=(
                    "w"
                    if columna == "cliente"
                    else "center"
                ),
                stretch=(columna == "cliente"),
            )

        barra_vertical = ttk.Scrollbar(
            marco,
            orient="vertical",
            command=self.grilla_detalles.yview,
        )
        barra_horizontal = ttk.Scrollbar(
            marco,
            orient="horizontal",
            command=self.grilla_detalles.xview,
        )

        self.grilla_detalles.configure(
            yscrollcommand=barra_vertical.set,
            xscrollcommand=barra_horizontal.set,
        )

        self.grilla_detalles.grid(
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

        self.grilla_detalles.bind(
            "<<TreeviewSelect>>",
            self._seleccionar_detalle,
        )

    def _crear_panel_acciones(
        self,
        parent: ttk.Frame,
    ) -> None:
        panel = ttk.Frame(parent)
        panel.grid(
            row=4,
            column=0,
            sticky="ew",
        )

        if self._pantalla_compacta:
            panel.columnconfigure(0, weight=1)

            self._crear_panel_stock(
                panel,
                fila=0,
                columna=0,
                padx=(0, 0),
            )
            self._crear_panel_plan(
                panel,
                fila=1,
                columna=0,
                padx=(0, 0),
                pady=(8, 0),
            )
        else:
            panel.columnconfigure(0, weight=1)
            panel.columnconfigure(1, weight=2)

            self._crear_panel_stock(
                panel,
                fila=0,
                columna=0,
                padx=(0, 6),
            )
            self._crear_panel_plan(
                panel,
                fila=0,
                columna=1,
                padx=(6, 0),
            )

    def _crear_panel_stock(
        self,
        parent: ttk.Frame,
        *,
        fila: int,
        columna: int,
        padx=(0, 0),
        pady=(0, 0),
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Asignar stock al pedido seleccionado",
            padding=12,
        )
        marco.grid(
            row=fila,
            column=columna,
            padx=padx,
            pady=pady,
            sticky="nsew",
        )

        marco.columnconfigure(0, weight=1)
        marco.columnconfigure(1, weight=1)

        self.lbl_detalle_stock = ttk.Label(
            marco,
            text="Seleccione un pedido del detalle.",
        )
        self.lbl_detalle_stock.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 6),
        )

        ttk.Label(
            marco,
            text="Cantidad total asignada",
        ).grid(
            row=1,
            column=0,
            sticky="w",
        )

        self.txt_stock = ttk.Entry(
            marco,
            justify="right",
            width=16,
        )
        self.txt_stock.grid(
            row=2,
            column=0,
            padx=(0, 8),
            sticky="ew",
        )

        self.btn_asignar_stock = ttk.Button(
            marco,
            text="Guardar asignación",
            command=self._guardar_stock,
            state="disabled",
        )
        self.btn_asignar_stock.grid(
            row=2,
            column=1,
            sticky="ew",
        )

        ttk.Label(
            marco,
            text=(
                "Reemplaza la asignación anterior. "
                "Utilice 0 para liberarla."
            ),
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            pady=(8, 0),
            sticky="w",
        )

    def _crear_panel_plan(
        self,
        parent: ttk.Frame,
        *,
        fila: int,
        columna: int,
        padx=(0, 0),
        pady=(0, 0),
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Planificar elaboración del producto",
            padding=12,
        )
        marco.grid(
            row=fila,
            column=columna,
            padx=padx,
            pady=pady,
            sticky="nsew",
        )

        marco.columnconfigure(0, weight=1)
        marco.columnconfigure(1, weight=1)
        marco.columnconfigure(2, weight=3)
        marco.columnconfigure(3, weight=1)
        marco.columnconfigure(4, weight=1)

        ttk.Label(
            marco,
            text="Fecha",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.fecha_plan = DateEntry(
            marco,
            date_pattern="dd/mm/yyyy",
            locale="es_AR",
            firstweekday="monday",
            width=12,
        )
        self.fecha_plan.grid(
            row=1,
            column=0,
            padx=(0, 8),
            sticky="ew",
        )

        ttk.Label(
            marco,
            text="Cantidad",
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )

        self.txt_cantidad_plan = ttk.Entry(
            marco,
            justify="right",
            width=14,
        )
        self.txt_cantidad_plan.grid(
            row=1,
            column=1,
            padx=(0, 8),
            sticky="ew",
        )

        ttk.Label(
            marco,
            text="Observaciones",
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )

        self.txt_observaciones_plan = ttk.Entry(
            marco,
            width=35,
        )
        self.txt_observaciones_plan.grid(
            row=1,
            column=2,
            padx=(0, 8),
            sticky="ew",
        )

        self.btn_total_pendiente = ttk.Button(
            marco,
            text="Usar pendiente",
            command=self._usar_total_pendiente,
            state="disabled",
        )
        self.btn_total_pendiente.grid(
            row=1,
            column=3,
            padx=(0, 8),
            sticky="ew",
        )

        self.btn_agregar_plan = ttk.Button(
            marco,
            text="Agregar al plan",
            command=self._guardar_plan,
            state="disabled",
        )
        self.btn_agregar_plan.grid(
            row=1,
            column=4,
            sticky="ew",
        )

    def _crear_grilla_planes(
        self,
        parent: ttk.Frame,
    ) -> None:
        self.marco_planes = ttk.LabelFrame(
            parent,
            text="Plan ya registrado para el grupo",
            padding=8,
        )
        self.marco_planes.grid(
            row=5,
            column=0,
            sticky="nsew",
            pady=(8, 0),
        )

        self.marco_planes.columnconfigure(0, weight=1)
        self.marco_planes.rowconfigure(0, weight=1)

        columnas = (
            "fecha",
            "cantidad",
            "estado",
            "detalles",
            "observaciones",
        )

        self.grilla_planes = ttk.Treeview(
            self.marco_planes,
            columns=columnas,
            show="headings",
            height=4,
        )

        titulos = {
            "fecha": "Fecha",
            "cantidad": "Cantidad",
            "estado": "Estado",
            "detalles": "Detalles afectados",
            "observaciones": "Observaciones",
        }

        anchos = {
            "fecha": 100,
            "cantidad": 110,
            "estado": 120,
            "detalles": 120,
            "observaciones": 500,
        }

        for columna in columnas:
            self.grilla_planes.heading(
                columna,
                text=titulos[columna],
            )
            self.grilla_planes.column(
                columna,
                width=anchos[columna],
                minwidth=(
                    180
                    if columna == "observaciones"
                    else 85
                ),
                anchor=(
                    "w"
                    if columna == "observaciones"
                    else "center"
                ),
                stretch=(columna == "observaciones"),
            )

        barra_vertical = ttk.Scrollbar(
            self.marco_planes,
            orient="vertical",
            command=self.grilla_planes.yview,
        )
        barra_horizontal = ttk.Scrollbar(
            self.marco_planes,
            orient="horizontal",
            command=self.grilla_planes.xview,
        )

        self.grilla_planes.configure(
            yscrollcommand=barra_vertical.set,
            xscrollcommand=barra_horizontal.set,
        )

        self.grilla_planes.grid(
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

    def _inicializar_filtros(self) -> None:
        hoy = date.today()

        self.fecha_desde.set_date(hoy)
        self.fecha_hasta.set_date(hoy)
        self.cbo_modalidad.set("TODAS")

    def _modalidad_filtro(self) -> str | None:
        modalidad = self.cbo_modalidad.get().strip().upper()

        if not modalidad or modalidad == "TODAS":
            return None

        return modalidad
    def aplicar_contexto(
        self,
        *,
        id_pedido: int | None = None,
    ) -> None:
        if id_pedido is None:
            return

        try:
            contexto = buscar_contexto_pedido(
                id_pedido
            )

        except Exception as error:
            messagebox.showerror(
                "Planificación",
                (
                    f"No se pudo localizar el pedido "
                    f"{id_pedido} en Planificación."
                    f"\n\n{error}"
                ),
                parent=self,
            )
            return

        if contexto is None:
            messagebox.showinfo(
                "Planificación",
                (
                    f"El pedido {id_pedido} no tiene "
                    "cantidades pendientes de planificación."
                ),
                parent=self,
            )
            return


        fecha_grupo = contexto[
            "fecha_elaboracion_sugerida"
        ]

        id_producto = int(
            contexto["id_producto"]
        )

        id_detalle = int(
            contexto["id_pedido_detalle"]
        )


        # Ajustamos el filtro para garantizar
        # que el pedido pueda verse.
        self.fecha_desde.set_date(
            fecha_grupo
        )

        self.fecha_hasta.set_date(
            fecha_grupo
        )

        self.cbo_modalidad.set(
            "TODAS"
        )

        self.solo_pendientes.set(
            True
        )


        # _actualizar ya sabe:
        # 1. seleccionar el producto,
        # 2. hacerlo visible,
        # 3. cargar sus pedidos,
        # 4. seleccionar el detalle exacto.
        self._actualizar(
            conservar_clave=(
                id_producto,
                fecha_grupo,
            ),
            conservar_detalle=id_detalle,
        )

    def _clave_grupo(
        self,
        fila: dict[str, Any],
    ) -> tuple[int, date]:
        return (
            int(fila["id_producto"]),
            fila["fecha_elaboracion_sugerida"],
        )

    def _actualizar(
        self,
        *,
        conservar_clave: tuple[int, date] | None = None,
        conservar_detalle: int | None = None,
    ) -> None:
        try:
            filas = listar_planificacion_productos(
                fecha_desde=self.fecha_desde.get_date(),
                fecha_hasta=self.fecha_hasta.get_date(),
                modalidad=self._modalidad_filtro(),
                solo_pendientes=self.solo_pendientes.get(),
            )
        except Exception as error:
            messagebox.showerror(
                "Planificación",
                "No se pudo recuperar la planificación."
                f"\n\n{error}",
                parent=self,
            )
            return

        self._filas_grupo.clear()

        for item in self.grilla.get_children():
            self.grilla.delete(item)

        item_a_seleccionar = None

        for indice, fila in enumerate(filas):
            fecha_grupo = fila[
                "fecha_elaboracion_sugerida"
            ]

            iid = (
                f"{fila['id_producto']}-"
                f"{fecha_grupo:%Y%m%d}-"
                f"{indice}"
            )

            self._filas_grupo[iid] = fila

            self.grilla.insert(
                "",
                "end",
                iid=iid,
                values=(
                    fecha_grupo.strftime("%d/%m/%Y"),
                    fila["descripcion_producto"],
                    int(fila["cantidad_pedidos"]),
                    formato_cantidad(
                        fila["cantidad"]
                    ),
                    formato_cantidad(
                        fila["stock_actual"]
                    ),
                    formato_cantidad(
                        fila["cantidad_desde_stock"]
                    ),
                    formato_cantidad(
                        fila["cantidad_planificada"]
                    ),
                    formato_cantidad(
                        fila["cantidad_sin_planificar"]
                    ),
                    fila["primera_entrega"].strftime(
                        "%d/%m/%Y"
                    ),
                    fila["ultima_entrega"].strftime(
                        "%d/%m/%Y"
                    ),
                ),
            )

            if (
                conservar_clave is not None
                and self._clave_grupo(fila)
                == conservar_clave
            ):
                item_a_seleccionar = iid

        if item_a_seleccionar is not None:
            self.grilla.selection_set(item_a_seleccionar)
            self.grilla.focus(item_a_seleccionar)
            self.grilla.see(item_a_seleccionar)

            self._seleccionar_grupo(
                conservar_detalle=conservar_detalle
            )
        else:
            self._limpiar_seleccion_grupo()

    def _seleccionar_grupo(
        self,
        _evento=None,
        *,
        conservar_detalle: int | None = None,
    ) -> None:
        seleccion = self.grilla.selection()

        if not seleccion:
            self._limpiar_seleccion_grupo()
            return

        fila = self._filas_grupo[seleccion[0]]
        self._seleccion_grupo = fila

        self.txt_cantidad_plan.delete(0, "end")

        self.fecha_plan.set_date(
            fila["fecha_elaboracion_sugerida"]
        )

        self.txt_observaciones_plan.delete(0, "end")

        self.btn_total_pendiente.configure(
            state="normal"
        )
        self.btn_agregar_plan.configure(
            state="normal"
        )

        self._cargar_detalles_grupo(
            conservar_detalle=conservar_detalle
        )
        self._cargar_planes_grupo()

    def _cargar_detalles_grupo(
        self,
        *,
        conservar_detalle: int | None = None,
    ) -> None:
        self._filas_detalle.clear()

        for item in self.grilla_detalles.get_children():
            self.grilla_detalles.delete(item)

        self._limpiar_seleccion_detalle()

        if self._seleccion_grupo is None:
            return

        grupo = self._seleccion_grupo

        try:
            detalles = listar_detalles_grupo(
                id_producto=int(grupo["id_producto"]),
                fecha_grupo=grupo[
                    "fecha_elaboracion_sugerida"
                ],
                modalidad=self._modalidad_filtro(),
            )
        except Exception as error:
            messagebox.showerror(
                "Planificación",
                "No se pudieron recuperar los pedidos "
                f"del grupo.\n\n{error}",
                parent=self,
            )
            return

        item_a_seleccionar = None

        for detalle in detalles:
            iid = str(detalle["id_pedido_detalle"])
            self._filas_detalle[iid] = detalle

            hora_entrega = detalle["hora_entrega"]
            hora_texto = (
                hora_entrega.strftime("%H:%M")
                if hora_entrega is not None
                else ""
            )

            self.grilla_detalles.insert(
                "",
                "end",
                iid=iid,
                values=(
                    detalle["id_pedido"],
                    detalle["fecha_entrega"].strftime(
                        "%d/%m/%Y"
                    ),
                    hora_texto,
                    detalle["modalidad_entrega"],
                    detalle["cliente"],
                    formato_cantidad(
                        detalle["cantidad"]
                    ),
                    formato_cantidad(
                        detalle["cantidad_desde_stock"]
                    ),
                    formato_cantidad(
                        detalle["cantidad_planificada"]
                    ),
                    formato_cantidad(
                        detalle["cantidad_sin_planificar"]
                    ),
                ),
            )

            if (
                conservar_detalle is not None
                and int(detalle["id_pedido_detalle"])
                == conservar_detalle
            ):
                item_a_seleccionar = iid

        if item_a_seleccionar is not None:
            self.grilla_detalles.selection_set(
                item_a_seleccionar
            )
            self.grilla_detalles.focus(
                item_a_seleccionar
            )
            self.grilla_detalles.see(
                item_a_seleccionar
            )
            self._seleccionar_detalle()

    def _seleccionar_detalle(
        self,
        _evento=None,
    ) -> None:
        seleccion = self.grilla_detalles.selection()

        if not seleccion:
            self._limpiar_seleccion_detalle()
            return

        fila = self._filas_detalle[seleccion[0]]
        self._seleccion_detalle = fila

        self.txt_stock.delete(0, "end")

        self.lbl_detalle_stock.configure(
            text=(
                f"Pedido {fila['id_pedido']} · "
                f"{fila['cliente']}"
            )
        )

        self.btn_asignar_stock.configure(
            state="normal"
        )

    def _cargar_planes_grupo(self) -> None:
        for item in self.grilla_planes.get_children():
            self.grilla_planes.delete(item)

        if self._seleccion_grupo is None:
            return

        grupo = self._seleccion_grupo

        try:
            planes = listar_planes_grupo(
                id_producto=int(grupo["id_producto"]),
                fecha_grupo=grupo[
                    "fecha_elaboracion_sugerida"
                ],
                modalidad=self._modalidad_filtro(),
            )
        except Exception as error:
            messagebox.showerror(
                "Planificación",
                "No se pudo recuperar el plan "
                f"del grupo.\n\n{error}",
                parent=self,
            )
            return

        for indice, plan in enumerate(planes):
            self.grilla_planes.insert(
                "",
                "end",
                iid=f"plan-{indice}",
                values=(
                    plan["fecha_elaboracion"].strftime(
                        "%d/%m/%Y"
                    ),
                    formato_cantidad(
                        plan["cantidad"]
                    ),
                    plan["estado"],
                    int(plan["cantidad_detalles"]),
                    plan["observaciones"] or "",
                ),
            )

    def _usar_total_pendiente(self) -> None:
        if self._seleccion_grupo is None:
            return

        pendiente = Decimal(
            str(
                self._seleccion_grupo[
                    "cantidad_sin_planificar"
                ]
                or 0
            )
        )

        self.txt_cantidad_plan.delete(0, "end")
        self.txt_cantidad_plan.insert(
            0,
            formato_cantidad(pendiente),
        )

    def _guardar_stock(self) -> None:
        if self._seleccion_detalle is None:
            return

        detalle = self._seleccion_detalle
        id_detalle = int(
            detalle["id_pedido_detalle"]
        )

        clave_grupo = (
            self._clave_grupo(self._seleccion_grupo)
            if self._seleccion_grupo is not None
            else None
        )

        try:
            cantidad = convertir_cantidad(
                self.txt_stock.get()
            )

            if cantidad < 0:
                raise ValueError(
                    "La cantidad no puede ser negativa."
                )

            asignar_stock(
                id_pedido_detalle=id_detalle,
                cantidad_desde_stock=cantidad,
            )
        except Exception as error:
            messagebox.showerror(
                "Asignar stock",
                "No se pudo guardar la asignación."
                f"\n\n{error}",
                parent=self,
            )
            return

        messagebox.showinfo(
            "Asignar stock",
            "La asignación se guardó correctamente.",
            parent=self,
        )

        self._actualizar(
            conservar_clave=clave_grupo,
            conservar_detalle=id_detalle,
        )

    def _guardar_plan(self) -> None:
        if self._seleccion_grupo is None:
            return

        grupo = self._seleccion_grupo
        clave_grupo = self._clave_grupo(grupo)

        try:
            cantidad = convertir_cantidad(
                self.txt_cantidad_plan.get()
            )

            if cantidad <= 0:
                raise ValueError(
                    "La cantidad debe ser mayor que cero."
                )

            pendiente = Decimal(
                str(
                    grupo[
                        "cantidad_sin_planificar"
                    ]
                    or 0
                )
            )

            if cantidad > pendiente:
                raise ValueError(
                    "La cantidad no puede superar el "
                    "pendiente del grupo ("
                    f"{formato_cantidad(pendiente)})."
                )

            observaciones = (
                self.txt_observaciones_plan
                .get()
                .strip()
                or None
            )

            resultado = guardar_plan_producto(
                id_producto=int(grupo["id_producto"]),
                fecha_grupo=grupo[
                    "fecha_elaboracion_sugerida"
                ],
                modalidad=self._modalidad_filtro(),
                fecha_elaboracion=(
                    self.fecha_plan.get_date()
                ),
                cantidad=cantidad,
                observaciones=observaciones,
            )
        except Exception as error:
            messagebox.showerror(
                "Agregar elaboración",
                "No se pudo guardar el plan."
                f"\n\n{error}",
                parent=self,
            )
            return

        cantidad_planificada = Decimal(
            str(resultado["cantidad_planificada"])
        )
        pendiente_restante = Decimal(
            str(
                resultado[
                    "cantidad_grupo_sin_planificar"
                ]
            )
        )

        messagebox.showinfo(
            "Agregar elaboración",
            "Plan guardado correctamente."
            "\n\n"
            "Cantidad planificada: "
            f"{formato_cantidad(cantidad_planificada)}"
            "\n"
            "Detalles afectados: "
            f"{resultado['detalles_afectados']}"
            "\n"
            "Pendiente restante: "
            f"{formato_cantidad(pendiente_restante)}",
            parent=self,
        )

        self._actualizar(
            conservar_clave=clave_grupo
        )

    def _limpiar_seleccion_detalle(self) -> None:
        self._seleccion_detalle = None

        self.txt_stock.delete(0, "end")
        self.lbl_detalle_stock.configure(
            text="Seleccione un pedido del detalle."
        )
        self.btn_asignar_stock.configure(
            state="disabled"
        )

        seleccion = self.grilla_detalles.selection()
        if seleccion:
            self.grilla_detalles.selection_remove(
                *seleccion
            )

    def _limpiar_seleccion_grupo(self) -> None:
        self._seleccion_grupo = None

        self._filas_detalle.clear()

        for item in self.grilla_detalles.get_children():
            self.grilla_detalles.delete(item)

        for item in self.grilla_planes.get_children():
            self.grilla_planes.delete(item)

        self.txt_cantidad_plan.delete(0, "end")
        self.txt_observaciones_plan.delete(0, "end")

        self.btn_total_pendiente.configure(
            state="disabled"
        )
        self.btn_agregar_plan.configure(
            state="disabled"
        )

        self._limpiar_seleccion_detalle()
