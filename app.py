from __future__ import annotations

from tkinter import messagebox

from ui.ventana_principal import VentanaPrincipal


def main() -> None:
    try:
        aplicacion = VentanaPrincipal()
        aplicacion.mainloop()

    except Exception as error:
        messagebox.showerror(
            "Punto de Venta",
            f"No se pudo iniciar la aplicación.\n\n{error}",
        )


if __name__ == "__main__":
    main()