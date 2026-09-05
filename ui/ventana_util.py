from __future__ import annotations

import tkinter as tk


def maximizar_ventana(
    ventana: tk.Toplevel | tk.Tk,
) -> None:
    """
    Maximiza la ventana cuando ya fue dibujada.

    En Windows, el estado 'zoomed' respeta el área
    disponible y evita quedar detrás de la barra
    de tareas.
    """

    def aplicar() -> None:
        try:
            ventana.state("zoomed")

        except tk.TclError:
            # Respaldo para entornos donde 'zoomed'
            # no esté disponible.
            ancho = ventana.winfo_screenwidth()
            alto = ventana.winfo_screenheight()

            ventana.geometry(
                f"{ancho}x{alto}+0+0"
            )

    ventana.after_idle(aplicar)