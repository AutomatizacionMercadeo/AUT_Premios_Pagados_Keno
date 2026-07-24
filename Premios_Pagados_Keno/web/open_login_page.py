import os
import time

from web.browser import BrowserManager
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


PAGE_READY_TIMEOUT_SECONDS = 90
RETRY_DELAY_SECONDS = 3


def open_login_page(manager: BrowserManager):
    web_url = os.getenv("WEB_URL")

    if not web_url:
        raise RuntimeError("No se encontro WEB_URL en el archivo .env")

    while True:
        page = manager.open()

        try:
            print("[INFO] Cargando pagina de login.")
            ready_deadline = time.monotonic() + PAGE_READY_TIMEOUT_SECONDS
            page.goto(
                web_url,
                wait_until="domcontentloaded",
                timeout=PAGE_READY_TIMEOUT_SECONDS * 1000,
            )
            remaining_timeout_ms = max(
                1,
                int((ready_deadline - time.monotonic()) * 1000),
            )
            page.get_by_text("Inicia sesión en Metabase").wait_for(
                state="visible",
                timeout=remaining_timeout_ms,
            )
            print("[INFO] Login disponible.")
            return page
        except PlaywrightTimeoutError:
            print(
                "[WARN] Metabase no estuvo disponible despues de "
                f"{PAGE_READY_TIMEOUT_SECONDS} segundos. Reintentando..."
            )
            manager.close()
            time.sleep(RETRY_DELAY_SECONDS)
