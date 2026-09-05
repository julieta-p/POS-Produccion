from __future__ import annotations

import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk
from typing import Callable

from db.caja_repository import (
    abrir_caja,
    listar_cajas_activas,
)


def convertir_importe(texto: str) -> Decimal:
    """
    Acepta formatos habituales:

    1000
    1000,50
    1000.50
    1.000,50
    """

    valor = texto.strip().replace(" ", "")

    if not valor:
        return Decimal("0")

    if "," in valor and "." in valor:
        valor = valor.replace(".", "")
        valor = valor.replace(",", ".")

    elif "," in valor:
        valor = valor.replace(",", ".")

    try:
        return Decimal(valor).quantize(
            Decimal("0.01")
        )

    except InvalidOperation as error:
        raise ValueError(
            "El saldo inicial no contiene un importe válido."
        ) from error


class VentanaAperturaCaja(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        al_abrir: Callable[[int], None],
    ) -> None:
        super().__init__(parent)

        self._al_abrir = al_abrir
        self._cajas_por_texto: dict[str, int] = {}

        self._ancho_pantalla = (
            self.winfo_screenwidth()
        )

        self._alto_pantalla = (
            self.winfo_screenheight()
        )

        self._pantalla_compacta = (
            self._ancho_pantalla < 900
            or self._alto_pantalla < 650
        )

        self.title("Abrir caja")
        self.transient(parent)
        self.resizable(True, True)

        self._ajustar_tamano_inicial(
            parent
        )

        self._crear_interfaz()
        self._cargar_cajas()

        self.grab_set()

        self.bind(
            "<Escape>",
            lambda _evento: self.destroy(),
        )

        self.bind(
            "<Control-Return>",
            lambda _evento: self._confirmar(),
        )

    def _ajustar_tamano_inicial(
        self,
        parent: tk.Misc,
    ) -> None:
        ancho = int(
            self._ancho_pantalla * 0.42
        )

        alto_disponible = max(
            self._alto_pantalla - 70,
            420,
        )

        alto = int(
            alto_disponible * 0.58
        )

        ancho = min(
            max(ancho, 420),
            620,
            self._ancho_pantalla - 30,
        )

        alto = min(
            max(alto, 360),
            520,
            self._alto_pantalla - 60,
        )

        self.minsize(
            min(390, ancho),
            min(340, alto),
        )

        parent.update_idletasks()

        if parent.winfo_viewable():
            x = (
                parent.winfo_rootx()
                + (
                    parent.winfo_width()
                    - ancho
                ) // 2
            )

            y = (
                parent.winfo_rooty()
                + (
                    parent.winfo_height()
                    - alto
                ) // 2
            )

        else:
            x = (
                self._ancho_pantalla
                - ancho
            ) // 2

            y = (
                self._alto_pantalla
                - alto
            ) // 2

        self.geometry(
            f"{ancho}x{alto}"
            f"+{max(x, 0)}"
            f"+{max(y, 0)}"
        )
    def _crear_interfaz(self) -> None:
        padding = (
            14
            if self._pantalla_compacta
            else 20
        )

        contenedor = ttk.Frame(
            self,
            padding=padding,
        )
        contenedor.pack(
            fill="both",
            expand=True,
        )

        contenedor.columnconfigure(
            0,
            weight=1,
        )

        # Observaciones absorbe el alto sobrante.
        contenedor.rowconfigure(
            6,
            weight=1,
        )

        ttk.Label(
            contenedor,
            text="Apertura de caja",
            font=("Segoe UI", 17, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 14),
        )

        ttk.Label(
            contenedor,
            text="Caja",
        ).grid(
            row=1,
            column=0,
            sticky="w",
        )

        self.cbo_caja = ttk.Combobox(
            contenedor,
            state="readonly",
        )
        self.cbo_caja.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(4, 12),
        )

        ttk.Label(
            contenedor,
            text="Saldo inicial",
        ).grid(
            row=3,
            column=0,
            sticky="w",
        )

        self.txt_saldo = ttk.Entry(
            contenedor,
            justify="right",
        )
        self.txt_saldo.insert(
            0,
            "0,00",
        )
        self.txt_saldo.grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(4, 12),
        )

        ttk.Label(
            contenedor,
            text="Observaciones",
        ).grid(
            row=5,
            column=0,
            sticky="w",
        )

        marco_observaciones = ttk.Frame(
            contenedor
        )
        marco_observaciones.grid(
            row=6,
            column=0,
            sticky="nsew",
            pady=(4, 14),
        )

        marco_observaciones.columnconfigure(
            0,
            weight=1,
        )
        marco_observaciones.rowconfigure(
            0,
            weight=1,
        )

        self.txt_observaciones = tk.Text(
            marco_observaciones,
            height=(
                4
                if self._pantalla_compacta
                else 6
            ),
            wrap="word",
            font=("Segoe UI", 10),
        )
        self.txt_observaciones.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        barra = ttk.Scrollbar(
            marco_observaciones,
            orient="vertical",
            command=self.txt_observaciones.yview,
        )
        barra.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.txt_observaciones.configure(
            yscrollcommand=barra.set
        )

        botones = ttk.Frame(
            contenedor
        )
        botones.grid(
            row=7,
            column=0,
            sticky="e",
        )

        ttk.Button(
            botones,
            text="Abrir caja",
            command=self._confirmar,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            botones,
            text="Cancelar",
            command=self.destroy,
        ).pack(
            side="left",
        )

        self.cbo_caja.bind(
            "<Return>",
            lambda _evento:
                self.txt_saldo.focus_set(),
        )

        self.txt_saldo.bind(
            "<Return>",
            lambda _evento:
                self._confirmar(),
        )
    
    

    def _cargar_cajas(self) -> None:
        try:
            cajas = listar_cajas_activas()

        except Exception as error:
            messagebox.showerror(
                "Abrir caja",
                "No se pudieron recuperar las cajas.\n\n"
                f"{error}",
                parent=self,
            )
            self.destroy()
            return

        if not cajas:
            messagebox.showwarning(
                "Abrir caja",
                "No hay cajas activas configuradas.",
                parent=self,
            )
            self.destroy()
            return

        valores: list[str] = []

        for caja in cajas:
            id_caja = int(caja["id_caja"])
            descripcion = str(caja["descripcion"])

            texto = f"{id_caja} - {descripcion}"

            valores.append(texto)
            self._cajas_por_texto[texto] = id_caja

        self.cbo_caja.configure(values=valores)

        if len(valores) == 1:
            self.cbo_caja.set(valores[0])

        self.cbo_caja.focus_set()

    def _confirmar(self) -> None:
        seleccion = self.cbo_caja.get().strip()

        if not seleccion:
            messagebox.showwarning(
                "Abrir caja",
                "Debe seleccionar una caja.",
                parent=self,
            )
            self.cbo_caja.focus_set()
            return

        try:
            saldo_inicial = convertir_importe(
                self.txt_saldo.get()
            )

            if saldo_inicial < 0:
                raise ValueError(
                    "El saldo inicial no puede ser negativo."
                )

            observaciones = self.txt_observaciones.get(
                "1.0",
                "end-1c",
            ).strip()

            id_sesion = abrir_caja(
                id_caja=self._cajas_por_texto[seleccion],
                saldo_inicial=saldo_inicial,
                observaciones=observaciones or None,
            )

        except Exception as error:
            messagebox.showerror(
                "Abrir caja",
                "No se pudo abrir la caja.\n\n"
                f"{error}",
                parent=self,
            )
            return

        messagebox.showinfo(
            "Abrir caja",
            "Caja abierta correctamente.\n\n"
            f"Sesión: {id_sesion}",
            parent=self,
        )

        self._al_abrir(id_sesion)
        self.destroy()

