import os, shutil, re

from datetime import date, datetime, timedelta


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(PROJECT_DIR, "Reports")

def clear_reports_folder() -> None:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    for item_name in os.listdir(DOWNLOAD_DIR):
        item_path = os.path.join(DOWNLOAD_DIR, item_name)

        if os.path.isfile(item_path) or os.path.islink(item_path):
            os.remove(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)

def download_report(page, report_date: date | None = None) -> str:
    with page.expect_download(timeout=120000) as download_info:
        page.get_by_role("button", name=re.compile(r"^Descargar$")).click()

    download = download_info.value
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    file_date = report_date or (datetime.now() - timedelta(days=1)).date()
    download_path = os.path.join(DOWNLOAD_DIR, f"{file_date:%Y-%m-%d}.csv")

    download.save_as(download_path)
    print(f"Archivo descargado exitosamente: {download_path}")

    return download_path
