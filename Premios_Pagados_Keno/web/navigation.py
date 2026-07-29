import os
import re
import time
from datetime import date, timedelta

from Modules.reports_folder import clear_reports_folder, download_report
from Modules.sftp_upload import (
    subir_reporte_equipos,
    subir_reporte_premio_pagado,
    subir_reporte_premios,
    subir_reporte_ventas,
)
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from web.browser import BrowserManager
from web.open_login_page import open_login_page


MONTH_NAMES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}
DASHBOARD_TIMEOUT_MS = 90000


def seleccionar_tipo_reporte(page, report_type: str) -> None:
    report_tab = page.locator(
        '[data-testid="tab-button-input-wrapper"]',
        has=page.locator(f'input[value="{report_type}"]'),
    ).first

    print(f"[INFO] Seleccionando directamente la seccion: {report_type}.")
    report_tab.wait_for(state="visible", timeout=DASHBOARD_TIMEOUT_MS)
    report_tab.click(timeout=DASHBOARD_TIMEOUT_MS)
    time.sleep(3)


def limpiar_filtros(page) -> None:
    close_icon = page.locator('svg[aria-label="close icon"]:visible')

    if close_icon.count() > 0:
        print("[INFO] Eliminando filtros seleccionados.")

        while close_icon.count() > 0:
            close_icon.first.click()
            time.sleep(1.5)
    else:
        print("[INFO] No hay filtros seleccionados para eliminar.")


def aplicar_limpieza_filtros(page, report_type: str) -> None:
    apply_button = page.get_by_role("button", name="Aplicar", exact=True)
    print(f"[INFO] Esperando confirmacion de filtros de {report_type}.")
    apply_button.wait_for(
        state="visible",
        timeout=DASHBOARD_TIMEOUT_MS,
    )
    apply_button.click(timeout=DASHBOARD_TIMEOUT_MS)


def revertir_filtros_si_es_necesario(page, report_type: str) -> None:
    revert_icons = page.locator(
        'svg.Icon-revert[role="img"][aria-label="revert icon"]:visible'
    )

    try:
        revert_icons.first.wait_for(state="visible", timeout=10000)
    except PlaywrightTimeoutError:
        print(f"[INFO] No hay filtros pendientes por revertir en {report_type}.")
        return

    print(f"[INFO] Revirtiendo filtros pendientes de {report_type}.")

    while revert_icons.count() > 0:
        revert_icons.first.click(timeout=DASHBOARD_TIMEOUT_MS)
        time.sleep(1.5)

    print(f"[INFO] Aplicando reversion de filtros de {report_type}.")
    aplicar_limpieza_filtros(page, report_type)
    time.sleep(3)


def esperar_resultados(page) -> None:
    print("[INFO] Esperando resultados.")

    while not page.get_by_text("Por Departamento").is_visible():
        time.sleep(3)


def formatear_fecha_metabase(report_date: date) -> str:
    month_name = MONTH_NAMES[report_date.month]
    return f"{report_date.day} de {month_name} de {report_date.year}"


def preparar_descarga_csv(
    page,
    section_title: str,
    buscar_menu_descarga: bool = False,
) -> None:
    print(f"[INFO] Buscando la seccion {section_title}.")
    title = page.locator(
        '[data-testid="legend-caption-title"]',
        has_text=re.compile(rf"^{re.escape(section_title)}$"),
    ).first
    title.wait_for(state="attached", timeout=30000)
    title.evaluate(
        "(element) => element.scrollIntoView({ block: 'center', inline: 'nearest' })"
    )
    title.wait_for(state="visible", timeout=10000)

    if buscar_menu_descarga:
        section_container = title.locator(
            "xpath=ancestor::*[@data-testid='legend-caption'][1]"
        )
        menu_button = section_container.locator(
            'button[data-testid="dashcard-menu"]'
        )

        if (
            section_container.count() != 1
            or section_container.get_attribute("data-testid") != "legend-caption"
            or title.inner_text().strip() != section_title
            or menu_button.count() != 1
            or menu_button.get_attribute("data-testid") != "dashcard-menu"
            or menu_button.get_attribute("aria-haspopup") != "menu"
            or not menu_button.get_attribute("aria-controls")
        ):
            raise RuntimeError(
                f"No se pudo validar el boton de descarga de {section_title}."
            )

        print(
            f"[INFO] Boton de menu validado dentro de la seccion {section_title}."
        )
        download_deadline = time.monotonic() + (DASHBOARD_TIMEOUT_MS / 1000)

        while time.monotonic() < download_deadline:
            section_container.hover(timeout=10000)
            menu_button.wait_for(state="visible", timeout=10000)
            menu_id = menu_button.get_attribute("aria-controls")

            if not menu_id:
                raise RuntimeError(
                    f"El boton de {section_title} no indica el menu que controla."
                )

            menu_button.click(timeout=10000)
            dropdown = page.locator(f'[id="{menu_id}"]')
            download_option = dropdown.get_by_text(
                "Descargar resultados",
                exact=True,
            )

            try:
                dropdown.wait_for(state="visible", timeout=3000)
                download_option.wait_for(state="visible", timeout=3000)
            except PlaywrightTimeoutError:
                page.keyboard.press("Escape")
                print(
                    f"[INFO] Los resultados de {section_title} aun no permiten "
                    "la descarga. Reintentando."
                )
                time.sleep(5)
                continue

            if (
                menu_button.get_attribute("aria-expanded") != "true"
                or dropdown.count() != 1
                or download_option.count() != 1
            ):
                raise RuntimeError(
                    f"No se pudo validar el menu abierto de {section_title}."
                )

            print(f"[INFO] Menu de descarga encontrado para {section_title}.")
            download_option.click()
            break
        else:
            raise RuntimeError(
                f"No se encontro el menu de descarga de la seccion {section_title} "
                f"despues de {DASHBOARD_TIMEOUT_MS // 1000} segundos."
            )
    else:
        ellipsis_button = page.locator(
            'button:has(svg[aria-label="ellipsis icon"])'
        ).last
        ellipsis_button.wait_for(state="visible", timeout=10000)
        ellipsis_button.click()

        time.sleep(3)
        page.get_by_text("Descargar resultado").click()

    time.sleep(3)
    page.get_by_text(".csv").click()

    time.sleep(3)


def volver_al_inicio(page) -> None:
    print("[INFO] Regresando al inicio del dashboard.")
    page.evaluate(
        """
        () => {
            window.scrollTo(0, 0);
            document.documentElement.scrollTop = 0;
            document.body.scrollTop = 0;
        }
        """
    )
    page.locator('[data-testid="tab-button-input-wrapper"]').first.scroll_into_view_if_needed()
    time.sleep(3)


def configurar_y_descargar_ventas(page) -> None:
    seleccionar_tipo_reporte(page, "Venta")
    sales_date_filter = page.get_by_text("Fecha de Venta", exact=True)
    revertir_filtros_si_es_necesario(page, "ventas")
    limpiar_filtros(page)

    print("[INFO] Aplicando limpieza de filtros de ventas.")
    aplicar_limpieza_filtros(page, "ventas")
    print("[INFO] Esperando que se actualicen los filtros de ventas.")
    sales_date_filter.wait_for(
        state="visible",
        timeout=DASHBOARD_TIMEOUT_MS,
    )

    yesterday = date.today() - timedelta(days=1)
    year_start = yesterday.replace(month=1, day=1)
    start_date_text = formatear_fecha_metabase(year_start)
    end_date_text = formatear_fecha_metabase(yesterday)

    print(
        "[INFO] Configurando fecha de venta: "
        f"{year_start:%Y-%m-%d} hasta {yesterday:%Y-%m-%d}."
    )
    sales_date_filter.click(timeout=DASHBOARD_TIMEOUT_MS)
    page.get_by_role(
        "button",
        name=re.compile(r"^Rango de fechas fijo"),
    ).click()

    page.get_by_label("Fecha de inicio").click()
    page.get_by_label("Fecha de inicio").fill(start_date_text)
    page.get_by_label("Fecha de fin").click()
    page.get_by_label("Fecha de fin").fill(end_date_text)
    page.get_by_role("button", name="Añadir filtro", exact=True).click()

    print("[INFO] Aplicando filtros de ventas.")
    page.get_by_role("button", name="Aplicar").click()
    esperar_resultados(page)

    preparar_descarga_csv(page, "Apuestas")
    sales_file_name = f"{year_start:%Y-%m-%d}_{yesterday:%Y-%m-%d}.csv"

    print("[INFO] Descargando consolidado de ventas.")
    download_path = download_report(page, file_name=sales_file_name)
    print("[INFO] Subiendo consolidado de ventas al SFTP.")
    subir_reporte_ventas(download_path)
    volver_al_inicio(page)


def preparar_filtros_base_premios(
    page,
    es_reporte_diario: bool,
    date_filter_name: str | None = "Fecha Pago de Premio",
):
    seleccionar_tipo_reporte(page, "Premio")
    revertir_filtros_si_es_necesario(page, "premios")
    limpiar_filtros(page)

    print("[INFO] Aplicando filtro de premio.")
    aplicar_limpieza_filtros(page, "premios")

    prize_date_filter = None

    if date_filter_name is not None:
        prize_date_filter = page.get_by_text(date_filter_name, exact=True)
        prize_date_filter.wait_for(
            state="visible",
            timeout=DASHBOARD_TIMEOUT_MS,
        )

    if es_reporte_diario:
        print("[INFO] Filtrando transacciones finalizadas.")
        page.get_by_text("Estado Transaccion").click()
        page.get_by_text("Finalizado").click()
        page.get_by_text("Restablecer al valor predeterminado").click()
    else:
        print("[INFO] Seleccionando todos los estados para el consolidado anual.")
        time.sleep(2)
        state_filter_buttons = page.locator(
            'button[data-testid="parameter-value-widget-target"]'
            '[aria-label="Estado Transaccion"]:visible'
        )
        state_filter_buttons.first.wait_for(
            state="visible",
            timeout=DASHBOARD_TIMEOUT_MS,
        )

        if state_filter_buttons.count() != 1:
            raise RuntimeError(
                "No se pudo validar el boton de Estado Transaccion."
            )

        state_filter_button = state_filter_buttons.first

        while True:
            selection_status = state_filter_button.get_by_text(
                "2 selecciones",
                exact=True,
            )

            if selection_status.count() == 1 and selection_status.is_visible():
                print("[INFO] Estado Transaccion confirmado con 2 selecciones.")
                break

            try:
                dialog_id = state_filter_button.get_attribute("aria-controls")

                if not dialog_id:
                    raise RuntimeError(
                        "Estado Transaccion no indica el dialogo que controla."
                    )

                state_filter_button.click(timeout=10000)
                state_filter_dialog = page.locator(f'[id="{dialog_id}"]')
                state_filter_dialog.wait_for(state="visible", timeout=10000)

                select_all_labels = state_filter_dialog.locator(
                    'label[for]:visible'
                ).filter(has_text=re.compile(r"^\s*Seleccionar todo\s*$"))
                select_all_labels.first.wait_for(state="visible", timeout=10000)

                if select_all_labels.count() != 1:
                    raise RuntimeError(
                        "No se pudo validar la etiqueta Seleccionar todo."
                    )

                checkbox_id = select_all_labels.first.get_attribute("for")

                if not checkbox_id:
                    raise RuntimeError(
                        "Seleccionar todo no esta asociado a una casilla."
                    )

                select_all_checkbox = state_filter_dialog.locator(
                    f'input[type="checkbox"][id="{checkbox_id}"]'
                )

                if select_all_checkbox.count() != 1:
                    raise RuntimeError(
                        "No se encontro la casilla de Seleccionar todo."
                    )

                select_all_checkbox.check(timeout=10000)

                if not select_all_checkbox.is_checked():
                    raise RuntimeError(
                        "La casilla Seleccionar todo no quedo marcada."
                    )

                update_filter_button = state_filter_dialog.get_by_role(
                    "button",
                    name="Actualizar filtro",
                    exact=True,
                )
                update_filter_button.click(timeout=10000)
                state_filter_dialog.wait_for(state="hidden", timeout=10000)
                selection_status.wait_for(state="visible", timeout=10000)
            except (PlaywrightTimeoutError, RuntimeError) as error:
                print(
                    "[WARN] No se confirmaron las 2 selecciones de "
                    f"Estado Transaccion: {error}. Reintentando."
                )
                page.keyboard.press("Escape")
                time.sleep(3)
                continue

            print("[INFO] Estado Transaccion confirmado con 2 selecciones.")
            break

    return prize_date_filter


def configurar_y_descargar_premios_acumulados(page, yesterday: date) -> None:
    preparar_filtros_base_premios(
        page,
        es_reporte_diario=False,
        date_filter_name=None,
    )
    print("[INFO] Aplicando todos los estados de transaccion.")
    page.get_by_role("button", name="Aplicar").click()
    esperar_resultados(page)
    preparar_descarga_csv(
        page,
        "Premios",
        buscar_menu_descarga=True,
    )

    try:
        print("[INFO] Descargando consolidado acumulado de premios.")
        accumulated_file_name = f"{yesterday:%Y-%m-%d}_acumulado.csv"
        download_path = download_report(page, file_name=accumulated_file_name)
        print("[INFO] Subiendo premios acumulados al SFTP.")
        subir_reporte_premios(download_path)
    except PlaywrightTimeoutError:
        print("[ERROR] No se pudo descargar el acumulado de premios.")


def configurar_y_descargar_premios_diarios(page, yesterday: date) -> None:
    prize_date_filter = preparar_filtros_base_premios(
        page,
        es_reporte_diario=True,
    )

    print(f"[INFO] Configurando premios diarios para: {yesterday:%Y-%m-%d}.")
    prize_date_filter.click(timeout=DASHBOARD_TIMEOUT_MS)
    page.get_by_text("Ayer", exact=True).click()

    print("[INFO] Aplicando filtros de premios diarios.")
    page.get_by_role("button", name="Aplicar").click()
    esperar_resultados(page)
    preparar_descarga_csv(page, "Premios")

    try:
        print("[INFO] Descargando reporte diario de premios.")
        download_path = download_report(page, report_date=yesterday)
        print("[INFO] Subiendo reporte diario a Paid_Prizes.")
        subir_reporte_premio_pagado(download_path)
    except PlaywrightTimeoutError:
        print("[ERROR] No se pudo descargar el reporte diario de premios.")


def configurar_y_descargar_premios(page) -> None:
    yesterday = date.today() - timedelta(days=1)

    print("[INFO] Iniciando consolidado acumulado de premios.")
    configurar_y_descargar_premios_acumulados(page, yesterday)

    volver_al_inicio(page)

    print("[INFO] Iniciando reporte diario de premios.")
    configurar_y_descargar_premios_diarios(page, yesterday)


def configurar_y_descargar_equipos(page) -> None:
    yesterday = date.today() - timedelta(days=1)

    seleccionar_tipo_reporte(page, "Equipos")
    preparar_descarga_csv(
        page,
        "Equipos",
        buscar_menu_descarga=True,
    )

    try:
        print("[INFO] Descargando consolidado acumulado de equipos.")
        teams_file_name = f"{yesterday:%Y-%m-%d}_equipos.csv"
        download_path = download_report(page, file_name=teams_file_name)
        print("[INFO] Subiendo consolidado de equipos al SFTP.")
        subir_reporte_equipos(download_path)
    except PlaywrightTimeoutError:
        print("[ERROR] No se pudo descargar el consolidado de equipos.")


def navigation():
    print("[INFO] Iniciando procesamiento.")
    headless = os.getenv("HEADLESS", "false").lower() == "true"
    web_username = os.getenv("WEB_USERNAME", "")
    web_password = os.getenv("WEB_PASSWORD", "")
    print("[INFO] Limpiando carpeta de reportes.")
    clear_reports_folder()
    manager = BrowserManager(headless=headless)

    try:
        print("[INFO] Abriendo Metabase.")
        page = open_login_page(manager)

        if page.get_by_text("Inicia sesión en Metabase").is_visible():
            print("[INFO] Iniciando sesion.")
            page.locator('input[type="email"]').fill(web_username)
            page.locator('input[type="password"]').fill(web_password)
            page.get_by_text("Iniciar sesión").click()

        time.sleep(3)

        print("[INFO] Abriendo dashboard Region 3.")
        page.locator("div", has_text=re.compile(r"^Region\s*3$")).first.click()
        page.get_by_text("Keno Ventas y Premios - Region 3").click()

        time.sleep(3)

        print("[INFO] Iniciando flujo de ventas.")
        configurar_y_descargar_ventas(page)

        print("[INFO] Iniciando flujo de premios.")
        configurar_y_descargar_premios(page)

        volver_al_inicio(page)

        print("[INFO] Iniciando flujo de equipos.")
        configurar_y_descargar_equipos(page)
    except Exception as error:
        print(f"[ERROR] Ocurrio un error: {error}")
        raise
    finally:
        print("[INFO] Cerrando navegador.")
        manager.close()
