import os, time, re

from web.browser import BrowserManager
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def open_login_page(manager: BrowserManager):
    web_url = os.getenv("WEB_URL")

    if not web_url:
        raise RuntimeError("No se encontro WEB_URL en el archivo .env")

    while True:
        page = manager.open()

        try:
            page.goto(web_url, wait_until="domcontentloaded", timeout=10000)
            page.get_by_text("Inicia sesión en Metabase").wait_for(
                state="visible",
                timeout=10000,
            )
            return page
        except PlaywrightTimeoutError:
            print("No cargo el browser correctamente. Cerrando y abriendo nuevamente...")
            manager.close()
            time.sleep(3)
