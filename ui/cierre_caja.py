from __future__ import annotations

import tkinter as tk
from decimal import Decimal
from tkinter import messagebox, ttk
from typing import Any
from pathlib import Path

from db.caja_repository import (
    cerrar_caja,
    obtener_datos_cierre_caja,
    obtener_sesion_abierta,
)
from ui.ventana_util import maximizar_ventana
from ui.reporte_cierre_caja import emitir_rendicion_caja


def formato_moneda(valor: Any) -> str:
    numero = Decimal(str(valor or 0))
    texto = f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"$ {texto}"


def convertir_importe(texto: str) -> Decimal:
    limpio = texto.strip().replace("$", "").replace(" ", "")
    if not limpio:
        raise ValueError("Debe indicar un importe.")
    if "," in limpio:
        limpio = limpio.replace(".", "").replace(",", ".")
    return Decimal(limpio)


class VentanaCierreCaja(tk.Toplevel):
    def __init__(self, parent: tk.Misc, navegador=None) -> None:
        super().__init__(parent)
        self.navegador = navegador
        self._tema = getattr(navegador, "tema", "claro")
        self._c = self._obtener_colores_tema()
        self.datos: dict[str, Any] | None = None
        self._declarados: dict[int, tk.StringVar] = {}
        self._diferencias: dict[int, tk.StringVar] = {}
        self._importes_sistema: dict[int, Decimal] = {}
        self._logo_img: tk.PhotoImage | None = None

        self.title("Cerrar Caja - Doña Elina")
        self.resizable(True, True)
        maximizar_ventana(self)
        self.minsize(1050, 650)
        self.configure(bg="#f3f1ef")
        self._crear_interfaz()
        self._cargar_datos()
        self._aplicar_tema()
        self.protocol("WM_DELETE_WINDOW", self._cerrar_ventana)

    def _crear_interfaz(self) -> None:
        c = self._obtener_colores_tema()
        self._c = c
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._crear_sidebar(c)

        contenedor = tk.Frame(self, bg=c["bg"], bd=0)
        contenedor.grid(row=0, column=1, sticky="nsew", padx=26, pady=22)
        contenedor.columnconfigure(0, weight=1)
        contenedor.rowconfigure(2, weight=1)

        encabezado = tk.Frame(contenedor, bg=c["surface"], highlightthickness=1, highlightbackground=c["border"])
        encabezado.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        encabezado.columnconfigure(0, weight=1)
        tk.Label(encabezado, text="Cerrar Caja", font=("Segoe UI", 24, "bold"), fg=c["burgundy"], bg=c["surface"], anchor="w").grid(row=0,column=0,sticky="w",padx=20,pady=(14,2))
        tk.Label(encabezado, text="Controlá los importes y confirmá el cierre de la sesión", font=("Segoe UI",10), fg=c["muted"], bg=c["surface"], anchor="w").grid(row=1,column=0,sticky="w",padx=21,pady=(0,13))
        self.btn_tema=tk.Button(encabezado,text="☾  Modo oscuro",command=self._alternar_tema,font=("Segoe UI",9,"bold"),bd=0,relief="flat",padx=12,pady=7,cursor="hand2",highlightthickness=1,highlightbackground=c["border"],bg=c["surface"],fg=c["text"],activebackground=c["surface2"],activeforeground=c["text"])
        self.btn_tema.grid(row=0,column=1,rowspan=2,sticky="e",padx=(8,4),pady=7)
        btnx=tk.Button(encabezado,text="×",command=self._cerrar_ventana,font=("Segoe UI",18,"bold"),fg=c["muted"],bg=c["surface"],activebackground=c["danger"],activeforeground=c["white"],bd=0,width=3,cursor="hand2")
        btnx.grid(row=0,column=2,rowspan=2,sticky="ne",padx=8,pady=7)
        btnx.bind("<Enter>",lambda _e:btnx.configure(bg=c["danger"],fg=c["white"]))
        btnx.bind("<Leave>",lambda _e:btnx.configure(bg=c["surface"],fg=c["muted"]))

        self.texto_sesion=tk.StringVar(value="Cargando sesión...")
        sesion_frame=tk.Frame(contenedor,bg=c["surface2"],highlightthickness=1,highlightbackground=c["border"])
        sesion_frame.grid(row=1,column=0,sticky="ew",pady=(0,12))
        tk.Label(sesion_frame,text="●",font=("Segoe UI",18,"bold"),fg=c["gold"],bg=c["surface2"]).pack(side="left",padx=(16,10),pady=10)
        tk.Label(sesion_frame,textvariable=self.texto_sesion,font=("Segoe UI",10,"bold"),fg=c["text"],bg=c["surface2"],anchor="w").pack(side="left",fill="x",expand=True,pady=10)

        cuerpo=tk.Frame(contenedor,bg=c["bg"],bd=0)
        cuerpo.grid(row=2,column=0,sticky="nsew")
        cuerpo.grid_propagate(True)
        cuerpo.columnconfigure(0,weight=1)
        cuerpo.rowconfigure(0,weight=1)

        marco=tk.LabelFrame(cuerpo,text="Importes según el sistema",font=("Segoe UI",10,"bold"),fg=c["burgundy"],bg=c["surface"],bd=1,relief="solid",padx=10,pady=8)
        marco.grid(row=0,column=0,sticky="nsew")
        marco.columnconfigure(0,weight=1); marco.rowconfigure(0,weight=1)
        columnas=("medio","saldo_inicial","cobros","movimientos","sistema")
        self.grilla=ttk.Treeview(marco,columns=columnas,show="headings",height=8)
        titulos={"medio":"Medio","saldo_inicial":"Saldo inicial","cobros":"Cobros","movimientos":"Caja chica","sistema":"Total sistema"}
        for col,titulo in titulos.items(): self.grilla.heading(col,text=titulo)
        self.grilla.column("medio",width=210,anchor="w")
        for col in columnas[1:]: self.grilla.column(col,width=145,anchor="e")
        self.grilla.grid(row=0,column=0,sticky="nsew")

        decl=tk.LabelFrame(cuerpo,text="Importes declarados",font=("Segoe UI",10,"bold"),fg=c["burgundy"],bg=c["surface"],bd=1,relief="solid",padx=12,pady=8)
        decl.grid(row=1,column=0,sticky="ew",pady=(12,0))
        for col in range(4): decl.columnconfigure(col,weight=1 if col==2 else 0)
        self.marco_declaraciones=decl
        for texto,col in (("Medio",0),("Sistema",1),("Declarado",2),("Diferencia",3)):
            tk.Label(decl,text=texto,font=("Segoe UI",9,"bold"),fg=c["muted"],bg=c["surface"],anchor="w" if col==0 else "e").grid(row=0,column=col,sticky="ew",padx=7,pady=(0,6))

        obs=tk.LabelFrame(cuerpo,text="Observaciones",font=("Segoe UI",10,"bold"),fg=c["burgundy"],bg=c["surface"],bd=1,relief="solid",padx=12,pady=8)
        obs.grid(row=2,column=0,sticky="ew",pady=(12,0)); obs.columnconfigure(0,weight=1)
        self.txt_observaciones=tk.Entry(obs,font=("Segoe UI",10),bg=c["surface2"],fg=c["text"],relief="solid",bd=1)
        self.txt_observaciones.grid(row=0,column=0,sticky="ew",ipady=6)

        acciones=tk.Frame(cuerpo,bg=c["bg"])
        acciones.grid(row=3,column=0,sticky="e",pady=(12,0))
        self.btn_confirmar=tk.Button(acciones,text="✓  Confirmar cierre",command=self._confirmar_cierre,font=("Segoe UI",10,"bold"),bg=c["burgundy"],fg=c["white"],activebackground=c["burgundy"],activeforeground=c["white"],bd=0,padx=18,pady=9,cursor="hand2")
        self.btn_confirmar.pack(side="left",padx=(0,8))
        tk.Button(acciones,text="Cerrar ventana",command=self._cerrar_ventana,font=("Segoe UI",10,"bold"),bg=c["surface"],fg=c["text"],activebackground=c["surface2"],bd=0,padx=16,pady=9,cursor="hand2").pack(side="left")

        style=ttk.Style(self)
        try: style.theme_use("clam")
        except tk.TclError: pass
        style.configure("Treeview",background=c["surface"],foreground=c["text"],fieldbackground=c["surface"],rowheight=30,font=("Segoe UI",9),bordercolor=c["border"])
        style.configure("Treeview.Heading",background=c["burgundy"],foreground=c["white"],font=("Segoe UI",9,"bold"),relief="flat")
        style.map("Treeview",background=[("selected",c["sidebar_hover"])],foreground=[("selected",c["white"])])

    def _crear_sidebar(self,c):
        sidebar=tk.Frame(self,bg=c["sidebar"],width=245); sidebar.grid(row=0,column=0,sticky="ns"); sidebar.grid_propagate(False)
        box=tk.Frame(sidebar,bg=c["logo_bg"]); box.pack(fill="x",padx=14,pady=(16,14))
        ruta=Path(__file__).resolve().parent.parent/"assets"/"logo_dona_elina.png"
        try:
            self._logo_img=tk.PhotoImage(file=str(ruta))
            if self._logo_img.width()>215:
                self._logo_img=self._logo_img.subsample(max(1,self._logo_img.width()//215))
            tk.Label(box,image=self._logo_img,bg=c["logo_bg"],bd=0).pack(padx=8,pady=8)
        except Exception:
            tk.Label(box,text="Doña Elina",font=("Segoe Script",24,"bold"),fg=c["burgundy"],bg=c["logo_bg"]).pack(pady=25)
        tk.Label(sidebar,text="ACCESOS RÁPIDOS",font=("Segoe UI",10,"bold"),fg=c["gold"],bg=c["sidebar"],anchor="w").pack(fill="x",padx=24,pady=(4,7))
        tk.Frame(sidebar,height=1,bg=c["gold"]).pack(fill="x",padx=24)
        opciones=(("+","Nuevo pedido",lambda:self.navegador.abrir_pedido(self)),("☷","Lista de precios",lambda:self.navegador.abrir_reporte_precios(self)),("▰","Salidas y Entregas",lambda:self.navegador.abrir_salidas(self)),("⚙","Configuración",lambda:messagebox.showinfo("Configuración","Esta función se mantiene para el próximo módulo.",parent=self)))
        for icono,texto,cmd in opciones: self._menu_button(sidebar,icono,texto,cmd,c)
        tk.Frame(sidebar,height=1,bg=c["gold"]).pack(fill="x",padx=24,pady=(10,8))
        self._menu_button(sidebar,"‹","Volver a Caja",self._cerrar_ventana,c)
        self._menu_button(sidebar,"×","Salir",self._salir,c)
        tk.Label(sidebar,text="Doña Elina - Sistema de Gestión\nVersión 1.0.0",font=("Segoe UI",7),fg=c["gold"],bg=c["sidebar"],anchor="w",justify="left").pack(side="bottom",fill="x",padx=20,pady=12)

    def _menu_button(self,parent,icono,texto,comando,c):
        b=tk.Button(parent,text=f"  {icono}   {texto}",command=comando,anchor="w",font=("Segoe UI",10,"bold"),bg=c["sidebar"],fg=c["white"],activebackground=c["sidebar_hover"],activeforeground=c["white"],bd=0,relief="flat",padx=14,pady=9,cursor="hand2")
        b.pack(fill="x",padx=12,pady=2)
        b.configure(overrelief="flat",takefocus=0)
        def _entrar(_event=None):
            try: b.configure(bg=self._obtener_colores_tema()["sidebar_hover"])
            except tk.TclError: pass
        def _salir(_event=None):
            try: b.configure(bg=self._obtener_colores_tema()["sidebar"])
            except tk.TclError: pass
        b.bind("<Enter>",_entrar,add="+")
        b.bind("<Leave>",_salir,add="+")

    def _cerrar_ventana(self):
        if self.navegador is not None:
            self.navegador.volver_menu(self)
        else:
            self.destroy()

    def _salir(self):
        self.destroy()

    def _obtener_colores_tema(self) -> dict[str,str]:
        if self._tema == "oscuro":
            return {"bg":"#15171b","surface":"#24282e","surface2":"#292e35","border":"#363c44","text":"#f3f4f6","muted":"#aeb5bf","sidebar":"#321019","sidebar_hover":"#4a1723","gold":"#d5a63a","burgundy":"#c13b58","danger":"#e05b68","success":"#55bd69","white":"#ffffff","logo_bg":"#fff8f8"}
        return {"bg":"#f3f1ef","surface":"#ffffff","surface2":"#faf8f7","border":"#ddd7d4","text":"#252328","muted":"#6d6870","sidebar":"#3a111b","sidebar_hover":"#511522","gold":"#c99624","burgundy":"#9f1230","danger":"#c94b57","success":"#3caa55","white":"#ffffff","logo_bg":"#fff9f9"}

    def _alternar_tema(self) -> None:
        self._tema = "oscuro" if self._tema == "claro" else "claro"
        if self.navegador is not None: self.navegador.tema = self._tema
        self._aplicar_tema()

    def _aplicar_tema(self) -> None:
        """Aplica el tema por rol de color, evitando colisiones como blanco=surface y blanco=texto."""
        nuevo = self._obtener_colores_tema()
        viejo = self._c

        # No usamos un diccionario color->color global porque, en claro,
        # ``surface`` y ``white`` pueden tener el mismo valor (#ffffff).
        # Eso hacía que los paneles quedaran blancos al pasar a oscuro.
        def convertir(opcion: str, valor: str) -> str | None:
            if opcion in ("bg", "background", "activebackground", "highlightbackground", "highlightcolor"):
                prioridades = (
                    "surface_alt", "surface", "bg", "panel",
                    "surface2", "sidebar_hover", "sidebar", "logo_bg",
                    "border", "burgundy", "gold", "danger", "success",
                )
            else:
                prioridades = (
                    "text", "muted", "burgundy", "gold", "danger",
                    "success", "white", "blue", "purple",
                )

            for clave in prioridades:
                if clave in viejo and valor == viejo[clave]:
                    return nuevo.get(clave, valor)
            return None

        def recorrer(w):
            try:
                for op in (
                    "bg", "background", "fg", "foreground",
                    "activebackground", "activeforeground",
                    "highlightbackground", "highlightcolor",
                    "insertbackground", "selectbackground",
                    "selectforeground",
                ):
                    try:
                        valor = w.cget(op)
                    except (tk.TclError, KeyError):
                        continue
                    nuevo_valor = convertir(op, valor)
                    if nuevo_valor is not None:
                        try:
                            w.configure(**{op: nuevo_valor})
                        except tk.TclError:
                            pass
                for h in w.winfo_children():
                    recorrer(h)
            except tk.TclError:
                pass

        recorrer(self)
        self._c = nuevo

        try:
            style = ttk.Style(self)
            style.theme_use("clam")
            style.configure(
                "Treeview",
                background=nuevo["surface"],
                foreground=nuevo["text"],
                fieldbackground=nuevo["surface"],
                bordercolor=nuevo["border"],
            )
            style.configure(
                "Treeview.Heading",
                background=nuevo["burgundy"],
                foreground=nuevo["white"],
            )
            style.map(
                "Treeview",
                background=[("selected", nuevo["sidebar_hover"])],
                foreground=[("selected", nuevo["white"])],
            )
            style.configure("TLabel", background=nuevo["surface"], foreground=nuevo["text"])
            style.configure("TEntry", fieldbackground=nuevo["surface2"], foreground=nuevo["text"])
        except tk.TclError:
            pass

        self.btn_tema.configure(
            text="☾  Modo oscuro" if self._tema == "claro" else "☀  Modo claro",
            bg=nuevo["surface"],
            fg=nuevo["text"],
            activebackground=nuevo["surface_alt"],
            activeforeground=nuevo["text"],
            highlightbackground=nuevo["border"],
        )
        self.configure(bg=nuevo["bg"])

    def _cargar_datos(self) -> None:
        try:
            sesion = obtener_sesion_abierta()

            if sesion is None:
                raise RuntimeError(
                    "No hay una sesión de caja abierta."
                )

            id_sesion = int(
                sesion["id_caja_sesion"]
            )

            self.datos = (
                obtener_datos_cierre_caja(
                    id_sesion
                )
            )

        except Exception as error:
            messagebox.showerror(
                "Cierre de caja",
                (
                    "No se pudieron cargar "
                    "los datos de cierre."
                    f"\n\n{error}"
                ),
                parent=self,
            )
            return

        datos_sesion = self.datos["sesion"]

        self.texto_sesion.set(
            f"{datos_sesion['caja_descripcion']} · "
            f"Sesión {datos_sesion['id_caja_sesion']} · "
            f"Apertura: {datos_sesion['fecha_apertura']} · "
            f"Saldo inicial: "
            f"{formato_moneda(datos_sesion['saldo_inicial'])}"
        )

        for medio in self.datos["medios"]:
            self.grilla.insert(
                "",
                "end",
                values=(
                    medio["descripcion"],
                    formato_moneda(
                        medio["saldo_inicial"]
                    ),
                    formato_moneda(
                        medio["cobros"]
                    ),
                    formato_moneda(
                        medio["movimientos_caja"]
                    ),
                    formato_moneda(
                        medio["importe_sistema"]
                    ),
                ),
            )

        self._cargar_declaraciones()

    def _cargar_declaraciones(self) -> None:
        if self.datos is None:
            return

        self._declarados.clear()
        self._diferencias.clear()
        self._importes_sistema.clear()

        for indice, medio in enumerate(
            self.datos["medios"],
            start=1,
        ):
            id_medio = int(
                medio["id_medio_pago"]
            )

            importe_sistema = Decimal(
                str(
                    medio["importe_sistema"]
                )
            )

            self._importes_sistema[
                id_medio
            ] = importe_sistema

            variable_declarado = tk.StringVar(
                value=""
            )

            variable_diferencia = tk.StringVar(
                value="—"
            )

            self._declarados[
                id_medio
            ] = variable_declarado

            self._diferencias[
                id_medio
            ] = variable_diferencia


            tk.Label(
                self.marco_declaraciones,
                text=medio["descripcion"],
                font=("Segoe UI", 9),
                fg=self._c["text"],
                bg=self._c["surface"],
            ).grid(
                row=indice,
                column=0,
                sticky="w",
                padx=(0, 12),
                pady=3,
            )


            tk.Label(
                self.marco_declaraciones,
                text=formato_moneda(
                    importe_sistema
                ),
                font=("Segoe UI", 9),
                fg=self._c["text"],
                bg=self._c["surface"],
            ).grid(
                row=indice,
                column=1,
                sticky="e",
                padx=(0, 12),
                pady=3,
            )


            entrada = tk.Entry(
                self.marco_declaraciones,
                textvariable=variable_declarado,
                width=18,
                justify="right",
                font=("Segoe UI", 9),
                bg=self._c["surface2"],
                fg=self._c["text"],
                insertbackground=self._c["text"],
                relief="solid",
                bd=1,
            )
            entrada.grid(
                row=indice,
                column=2,
                sticky="e",
                padx=(0, 12),
                pady=3,
            )

            entrada.bind(
                "<KeyRelease>",
                lambda _evento,
                medio_id=id_medio:
                    self._actualizar_diferencia(
                        medio_id
                    ),
            )


            tk.Label(
                self.marco_declaraciones,
                textvariable=variable_diferencia,
                width=18,
                anchor="e",
                font=("Segoe UI", 9),
                fg=self._c["text"],
                bg=self._c["surface"],
            ).grid(
                row=indice,
                column=3,
                sticky="e",
                pady=3,
            )


    def _actualizar_diferencia(
        self,
        id_medio_pago: int,
    ) -> None:
        variable = self._declarados.get(
            id_medio_pago
        )

        variable_diferencia = (
            self._diferencias.get(
                id_medio_pago
            )
        )

        importe_sistema = (
            self._importes_sistema.get(
                id_medio_pago
            )
        )

        if (
            variable is None
            or variable_diferencia is None
            or importe_sistema is None
        ):
            return

        texto = variable.get().strip()

        if not texto:
            variable_diferencia.set(
                "—"
            )
            return

        try:
            declarado = convertir_importe(
                texto
            )

            if declarado < 0:
                raise ValueError

        except Exception:
            variable_diferencia.set(
                "Importe inválido"
            )
            return

        diferencia = (
            declarado
            - importe_sistema
        )

        variable_diferencia.set(
            formato_moneda(
                diferencia
            )
        )

    def _confirmar_cierre(self) -> None:
        if self.datos is None:
            return

        declaraciones: list[
            dict[str, Any]
        ] = []

        hay_diferencia = False

        # =========================================================
        # Validamos los importes declarados
        # =========================================================

        for medio in self.datos["medios"]:
            id_medio = int(
                medio["id_medio_pago"]
            )

            variable = self._declarados.get(
                id_medio
            )

            if variable is None:
                continue

            texto = variable.get().strip()

            if not texto:
                messagebox.showwarning(
                    "Cierre de caja",
                    (
                        "Debe declarar el importe de "
                        f"{medio['descripcion']}."
                    ),
                    parent=self,
                )
                return

            try:
                importe_declarado = (
                    convertir_importe(
                        texto
                    )
                )

            except Exception:
                messagebox.showwarning(
                    "Cierre de caja",
                    (
                        "El importe declarado para "
                        f"{medio['descripcion']} "
                        "no es válido."
                    ),
                    parent=self,
                )
                return

            if importe_declarado < 0:
                messagebox.showwarning(
                    "Cierre de caja",
                    (
                        "El importe declarado para "
                        f"{medio['descripcion']} "
                        "no puede ser negativo."
                    ),
                    parent=self,
                )
                return

            importe_sistema = Decimal(
                str(
                    medio[
                        "importe_sistema"
                    ]
                )
            )

            diferencia = (
                importe_declarado
                - importe_sistema
            )

            if abs(diferencia) >= Decimal(
                "0.01"
            ):
                hay_diferencia = True

            declaraciones.append(
                {
                    "id_medio_pago":
                        id_medio,

                    "importe_declarado":
                        importe_declarado,
                }
            )

        # =========================================================
        # Observaciones
        # =========================================================

        observaciones = (
            self.txt_observaciones
            .get()
            .strip()
            or None
        )

        # =========================================================
        # Diferencias: oportunidad de revisar Caja chica
        # =========================================================

        if hay_diferencia:
            revisar_caja_chica = messagebox.askyesno(
                "Caja con diferencias",
                (
                    "La caja presenta diferencias entre "
                    "los importes del sistema y los "
                    "importes declarados.\n\n"
                    "Es posible que falte registrar algún "
                    "movimiento de Caja chica.\n\n"
                    "¿Desea revisar Caja chica antes "
                    "de continuar con el cierre?\n\n"
                    "Sí: ir a Caja chica.\n"
                    "No: continuar con el cierre."
                ),
                parent=self,
            )

            if revisar_caja_chica:
                if self.navegador is not None:
                    self.navegador.abrir_caja_chica(
                        self
                    )
                else:
                    messagebox.showinfo(
                        "Cierre de caja",
                        (
                            "Ingrese a Caja chica para revisar "
                            "los movimientos antes de cerrar."
                        ),
                        parent=self,
                    )

                return

            # Si decidió cerrar igualmente con diferencia,
            # la observación pasa a ser obligatoria.
            if observaciones is None:
                messagebox.showwarning(
                    "Cierre de caja",
                    (
                        "La caja presenta diferencias.\n\n"
                        "Para continuar con el cierre debe "
                        "indicar una observación."
                    ),
                    parent=self,
                )

                self.txt_observaciones.focus_set()
                return

            mensaje = (
                "La caja presenta diferencias entre "
                "los importes del sistema y los "
                "importes declarados.\n\n"
                "El cierre quedará registrado "
                "CON DIFERENCIA.\n\n"
                "Observación:\n"
                f"{observaciones}\n\n"
                "¿Confirma el cierre de caja?"
            )

        else:
            mensaje = (
                "Todos los importes declarados "
                "coinciden con el sistema.\n\n"
                "La caja quedará cerrada.\n\n"
                "¿Confirma el cierre de caja?"
            )

        confirmar = messagebox.askyesno(
            "Confirmar cierre",
            mensaje,
            parent=self,
        )

        if not confirmar:
            return

        # =========================================================
        # Cerramos
        # =========================================================

        self.btn_confirmar.configure(
            state="disabled",
        )

        try:
            resultado = cerrar_caja(
                id_caja_sesion=int(
                    self.datos[
                        "sesion"
                    ][
                        "id_caja_sesion"
                    ]
                ),

                declaraciones=
                    declaraciones,

                permitir_diferencia=
                    hay_diferencia,

                observaciones=
                    observaciones,
            )

        except Exception as error:
            self.btn_confirmar.configure(
                state="normal",
            )

            messagebox.showerror(
                "Cierre de caja",
                (
                    "No se pudo cerrar la caja."
                    f"\n\n{error}"
                ),
                parent=self,
            )
            return

        # =========================================================
        # Resultado
        # =========================================================

        messagebox.showinfo(
            "Caja cerrada",
            (
                "Caja cerrada correctamente."
                "\n\n"
                "Estado: "
                f"{resultado['estado_cierre']}\n"
                "Total sistema: "
                f"{formato_moneda(
                    resultado['total_sistema']
                )}\n"
                "Total declarado: "
                f"{formato_moneda(
                    resultado['total_declarado']
                )}\n"
                "Diferencia: "
                f"{formato_moneda(
                    resultado['diferencia_neta']
                )}"
            ),
            parent=self,
        )

        try:
            emitir_rendicion_caja(
                int(
                    self.datos[
                        "sesion"
                    ][
                        "id_caja_sesion"
                    ]
                )
            )

        except Exception as error:
            messagebox.showwarning(
                "Rendición de caja",
                (
                    "La caja fue cerrada correctamente, "
                    "pero no se pudo emitir la rendición."
                    f"\n\n{error}"
                ),
                parent=self,
            )

        # Actualizamos el estado del menú principal.
        actualizar_estado = getattr(
            self.master,
            "_actualizar_estado_caja",
            None,
        )

        if callable(actualizar_estado):
            actualizar_estado()

        if self.navegador is not None:
            self.navegador.volver_menu(
                self
            )
        else:
            self.destroy()