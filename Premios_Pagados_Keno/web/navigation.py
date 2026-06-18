import time, os, re

from Modules.date_input import preguntar_fecha_reporte
from Modules.reports_folder import clear_reports_folder, download_report
from web.browser import BrowserManager
from web.open_login_page import open_login_page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from Modules.sftp_upload import subir_reporte_premio_pagado


def navigation(report_date = None):
    headless = os.getenv("HEADLESS", "false").lower() == "true"
    web_username = os.getenv("WEB_USERNAME", "")
    web_password = os.getenv("WEB_PASSWORD", "")
    report_date_input = preguntar_fecha_reporte()
    report_date = None
    report_date_text = None

    if report_date_input is not None:
        report_date, report_date_text = report_date_input

    clear_reports_folder()
    manager = BrowserManager(headless=headless)

    try:
        page = open_login_page(manager)

        if page.get_by_text("Inicia sesión en Metabase").is_visible():
            page.locator('input[type="email"]').fill(web_username)
            page.locator('input[type="password"]').fill(web_password)
            page.get_by_text("Iniciar sesión").click()

        time.sleep(3)

        page.locator("div", has_text=re.compile(r"^Region\s*3$")).first.click()
        page.get_by_text("Keno Ventas y Premios - Region 3").click()

        time.sleep(3)

        page.locator('[data-testid="tab-button-input-wrapper"]:has(input[value="Premio"])').click()

        time.sleep(3)

        close_icon = page.locator('svg[aria-label="close icon"]')

        while close_icon.first.is_visible():
            close_icon.first.click()
            time.sleep(1.5)

        page.get_by_role("button", name="Aplicar").click()

        page.get_by_text("Estado Transaccion").click()
        page.get_by_text("Finalizado").click()
        page.get_by_text("Restablecer al valor predeterminado").click()

        page.get_by_text("Fecha Pago de Premio").click()
        if report_date is None:
            page.get_by_text("Ayer").click()
        else:
            print(f"Usando rango personalizado para la fecha: {report_date_text}")
            page.get_by_role("button", name = re.compile(r"Rango de fechas fijo")).click()

            page.get_by_label("Fecha de inicio").click()
            page.get_by_label("Fecha de inicio").fill(report_date_text)

            page.get_by_label("Fecha de fin").click()
            page.get_by_label("Fecha de fin").fill(report_date_text)

            page.get_by_role("button", name = "Añadir filtro").click()

        page.get_by_role("button", name="Aplicar").click()

        while not page.get_by_text("Por Departamento").is_visible():
            time.sleep(3)

        premios_title = page.locator(
            '[data-testid="legend-caption-title"]',
            has_text=re.compile(r"^Premios$"),
        ).first
        premios_title.wait_for(state="attached", timeout=30000)
        premios_title.evaluate(
            "(element) => element.scrollIntoView({ block: 'center', inline: 'nearest' })"
        )
        premios_title.wait_for(state="visible", timeout=10000)

        ellipsis_button = page.locator('button:has(svg[aria-label="ellipsis icon"])').last
        ellipsis_button.wait_for(state="visible", timeout=10000)
        ellipsis_button.click()

        time.sleep(3)

        page.get_by_text("Descargar resultado").click()

        time.sleep(3)

        page.get_by_text(".csv").click()

        time.sleep(3)

        try:
            download_path = download_report(page, report_date)
            subir_reporte_premio_pagado(download_path)
        except PlaywrightTimeoutError:
            print("No se pudo descargar el archivo. Cerrando navegador...")

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        raise
    finally:
        manager.close()
