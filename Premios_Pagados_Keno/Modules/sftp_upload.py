import os, paramiko
import re
from datetime import datetime
from pathlib import Path


MONTH_NAMES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

LEGACY_ACCUMULATED_PATTERNS = {
    "ventas_acumuladas.csv": re.compile(r"^\d{4}-\d{2}-01_\d{4}-\d{2}-\d{2}\.csv$"),
    "premios_acumulados.csv": re.compile(r"^\d{4}-\d{2}-\d{2}_acumulado\.csv$"),
}

def asegurar_directorio_sftp(sftp, remote_dir: str) -> None:
    current_path = ""

    for part in remote_dir.strip("/").split("/"):
        current_path += f"/{part}"

        try:
            sftp.stat(current_path)
        except FileNotFoundError:
            sftp.mkdir(current_path)


def eliminar_consolidados_anteriores(sftp, remote_dir: str, remote_file_name: str) -> None:
    legacy_pattern = LEGACY_ACCUMULATED_PATTERNS.get(remote_file_name)

    if legacy_pattern is None:
        return

    for file_name in sftp.listdir(remote_dir):
        if legacy_pattern.fullmatch(file_name):
            legacy_path = f"{remote_dir}/{file_name}"
            print(f"[INFO] Eliminando consolidado anterior del SFTP: {legacy_path}")
            sftp.remove(legacy_path)


def obtener_fecha_reporte(local_file_path: str) -> datetime:
    file_path = Path(local_file_path)

    return datetime.strptime(file_path.stem[:10], "%Y-%m-%d")


def obtener_ruta_reportes(local_file_path: str) -> str:
    file_path = Path(local_file_path)

    report_date = obtener_fecha_reporte(local_file_path)
    year = str(report_date.year)
    month = MONTH_NAMES[report_date.month]

    base_dir = os.getenv("SFTP_BASE_DIR", "/Paid_Prizes").strip()

    if not base_dir.startswith("/"):
        base_dir = f"/{base_dir}"

    return f"{base_dir}/{year}/{month}/{file_path.name}"


def obtener_ruta_directorio_ventas(local_file_path: str) -> str:
    report_date = obtener_fecha_reporte(local_file_path)
    year = str(report_date.year)

    sales_base_dir = os.getenv("SFTP_SALES_DIR", "/Sales").strip()

    if not sales_base_dir.startswith("/"):
        sales_base_dir = f"/{sales_base_dir}"

    return f"{sales_base_dir}/{year}"


def obtener_ruta_reporte_ventas(local_file_path: str) -> str:
    return f"{obtener_ruta_directorio_ventas(local_file_path)}/ventas_acumuladas.csv"


def obtener_ruta_directorio_premios(local_file_path: str) -> str:
    report_date = obtener_fecha_reporte(local_file_path)
    year = str(report_date.year)

    prizes_base_dir = os.getenv("SFTP_PRIZES_DIR", "/Prizes").strip()

    if not prizes_base_dir.startswith("/"):
        prizes_base_dir = f"/{prizes_base_dir}"

    return f"{prizes_base_dir}/{year}"


def obtener_ruta_reporte_premios(local_file_path: str) -> str:
    return f"{obtener_ruta_directorio_premios(local_file_path)}/premios_acumulados.csv"


def subir_archivo_sftp(local_file_path: str, remote_file_path: str) -> None:
    host = os.getenv("SFTP_HOST")
    port = int(os.getenv("SFTP_PORT", "22"))
    username = os.getenv("SFTP_USERNAME")
    password = os.getenv("SFTP_PASSWORD")

    if not all([host, username, password]):
        raise RuntimeError("Faltan credenciales SFTP en el archivo .env")

    remote_dir = str(Path(remote_file_path).parent).replace("\\", "/")

    transport = paramiko.Transport((host, port))

    try:
        print("[INFO] Conectando al SFTP.")
        transport.connect(username=username, password=password)

        with paramiko.SFTPClient.from_transport(transport) as sftp:
            print(f"[INFO] Verificando ruta remota: {remote_dir}")
            asegurar_directorio_sftp(sftp, remote_dir)
            eliminar_consolidados_anteriores(
                sftp,
                remote_dir,
                Path(remote_file_path).name,
            )

            print("[INFO] Enviando archivo al SFTP.")
            sftp.put(local_file_path, remote_file_path)

            print(f"[INFO] Archivo subido al SFTP: {remote_file_path}")
    finally:
        print("[INFO] Cerrando conexion SFTP.")
        transport.close()


def subir_reporte_ventas(local_file_path: str) -> None:
    remote_file_path = obtener_ruta_reporte_ventas(local_file_path)
    subir_archivo_sftp(local_file_path, remote_file_path)


def subir_reporte_premios(local_file_path: str) -> None:
    remote_file_path = obtener_ruta_reporte_premios(local_file_path)
    subir_archivo_sftp(local_file_path, remote_file_path)


def subir_reporte_premio_pagado(local_file_path: str) -> None:
    remote_file_path = obtener_ruta_reportes(local_file_path)
    subir_archivo_sftp(local_file_path, remote_file_path)
