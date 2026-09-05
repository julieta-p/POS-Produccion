from __future__ import annotations

import ast
from pathlib import Path
import shutil

ARCHIVO = Path("ui/salida_pedido.py")


def _reemplazar_llamadas(texto: str) -> str:
    arbol = ast.parse(texto)
    lineas = texto.splitlines(keepends=True)

    offsets = []
    total = 0
    for linea in lineas:
        offsets.append(total)
        total += len(linea)

    cambios: list[tuple[int, int, str]] = []

    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue

        if not isinstance(nodo.func, ast.Name):
            continue

        nombre = nodo.func.id
        if nombre not in {"formato_decimal", "convertir_decimal"}:
            continue

        decimales = None
        for kw in nodo.keywords:
            if kw.arg == "decimales" and isinstance(kw.value, ast.Constant):
                decimales = kw.value.value
                break

        if decimales != 3 or not nodo.args:
            continue

        argumento = ast.get_source_segment(texto, nodo.args[0])
        if argumento is None:
            continue

        nuevo_nombre = (
            "formato_cantidad"
            if nombre == "formato_decimal"
            else "convertir_cantidad"
        )

        inicio = offsets[nodo.lineno - 1] + nodo.col_offset
        fin = offsets[nodo.end_lineno - 1] + nodo.end_col_offset
        cambios.append((inicio, fin, f"{nuevo_nombre}({argumento})"))

    for inicio, fin, reemplazo in sorted(cambios, reverse=True):
        texto = texto[:inicio] + reemplazo + texto[fin:]

    return texto


def main() -> None:
    if not ARCHIVO.exists():
        raise SystemExit(
            "No encontré ui/salida_pedido.py. "
            "Ejecutá este script desde la carpeta raíz del POS."
        )

    texto = ARCHIVO.read_text(encoding="utf-8")

    import_viejo = """from ui.pedido import (\n    convertir_decimal,\n    formato_decimal,\n)"""
    import_nuevo = """from ui.pedido import (\n    convertir_cantidad,\n    convertir_decimal,\n    formato_cantidad,\n    formato_decimal,\n)"""

    if import_viejo in texto:
        texto = texto.replace(import_viejo, import_nuevo, 1)
    elif "convertir_cantidad" not in texto or "formato_cantidad" not in texto:
        raise SystemExit(
            "No pude reconocer el bloque de importación de ui.pedido. "
            "No modifiqué el archivo."
        )

    # Al cargar un pedido, ninguna cantidad queda marcada para entregar
    # hasta que el operador la indique o use 'Todo pendiente'.
    bloque_inicial_viejo = """                pendiente = numero(\n                    fila[\"cantidad_pendiente\"]\n                )\n\n                self._cantidades[id_detalle] = (\n                    pendiente\n                )"""
    bloque_inicial_nuevo = """                self._cantidades[id_detalle] = (\n                    Decimal(\"0\")\n                )"""

    if bloque_inicial_viejo in texto:
        texto = texto.replace(
            bloque_inicial_viejo,
            bloque_inicial_nuevo,
            1,
        )

    # Al seleccionar un producto, el cuadro de ingreso queda vacío.
    seleccion_vieja = """        id_detalle = int(\n            fila[\"id_pedido_detalle\"]\n        )\n\n        cantidad = self._cantidades.get(\n            id_detalle,\n            Decimal(\"0\"),\n        )\n\n        self.txt_cantidad.delete(0, \"end\")\n        self.txt_cantidad.insert(\n            0,\n            formato_decimal(\n                cantidad,\n                decimales=3,\n            ),\n        )"""
    seleccion_nueva = """        self.txt_cantidad.delete(0, \"end\")"""

    if seleccion_vieja in texto:
        texto = texto.replace(
            seleccion_vieja,
            seleccion_nueva,
            1,
        )

    texto = _reemplazar_llamadas(texto)

    # Validamos que ya no queden formatos/entradas de cantidades a 3 decimales.
    arbol = ast.parse(texto)
    pendientes = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call) or not isinstance(nodo.func, ast.Name):
            continue
        if nodo.func.id not in {"formato_decimal", "convertir_decimal"}:
            continue
        for kw in nodo.keywords:
            if (
                kw.arg == "decimales"
                and isinstance(kw.value, ast.Constant)
                and kw.value.value == 3
            ):
                pendientes.append(nodo.lineno)

    if pendientes:
        raise SystemExit(
            "Quedaron cantidades a 3 decimales en las líneas: "
            + ", ".join(map(str, pendientes))
            + ". No modifiqué el archivo."
        )

    backup = ARCHIVO.with_suffix(".py.bak_cantidades")
    if not backup.exists():
        shutil.copy2(ARCHIVO, backup)

    ARCHIVO.write_text(texto, encoding="utf-8")
    print("OK: cantidades de Salidas y entregas actualizadas.")
    print(f"Backup: {backup}")


if __name__ == "__main__":
    main()
