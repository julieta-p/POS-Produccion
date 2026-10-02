from pathlib import Path
import py_compile
import zipfile

BASE = Path(__file__).resolve().parent
required = [
    BASE / "app.py",
    BASE / "config.ini",
    BASE / "db" / "conexion.py",
    BASE / "db" / "cobro_repository.py",
    BASE / "ui" / "estado_cuenta.py",
    BASE / "assets" / "logo_dona_elina.png",
]

for p in required:
    if not p.exists():
        raise SystemExit(f"FALTA: {p.relative_to(BASE)}")

for p in BASE.rglob("*.py"):
    py_compile.compile(str(p), doraise=True)

estado = (BASE / "ui" / "estado_cuenta.py").read_text(encoding="utf-8")
cobro = (BASE / "db" / "cobro_repository.py").read_text(encoding="utf-8")

checks = [
    ("obtener_resumen_venta" in cobro, "resumen de venta"),
    ("vw_VentaSaldo" in cobro, "vista saldo de venta"),
    ("REMITO / DETALLE DE VENTA" in estado, "remito estado de cuenta"),
    ("Imprimir / Guardar PDF" in estado, "boton imprimir guardar PDF"),
    ("saldo_actual_cliente" in estado, "saldo actual cliente"),
    ("obtener_detalle_venta" in estado, "detalle de venta"),
    ("ventas.dbo" not in estado and "ventas.dbo" not in cobro, "sin dependencia ventas.dbo"),
    ("PENDIENTE DE PAGO" not in estado and "VENTA CANCELADA" not in estado, "remito sin estados textuales"),
    ("ORDER BY\n                fecha_hora DESC" in (BASE / "db" / "estado_cuenta_repository.py").read_text(encoding="utf-8"), "movimientos recientes primero"),
]

for ok, label in checks:
    if not ok:
        raise SystemExit(f"FALTA CHECK: {label}")

print("KIT_VALIDO")
print("CONFIG_EXTERNA_OK")
print("REMITO_VENTA_OK")
print("IMPRESION_PDF_OK")
print("SIN_VENTAS_DBO_OK")
