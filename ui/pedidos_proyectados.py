from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import messagebox, simpledialog, ttk
from typing import Any

from tkcalendar import DateEntry

from db.proyeccion_repository import (
    listar_pedidos_proyectados,
    omitir_pedido_proyectado,
)

from ui.nueva_proyeccion import (
    VentanaNuevaProyeccion,
)

from ui.revisar_pedido_proyectado import (
    VentanaRevisarPedidoProyectado,
)

from ui.navegacion import crear_barra_navegacion
from ui.pedido import formato_cantidad
from ui.ventana_util import maximizar_ventana


class VentanaPedidosProyectados(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        navegador=None,
    ) -> None:
        super().__init__(parent)

        self.navegador = navegador

        self._ocurrencias: dict[
            str,
            dict[str, Any],
        ] = {}

        self._detalles: dict[
            int,
            list[dict[str, Any]],
        ] = {}

        self._seleccion_ocurrencia: (
            dict[str, Any] | None
        ) = None

        self.title(
            "Pedidos proyectados"
        )
        self.resizable(
            True,
            True,
        )

        maximizar_ventana(self)

        if self.navegador is not None:
            crear_barra_navegacion(
                ventana=self,
                navegador=self.navegador,
                modulo_actual="proyecciones",
            )

        self._crear_interfaz()
        self._inicializar_filtros()
        self._actualizar()


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

        contenedor.columnconfigure(
            0,
            weight=1,
        )

        contenedor.rowconfigure(
            2,
            weight=2,
        )

        contenedor.rowconfigure(
            3,
            weight=2,
        )

        ttk.Label(
            contenedor,
            text="Pedidos proyectados",
            font=(
                "Segoe UI",
                18,
                "bold",
            ),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 8),
        )

        self._crear_filtros(
            contenedor
        )

        self._crear_grilla_ocurrencias(
            contenedor
        )

        self._crear_grilla_detalles(
            contenedor
        )

        self._crear_acciones(
            contenedor
        )


    def _nueva_proyeccion(self) -> None:
        VentanaNuevaProyeccion(
            self,
            al_guardar=self._actualizar,
        )

    def _crear_filtros(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Consulta",
            padding=10,
        )
        marco.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        ttk.Label(
            marco,
            text="Fecha",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.fecha = DateEntry(
            marco,
            date_pattern="dd/mm/yyyy",
            locale="es_AR",
            firstweekday="monday",
            width=12,
        )
        self.fecha.grid(
            row=1,
            column=0,
            padx=(0, 10),
            sticky="w",
        )

        ttk.Label(
            marco,
            text="Ver por",
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )

        self.cbo_criterio = ttk.Combobox(
            marco,
            state="readonly",
            width=18,
            values=(
                "A CONFIRMAR",
                "POR ENTREGAR",
            ),
        )
        self.cbo_criterio.grid(
            row=1,
            column=1,
            padx=(0, 10),
            sticky="w",
        )

        ttk.Label(
            marco,
            text="Modalidad",
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )

        self.cbo_modalidad = ttk.Combobox(
            marco,
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
            padx=(0, 10),
            sticky="w",
        )

        ttk.Button(
            marco,
            text="Actualizar",
            command=self._actualizar,
        ).grid(
            row=1,
            column=3,
            sticky="w",
        )
        ttk.Button(
    marco,
        text="Nueva proyección",
        command=self._nueva_proyeccion,
    ).grid(
        row=1,
        column=4,
        padx=(12, 0),
        sticky="w",
    )


    def _crear_grilla_ocurrencias(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text="Proyecciones pendientes",
            padding=8,
        )
        marco.grid(
            row=2,
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
            "entrega",
            "cliente",
            "modalidad",
            "hora",
            "productos",
            "direccion",
        )

        self.grilla = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
        )

        titulos = {
            "entrega": "Entrega prevista",
            "cliente": "Cliente",
            "modalidad": "Modalidad",
            "hora": "Hora habitual",
            "productos": "Productos",
            "direccion": "Dirección",
        }

        anchos = {
            "entrega": 120,
            "cliente": 280,
            "modalidad": 110,
            "hora": 100,
            "productos": 90,
            "direccion": 360,
        }

        for columna in columnas:
            self.grilla.heading(
                columna,
                text=titulos[columna],
            )

            self.grilla.column(
                columna,
                width=anchos[columna],
                anchor=(
                    "w"
                    if columna
                    in (
                        "cliente",
                        "direccion",
                    )
                    else "center"
                ),
                stretch=(
                    columna
                    in (
                        "cliente",
                        "direccion",
                    )
                ),
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

        self.grilla.bind(
            "<<TreeviewSelect>>",
            self._seleccionar_ocurrencia,
        )


    def _crear_grilla_detalles(
        self,
        parent: ttk.Frame,
    ) -> None:
        marco = ttk.LabelFrame(
            parent,
            text=(
                "Productos proyectados "
                "para el cliente seleccionado"
            ),
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
            "producto",
            "cantidad",
            "observaciones",
        )

        self.grilla_detalles = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
        )

        self.grilla_detalles.heading(
            "producto",
            text="Producto",
        )
        self.grilla_detalles.heading(
            "cantidad",
            text="Cantidad proyectada",
        )
        self.grilla_detalles.heading(
            "observaciones",
            text="Observaciones",
        )

        self.grilla_detalles.column(
            "producto",
            width=350,
            anchor="w",
        )

        self.grilla_detalles.column(
            "cantidad",
            width=150,
            anchor="center",
        )

        self.grilla_detalles.column(
            "observaciones",
            width=450,
            anchor="w",
        )

        barra = ttk.Scrollbar(
            marco,
            orient="vertical",
            command=self.grilla_detalles.yview,
        )

        self.grilla_detalles.configure(
            yscrollcommand=barra.set,
        )

        self.grilla_detalles.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        barra.grid(
            row=0,
            column=1,
            sticky="ns",
        )


    def _crear_acciones(
        self,
        parent: ttk.Frame,
    ) -> None:
        acciones = ttk.Frame(
            parent
        )
        acciones.grid(
            row=4,
            column=0,
            sticky="e",
        )

        self.btn_omitir = ttk.Button(
            acciones,
            text="Esta vez no necesita",
            command=self._omitir,
            state="disabled",
        )
        self.btn_omitir.pack(
            side="left",
            padx=(0, 8),
        )

        self.btn_revisar = ttk.Button(
            acciones,
            text="Revisar / generar pedido",
            command=self._revisar,
            state="disabled",
        )
        self.btn_revisar.pack(
            side="left",
        )


    # =========================================================
    # FILTROS
    # =========================================================

    def _inicializar_filtros(
        self,
    ) -> None:
        self.fecha.set_date(
            date.today()
        )

        self.cbo_criterio.set(
            "A CONFIRMAR"
        )

        self.cbo_modalidad.set(
            "TODAS"
        )


    def _criterio_sql(self) -> str:
        if (
            self.cbo_criterio.get()
            == "POR ENTREGAR"
        ):
            return "ENTREGA"

        return "REVISION"


    def _modalidad_sql(
        self,
    ) -> str | None:
        modalidad = (
            self.cbo_modalidad
            .get()
            .strip()
            .upper()
        )

        if (
            not modalidad
            or modalidad == "TODAS"
        ):
            return None

        return modalidad


    # =========================================================
    # CARGA
    # =========================================================

    def _actualizar(self) -> None:
        try:
            filas = listar_pedidos_proyectados(
                fecha=self.fecha.get_date(),
                criterio=self._criterio_sql(),
                modalidad=self._modalidad_sql(),
            )

        except Exception as error:
            messagebox.showerror(
                "Pedidos proyectados",
                "No se pudieron recuperar "
                "las proyecciones."
                f"\n\n{error}",
                parent=self,
            )
            return

        self._ocurrencias.clear()
        self._detalles.clear()
        self._seleccion_ocurrencia = None

        for item in self.grilla.get_children():
            self.grilla.delete(item)

        for item in self.grilla_detalles.get_children():
            self.grilla_detalles.delete(item)

        self.btn_omitir.configure(
            state="disabled"
        )
        self.btn_revisar.configure(
            state="disabled"
        )


        # -----------------------------------------
        # Agrupar las filas del SP por ocurrencia
        # -----------------------------------------

        for fila in filas:
            id_ocurrencia = int(
                fila[
                    "id_pedido_recurrente_ocurrencia"
                ]
            )

            if id_ocurrencia not in self._detalles:
                self._detalles[
                    id_ocurrencia
                ] = []

            self._detalles[
                id_ocurrencia
            ].append(
                fila
            )


        # -----------------------------------------
        # Una fila visual por cliente/ocurrencia
        # -----------------------------------------

        for id_ocurrencia, detalles in (
            self._detalles.items()
        ):
            cabecera = detalles[0]

            iid = (
                f"ocurrencia-{id_ocurrencia}"
            )

            self._ocurrencias[
                iid
            ] = cabecera

            hora = cabecera.get(
                "hora_entrega_sugerida"
            )

            hora_texto = (
                hora.strftime("%H:%M")
                if hora is not None
                else ""
            )

            fecha_entrega = cabecera[
                "fecha_entrega_proyectada"
            ]

            self.grilla.insert(
                "",
                "end",
                iid=iid,
                values=(
                    fecha_entrega.strftime(
                        "%d/%m/%Y"
                    ),
                    cabecera["cliente"],
                    cabecera[
                        "modalidad_entrega"
                    ] or "",
                    hora_texto,
                    len(detalles),
                    cabecera[
                        "direccion_entrega_sugerida"
                    ] or "",
                ),
            )


    # =========================================================
    # SELECCIÓN
    # =========================================================

    def _seleccionar_ocurrencia(
        self,
        _evento=None,
    ) -> None:
        seleccion = (
            self.grilla.selection()
        )

        if not seleccion:
            self._limpiar_seleccion()
            return

        iid = seleccion[0]

        self._seleccion_ocurrencia = (
            self._ocurrencias[iid]
        )

        id_ocurrencia = int(
            self._seleccion_ocurrencia[
                "id_pedido_recurrente_ocurrencia"
            ]
        )

        self._mostrar_detalles(
            id_ocurrencia
        )

        self.btn_omitir.configure(
            state="normal"
        )

        self.btn_revisar.configure(
            state="normal"
        )


    def _mostrar_detalles(
        self,
        id_ocurrencia: int,
    ) -> None:
        for item in self.grilla_detalles.get_children():
            self.grilla_detalles.delete(item)

        detalles = self._detalles.get(
            id_ocurrencia,
            [],
        )

        for indice, fila in enumerate(
            detalles
        ):
            self.grilla_detalles.insert(
                "",
                "end",
                iid=f"detalle-{indice}",
                values=(
                    fila["producto"],
                    formato_cantidad(
                        fila[
                            "cantidad_sugerida"
                        ]
                    ),
                    fila[
                        "observaciones_producto"
                    ] or "",
                ),
            )


    def _limpiar_seleccion(
        self,
    ) -> None:
        self._seleccion_ocurrencia = None

        for item in self.grilla_detalles.get_children():
            self.grilla_detalles.delete(item)

        self.btn_omitir.configure(
            state="disabled"
        )

        self.btn_revisar.configure(
            state="disabled"
        )


    # =========================================================
    # OMITIR
    # =========================================================

    def _omitir(self) -> None:
        if self._seleccion_ocurrencia is None:
            return

        fila = self._seleccion_ocurrencia

        cliente = fila["cliente"]

        id_ocurrencia = int(
            fila[
                "id_pedido_recurrente_ocurrencia"
            ]
        )

        confirmar = messagebox.askyesno(
            "Esta vez no necesita",
            (
                f"Cliente: {cliente}\n"
                f"Entrega prevista: "
                f"{fila['fecha_entrega_proyectada']:%d/%m/%Y}"
                "\n\n"
                "¿Confirmar que esta vez "
                "el cliente no necesita pedido?"
            ),
            parent=self,
        )

        if not confirmar:
            return

        motivo = simpledialog.askstring(
            "Motivo",
            (
                "Observación opcional:\n"
                "por ejemplo, vacaciones, stock propio, "
                "esta semana no necesita, etc."
            ),
            parent=self,
        )

        try:
            omitir_pedido_proyectado(
                id_ocurrencia=id_ocurrencia,
                motivo=motivo,
            )

        except Exception as error:
            messagebox.showerror(
                "Pedidos proyectados",
                "No se pudo omitir la proyección."
                f"\n\n{error}",
                parent=self,
            )
            return

        messagebox.showinfo(
            "Pedidos proyectados",
            (
                f"{cliente}\n\n"
                "La ocurrencia quedó marcada "
                "como OMITIDA."
            ),
            parent=self,
        )

        self._actualizar()


    # =========================================================
    # REVISAR
    # =========================================================

    def _revisar(self) -> None:
        if self._seleccion_ocurrencia is None:
            return

        id_ocurrencia = int(
            self._seleccion_ocurrencia[
                "id_pedido_recurrente_ocurrencia"
            ]
        )

        detalles = [
            dict(fila)
            for fila in self._detalles.get(
                id_ocurrencia,
                [],
            )
        ]

        VentanaRevisarPedidoProyectado(
            self,
            cabecera=dict(
                self._seleccion_ocurrencia
            ),
            detalles=detalles,
            al_guardar=self._pedido_generado,
    )

    def _pedido_generado(
        self,
        _id_pedido: int,
    ) -> None:
        self._actualizar()

 
    