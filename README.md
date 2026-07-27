# Premios Pagados Keno

Automatizacion en Python para consultar en Metabase el reporte de premios pagados de Keno, descargar el resultado en formato CSV y subirlo a un servidor SFTP organizado por anio y mes.

El flujo usa Playwright para navegar la interfaz web, Paramiko para la conexion SFTP y variables de entorno para credenciales y configuracion.

## Flujo General

1. Carga variables desde `Premios_Pagados_Keno/.env`.
2. Limpia la carpeta local de reportes antes de ejecutar.
3. Inicia Chromium con Playwright e inicia sesion en Metabase.
4. Navega al dashboard `Keno Ventas y Premios - Region 3`.
5. Verifica que el dashboard este en `Venta` y limpia sus filtros actuales.
6. Filtra `Fecha de Venta` desde el 1 de enero del anio de ayer hasta ayer.
7. Descarga el consolidado de `Apuestas` y lo sube a `Sales`.
8. Regresa mediante scroll al inicio y cambia a `Premio`.
9. Revierte y limpia los filtros actuales de premios.
10. Abre `Estado Transaccion`, marca `Finalizado` y usa `Restablecer al valor predeterminado` para el acumulado anual.
11. Filtra `Fecha Pago de Premio` desde el 1 de enero hasta ayer.
12. Descarga el acumulado y lo sube a `Prizes`.
13. Limpia nuevamente los filtros de premios y filtra `Estado Transaccion` por `Finalizado` para el reporte diario.
14. Filtra `Fecha Pago de Premio` por `Ayer`.
15. Descarga el reporte diario y lo sube a `Paid_Prizes`.
16. Crea las rutas remotas de anio y, solo para `Paid_Prizes`, de mes si no existen.
17. Cierra el navegador y pregunta si se desea ejecutar nuevamente.

La carga de los controles de ventas dispone de hasta 90 segundos despues de
aplicar la seleccion de `Venta` y la limpieza de filtros.

El cambio entre `Venta` y `Premio` pulsa directamente la pestaña identificada
por `data-testid="tab-button-input-wrapper"` y el valor de su `input`. No se usa
la visibilidad para determinar cual esta activa, porque ambas pestañas pueden
estar visibles simultaneamente.

La limpieza de filtros de `Venta` y `Premio` usa la misma logica. Primero busca
directamente SVG visibles con clase `Icon-revert`, rol `img` y etiqueta
`revert icon`. Si existen, los pulsa todos,
confirma la reversion con `Aplicar` y espera 3 segundos. Luego localiza todas las
X visibles, las pulsa una por una y espera hasta 90 segundos a que aparezca el
boton inferior `Aplicar` antes de confirmar nuevamente los cambios.

## Estructura Del Proyecto

```text
Premios_Pagados_Keno/
|-- main.py
|-- requirements.txt
|-- Modules/
|   |-- date_input.py
|   |-- reports_folder.py
|   |-- sftp_upload.py
|   `-- Reports/
`-- web/
    |-- browser.py
    |-- navigation.py
    `-- open_login_page.py
```

## Modulos Principales

`main.py`

Punto de entrada del proyecto. Carga el archivo `.env` y ejecuta el flujo principal desde `web.navigation`.

`web/browser.py`

Gestiona Playwright:

- Inicia Chromium.
- Crea una pagina con `ignore_https_errors=True`.
- Habilita descargas con `accept_downloads=True`.
- Cierra navegador y Playwright al terminar.

`web/open_login_page.py`

Abre la URL configurada en `WEB_URL`. Cada intento dispone de un maximo total de
90 segundos para cargar la pagina y mostrar el inicio de sesion. Si no queda
lista, cierra el navegador, espera 3 segundos y vuelve a intentar.

`web/navigation.py`

Contiene la navegacion principal:

- Login.
- Seleccion del dashboard.
- Seleccion del tipo de reporte.
- Limpieza de filtros.
- Aplicacion de filtros.
- Descarga del CSV.
- Subida del archivo al SFTP.

`Modules/date_input.py`

Gestiona la pregunta de reprocesamiento al final de cada ejecucion. Los rangos de
ventas y premios se calculan automaticamente y ya no se solicita una fecha al
inicio.

`Modules/reports_folder.py`

Gestiona la carpeta local de reportes:

- Limpia la carpeta antes de cada ejecucion.
- Espera el evento real de descarga de Playwright.
- Guarda el CSV de premios usando la fecha de corte de ayer.
- Permite asignar al consolidado de ventas un nombre basado en su rango anual.

`Modules/sftp_upload.py`

Gestiona la conexion SFTP:

- Lee credenciales desde `.env`.
- Construye la ruta remota usando la fecha del nombre del archivo.
- Crea carpetas remotas si no existen.
- Sube el archivo CSV.

## Requisitos

- Python 3.10 o superior.
- Acceso a Metabase.
- Acceso al servidor SFTP.
- Chromium instalado por Playwright.

Dependencias:

```text
playwright
python-dotenv
paramiko
```

## Instalacion

Desde la carpeta del proyecto:

```powershell
cd C:\Projects\Premios_Pagados_Keno\Premios_Pagados_Keno
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Configuracion

Crear o actualizar el archivo:

```text
Premios_Pagados_Keno/.env
```

Variables requeridas:

```env
WEB_URL=https://url-de-metabase
WEB_USERNAME=usuario
WEB_PASSWORD=password
HEADLESS=false

SFTP_HOST=host-sftp
SFTP_PORT=22
SFTP_USERNAME=usuario-sftp
SFTP_PASSWORD=password-sftp
SFTP_BASE_DIR=/Paid_Prizes
SFTP_SALES_DIR=/Sales
SFTP_PRIZES_DIR=/Prizes
```

Notas:

- `HEADLESS=false` permite ver el navegador durante la ejecucion.
- `HEADLESS=true` ejecuta el navegador en segundo plano.
- `SFTP_BASE_DIR` define la carpeta raiz remota donde se suben los reportes.
- `SFTP_SALES_DIR` define la carpeta raiz remota de ventas. Si no se configura, usa `/Sales`.
- `SFTP_PRIZES_DIR` define la carpeta raiz de premios acumulados. Si no se configura, usa `/Prizes`.
- No subir el archivo `.env` al repositorio.

## Ejecucion

Desde:

```powershell
C:\Projects\Premios_Pagados_Keno\Premios_Pagados_Keno
```

Ejecutar:

```powershell
python main.py
```

## Fechas Automaticas

- Ventas: desde el 1 de enero del anio al que pertenece ayer hasta ayer.
- Premios acumulados: desde el 1 de enero del anio al que pertenece ayer hasta ayer.
- Premios diarios: solamente ayer.

Por ejemplo, en una ejecucion del 24 de julio de 2026, premios utiliza el rango
`1 de enero de 2026` a `23 de julio de 2026`.

## Reprocesamiento

Al finalizar una ejecucion completa, el programa pregunta:

```text
Deseas ejecutar nuevamente el proceso? (si/no):
```

Si el usuario responde `si`, el flujo completo vuelve a empezar.

Si responde `no`, termina la ejecucion.

Si no responde en 10 segundos, tambien termina la ejecucion.

Respuestas aceptadas para continuar:

```text
s
si
y
yes
```

Respuestas aceptadas para terminar:

```text
n
no
```

## Nombre Del Archivo

El CSV diario de premios se guarda con el formato:

```text
YYYY-MM-DD.csv
```

Ejemplos:

```text
2026-06-17.csv
2027-01-01.csv
```

El consolidado acumulado de premios se diferencia con el sufijo `_acumulado`:

```text
YYYY-MM-DD_acumulado.csv
```

Ejemplo:

```text
2026-07-23_acumulado.csv
```

El consolidado de ventas incluye el rango anual en el nombre:

```text
YYYY-01-01_YYYY-MM-DD.csv
```

Ejemplo:

```text
2026-01-01_2026-07-23.csv
```

El periodo se calcula usando el anio al que pertenece ayer. Esto permite que el
1 de enero se descargue correctamente el consolidado completo del anio anterior,
en lugar de construir un rango de fechas invertido.

## Carpeta Local De Reportes

Antes de cada ejecucion, la carpeta local de reportes se limpia para evitar archivos de ejecuciones anteriores.

La ruta local usada por el modulo actual es:

```text
Premios_Pagados_Keno/Modules/Reports/
```

## Subida Al SFTP

La ruta remota se construye con base en el nombre del archivo descargado.

Formato:

```text
/Paid_Prizes/ANIO/MES/ARCHIVO.csv
```

Ejemplo:

```text
/Paid_Prizes/2026/Junio/2026-06-17.csv
```

Si las carpetas no existen, el programa las crea.

Para el consolidado acumulado de premios verifica y crea:

```text
/Prizes/ANIO/premios_acumulados.csv
```

Ejemplo:

```text
/Prizes/2026/premios_acumulados.csv
```

Como este reporte acumula los premios desde el 1 de enero hasta la fecha de
corte, se almacena directamente dentro del anio y no se divide en carpetas
mensuales.

Para ventas verifica y crea la estructura:

```text
/Sales/ANIO/ventas_acumuladas.csv
```

Ejemplo:

```text
/Sales/2026/ventas_acumuladas.csv
```

Los consolidados conservan nombres con fechas mientras se encuentran en la
carpeta local, pero se cargan al SFTP con nombres remotos fijos. Por eso, cada
nueva ejecucion sobrescribe el acumulado anterior de su carpeta de destino y no
deja multiples versiones con fechas de corte diferentes. Antes de la carga,
tambien elimina de esa carpeta los consolidados historicos que tengan el formato
anterior con fechas en el nombre. Esta limpieza no afecta los reportes diarios
de `Paid_Prizes` ni archivos con otros nombres.

El periodo de los destinos se obtiene del nombre del reporte: `Sales` y
`Prizes` usan el anio, mientras que `Paid_Prizes` usa el anio y el mes.

Esto evita errores en cambios de mes o anio. Por ejemplo, si el programa se ejecuta el `2027-01-01` y el archivo generado es:

```text
2026-12-31.csv
```

Entonces se sube a:

```text
/Paid_Prizes/2026/Diciembre/2026-12-31.csv
```

## Selectores Importantes

El flujo usa selectores de Playwright basados en texto, roles accesibles y atributos estables:

- Login: inputs `email` y `password`.
- Botones: `get_by_role("button", name=...)`.
- Filtros: `get_by_text(...)`.
- Iconos SVG: `svg[aria-label="close icon"]` y `svg[aria-label="ellipsis icon"]`.
- Titulos de leyenda: `[data-testid="legend-caption-title"]`.

Cuando sea posible, preferir:

```python
page.get_by_role("button", name="Aplicar")
page.get_by_label("Fecha de inicio")
page.locator('[data-testid="legend-caption-title"]')
```

Evitar clases generadas por Mantine o Emotion como:

```text
emotion-...
m_...
QSUlZ...
```

Estas clases pueden cambiar entre cargas o versiones.

## Manejo De Errores

El proyecto maneja estos casos:

- Si Metabase no carga, cierra y reabre el navegador.
- Si no existe `WEB_URL`, lanza un error claro.
- Si no se descarga el archivo dentro del timeout, informa fallo de descarga.
- Si faltan credenciales SFTP, lanza un error claro.
- Si no hay respuesta en la pregunta de reprocesamiento, finaliza la ejecucion.

## Logs En Terminal

El flujo imprime mensajes cortos para seguir el avance del proceso:

```text
[INFO] Accion normal del proceso.
[WARN] Advertencia o reintento.
[ERROR] Error que requiere atencion.
```

Estos mensajes ayudan a identificar en que etapa esta la ejecucion: login, filtros, descarga, subida SFTP o cierre.

## Consideraciones

- El input con timeout usa `msvcrt`, por lo que esta implementacion esta pensada para Windows.
- El flujo depende de textos visibles en Metabase. Si cambian labels o textos, puede ser necesario actualizar selectores.
- La descarga usa `page.expect_download()`, por lo que el navegador no se cierra hasta que Playwright recibe y guarda el archivo.
- La organizacion remota del SFTP depende del nombre del CSV, no de la fecha actual de ejecucion.

## Comandos Utiles

Validar sintaxis:

```powershell
python -m py_compile main.py web\navigation.py web\browser.py web\open_login_page.py Modules\date_input.py Modules\reports_folder.py Modules\sftp_upload.py
```

Ejecutar en modo visible:

```env
HEADLESS=false
```

Ejecutar en modo oculto:

```env
HEADLESS=true
```
