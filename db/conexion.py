from __future__ import annotations

import configparser
from pathlib import Path
from typing import Any

import pyodbc


# Carpeta principal del proyecto:
# E:\Users\Seba\Laboral\000 Fábrica\BASE\Punto de Venta\POS
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.ini"


class ErrorConfiguracion(Exception):
    """Error en el archivo de configuración."""


def cargar_configuracion() -> configparser.SectionProxy:
    """Lee y valida la sección [sqlserver] de config.ini."""

    config = configparser.ConfigParser()

    if not CONFIG_PATH.exists():
        raise ErrorConfiguracion(
            f"No se encontró el archivo: {CONFIG_PATH}"
        )

    config.read(CONFIG_PATH, encoding="utf-8")

    if "sqlserver" not in config:
        raise ErrorConfiguracion(
            "El archivo config.ini no contiene la sección [sqlserver]."
        )

    return config["sqlserver"]


def construir_cadena_conexion() -> str:
    """Construye la cadena ODBC para SQL Server."""

    sql_config = cargar_configuracion()

    driver = sql_config.get("driver", "").strip()
    server = sql_config.get("server", "").strip()
    database = sql_config.get("database", "").strip()
    user = sql_config.get("user", "").strip()
    password = sql_config.get("password", "")

    if not driver:
        raise ErrorConfiguracion(
            "Falta indicar driver en config.ini."
        )

    if not server:
        raise ErrorConfiguracion(
            "Falta indicar server en config.ini."
        )

    if not database:
        raise ErrorConfiguracion(
            "Falta indicar database en config.ini."
        )

    trusted_connection = sql_config.get(
        "trusted_connection",
        "yes",
    ).strip()

    encrypt = sql_config.get(
        "encrypt",
        "yes",
    ).strip()

    trust_server_certificate = sql_config.get(
        "trust_server_certificate",
        "yes",
    ).strip()

    cadena = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"Trusted_Connection={trusted_connection};"
        f"Encrypt={encrypt};"
        f"TrustServerCertificate={trust_server_certificate};"
    )

    if trusted_connection.lower() not in {"yes", "true", "1"}:
        if not user:
            raise ErrorConfiguracion(
                "Falta indicar user en config.ini para autenticación SQL Server."
            )
        if not password:
            raise ErrorConfiguracion(
                "Falta indicar password en config.ini para autenticación SQL Server."
            )
        cadena += f"UID={user};PWD={password};"

    return cadena


def abrir_conexion(
    *,
    autocommit: bool = False,
) -> pyodbc.Connection:
    """Abre una conexión con SQL Server."""

    cadena_conexion = construir_cadena_conexion()

    try:
        return pyodbc.connect(
            cadena_conexion,
            autocommit=autocommit,
            timeout=10,
        )

    except pyodbc.Error as error:
        raise ConnectionError(
            f"No se pudo conectar con SQL Server: {error}"
        ) from error


def probar_conexion() -> dict[str, Any]:
    """Devuelve información básica de la conexión actual."""

    conexion: pyodbc.Connection | None = None

    try:
        conexion = abrir_conexion()
        cursor = conexion.cursor()

        fila = cursor.execute(
            """
            SELECT
                @@SERVERNAME AS servidor,
                DB_NAME() AS base_datos,
                SUSER_SNAME() AS usuario_sql,
                SYSDATETIME() AS fecha_servidor;
            """
        ).fetchone()

        if fila is None:
            raise ConnectionError(
                "SQL Server no devolvió información."
            )

        return {
            "servidor": fila.servidor,
            "base_datos": fila.base_datos,
            "usuario_sql": fila.usuario_sql,
            "fecha_servidor": fila.fecha_servidor,
        }

    finally:
        if conexion is not None:
            conexion.close()