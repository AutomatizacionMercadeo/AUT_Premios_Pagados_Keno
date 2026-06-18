import os, paramiko
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

def asegurar_directorio_sftp(sftp, remote_dir: str) -> None:
    current_path = ""

    for part in remote_dir.strip("/").split("/"):
        current_path += f"/{part}"

        try:
            sftp.stat(current_path)
        except FileNotFoundError:
            sftp.mkdir(current_path)

def obtener_ruta_reportes(local_file_path: str) -> str:
    file_path = Path(local_file_path)

    report_date = datetime.strptime(file_path.stem, "%Y-%m-%d")
    year = str(report_date.year)
    month = MONTH_NAMES[report_date.month]

    base_dir = os.getenv("SFTP_BASE_DIR", "/Paid_Prizes").strip()

    if not base_dir.startswith("/"):
        base_dir = f"/{base_dir}"

    return f"{base_dir}/{year}/{month}/{file_path.name}"

def subir_reporte_premio_pagado(local_file_path: str) -> None:
    host = os.getenv("SFTP_HOST")
    port = int(os.getenv("SFTP_PORT", "22"))
    username = os.getenv("SFTP_USERNAME")
    password = os.getenv("SFTP_PASSWORD")

    if not all([host, username, password]):
        raise RuntimeError("Faltan credenciales SFTP en el archivo .env")
    
    remote_file_path = obtener_ruta_reportes(local_file_path)
    remote_dir = str(Path(remote_file_path).parent).replace("\\", "/")

    transport = paramiko.Transport((host, port))

    try:
        transport.connect(username=username, password=password)

        with paramiko.SFTPClient.from_transport(transport) as sftp:
            asegurar_directorio_sftp(sftp, remote_dir)
            sftp.put(local_file_path, remote_file_path)

            print(f"Archivo subido exitosamente al SFTP: {remote_file_path}")
    finally:
        transport.close()