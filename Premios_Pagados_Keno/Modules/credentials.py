"""Conexion SQL y carga de credenciales desde sp_getData."""

import os
import re
from contextlib import closing

import pyodbc


def construir_conexion_sql() -> str:
    valores = {nombre: os.getenv(nombre, "") for nombre in ("SERVER", "DATABASE", "USR", "PASS")}
    faltantes = [nombre for nombre, valor in valores.items() if not valor.strip()]
    if faltantes:
        raise RuntimeError("Faltan variables SQL en .env: " + ", ".join(faltantes))

    def escapar(valor: str) -> str:
        return "{" + valor.replace("}", "}}") + "}"

    drivers = pyodbc.drivers()
    driver = next((nombre for nombre in (
        "ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server",
    ) if nombre in drivers), None)
    if driver is None:
        raise RuntimeError("Instale ODBC Driver 18 o 17 for SQL Server.")
    return (
        f"DRIVER={escapar(driver)};SERVER={escapar(valores['SERVER'])};"
        f"DATABASE={escapar(valores['DATABASE'])};UID={escapar(valores['USR'])};"
        f"PWD={escapar(valores['PASS'])};Encrypt=yes;TrustServerCertificate=yes;"
    )


def describir_error_sql(error: pyodbc.Error) -> str:
    """Describe la causa sin publicar mensajes del driver con datos de conexion."""
    estado = str(error.args[0]) if error.args else ""
    estado = estado if re.fullmatch(r"[A-Z0-9]{5}", estado) else "desconocido"
    detalle = str(error).lower()
    if any(texto in detalle for texto in (
        "-2146893019", "certificate chain", "cadena de certific",
        "certificate verify failed", "self-signed certificate",
    )):
        causa = (
            "El driver reporto un error de certificado aunque el flujo configura "
            "TrustServerCertificate=yes. Verifique con infraestructura la configuracion "
            "TLS del servidor y que se este ejecutando la version actual del flujo."
        )
    elif estado == "28000":
        causa = "SQL Server rechazo la autenticacion. Revise USR, PASS y los permisos de la cuenta."
    elif estado in ("08001", "08S01", "HYT00", "HYT01"):
        causa = "Revise SERVER, puerto, red/VPN, disponibilidad de SQL Server y configuracion TLS."
    elif estado in ("42000", "3D000"):
        causa = "Revise DATABASE, la existencia de sp_getData y los permisos para ejecutarlo."
    else:
        causa = "Revise la configuracion SQL y los registros del servidor."
    return f"Error SQL Server (SQLSTATE {estado}). {causa}"


def consultar(cursor, opcion: str, columnas: tuple[str, ...]) -> tuple:
    cursor.execute("EXEC sp_getData ?", opcion)
    while cursor.description is None:
        if not cursor.nextset():
            raise RuntimeError(f"sp_getData '{opcion}' no devolvio resultados.")
    nombres = [columna[0].lower() for columna in cursor.description]
    fila = cursor.fetchone()
    if fila is None or any(columna not in nombres for columna in columnas):
        raise RuntimeError(f"sp_getData '{opcion}' no devolvio las columnas requeridas.")
    valores = tuple(fila[nombres.index(columna)] for columna in columnas)
    if any(valor is None or not str(valor).strip() for valor in valores):
        raise RuntimeError(f"sp_getData '{opcion}' devolvio credenciales incompletas.")
    return valores


def cargar_credenciales() -> None:
    """Actualiza el entorno solo cuando ambas configuraciones son validas."""
    conexion_sql = construir_conexion_sql()
    try:
        with closing(pyodbc.connect(conexion_sql, timeout=30)) as conexion:
            conexion.timeout = 30
            with closing(conexion.cursor()) as cursor:
                web_url, web_username, web_password, secret_id = consultar(
                    cursor, "31", ("tenant_id", "server_smtp", "port_smtp", "secret_id"),
                )
                host, port, username, password = consultar(
                    cursor, "29", ("tenant_id", "port_smtp", "user_sig", "pass_sig"),
                )
    except pyodbc.Error as error:
        raise RuntimeError(
            "No se pudieron obtener las credenciales desde SQL Server. " + describir_error_sql(error)
        ) from None
    try:
        puerto = int(str(port))
        if not 1 <= puerto <= 65535:
            raise ValueError
    except (TypeError, ValueError):
        raise RuntimeError("sp_getData '29' devolvio un puerto SFTP invalido.") from None
    os.environ.update({
        "WEB_URL": str(web_url), "WEB_USERNAME": str(web_username),
        "WEB_PASSWORD": str(web_password), "DASHBOARD_URL": str(web_url) + str(secret_id),
        "SFTP_HOST": str(host), "SFTP_PORT": str(puerto),
        "SFTP_USERNAME": str(username), "SFTP_PASSWORD": str(password),
    })
