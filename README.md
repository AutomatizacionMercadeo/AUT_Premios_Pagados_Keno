# Premios Pagados Keno

Automatizacion en Python para consultar en Metabase el reporte de premios pagados de Keno, descargar el resultado en formato CSV y subirlo a un servidor SFTP organizado por anio y mes.

El flujo usa Playwright para navegar la interfaz web, Paramiko para la conexion SFTP y variables de entorno para credenciales y configuracion.

## Flujo General

1. Carga variables desde `Premios_Pagados_Keno/.env`.
2. Pregunta una fecha de reporte por terminal.
3. Si no se ingresa fecha, usa el filtro `Ayer`.
4. Si se ingresa fecha, usa un rango fijo con esa fecha como inicio y fin.
5. Limpia la carpeta local de reportes antes de ejecutar.
6. Inicia Chromium con Playwright.
7. Inicia sesion en Metabase.
8. Navega al dashboard `Keno Ventas y Premios - Region 3`.
9. Aplica filtros de estado y fecha.
10. Descarga el resultado en `.csv`.
11. Guarda el archivo con nombre `YYYY-MM-DD.csv`.
12. Se conecta al SFTP.
13. Crea la ruta remota si no existe.
14. Sube el archivo al SFTP.
15. Cierra el navegador.
16. Pregunta si se desea procesar otra fecha.
17. Si la respuesta es `si`, vuelve a iniciar desde el input de fecha.
18. Si la respuesta es `no` o no hay respuesta en 10 segundos, termina la ejecucion.

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

Abre la URL configurada en `WEB_URL`. Si la pagina no carga correctamente o no aparece el texto de inicio de sesion, cierra el navegador y vuelve a intentar.

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

Gestiona la fecha del reporte ingresada por terminal:

- Acepta dia, mes y anio.
- El mes puede ingresarse como numero o como texto.
- Normaliza el mes sin importar mayusculas/minusculas.
- Convierte la fecha a texto para los inputs de Metabase, por ejemplo `1 de junio de 2026`.
- Si pasan 10 segundos sin input en algun campo, usa el flujo por defecto `Ayer`.
- Si el usuario deja los tres campos vacios, usa `Ayer`.
- Si solo llena uno o dos campos, muestra cuales datos faltan.
- Valida que la fecha ingresada sea igual o anterior a la fecha de ayer.
- Al final del procesamiento pregunta si se desea ejecutar otra fecha.

`Modules/reports_folder.py`

Gestiona la carpeta local de reportes:

- Limpia la carpeta antes de cada ejecucion.
- Espera el evento real de descarga de Playwright.
- Guarda el CSV con nombre basado en la fecha del reporte.
- Si no se ingreso fecha, usa la fecha de ayer.

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
```

Notas:

- `HEADLESS=false` permite ver el navegador durante la ejecucion.
- `HEADLESS=true` ejecuta el navegador en segundo plano.
- `SFTP_BASE_DIR` define la carpeta raiz remota donde se suben los reportes.
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

## Input De Fecha

Al iniciar, el programa pregunta:

```text
Dia:
Mes (numero o nombre):
Anio:
```

### Usar Fecha Personalizada

Ejemplos validos:

```text
Dia: 1
Mes (numero o nombre): junio
Anio: 2026
```

```text
Dia: 1
Mes (numero o nombre): 6
Anio: 2026
```

Ambos generan el texto:

```text
1 de junio de 2026
```

Ese texto se usa para llenar `Fecha de inicio` y `Fecha de fin`.

### Usar Ayer

El flujo usa `Ayer` cuando:

- El usuario deja los tres campos vacios.
- El usuario no ingresa ningun valor durante 10 segundos en cualquiera de los campos.

### Datos Incompletos

Si el usuario ingresa solo uno o dos campos, el programa informa que datos faltan.

Ejemplo:

```text
Faltan datos por ingresar: mes, anio. Completa dia, mes y anio, o deja los tres campos vacios para usar 'Ayer'.
```

### Fechas Futuras O Del Dia Actual

La fecha ingresada debe corresponder a un dia que ya haya pasado. El programa compara la fecha ingresada contra la fecha de ayer.

Si la fecha ingresada es mayor a ayer, muestra una advertencia y vuelve a pedir los datos.

Ejemplo de advertencia:

```text
La fecha ingresada corresponde a un dia que todavia no ha pasado. Ingresa una fecha igual o menor a 17 de junio de 2026.
```

## Reprocesamiento

Al finalizar una ejecucion completa, el programa pregunta:

```text
Deseas procesar otra fecha? (si/no):
```

Si el usuario responde `si`, el flujo vuelve a empezar desde el input de fecha.

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

El CSV se guarda con el formato:

```text
YYYY-MM-DD.csv
```

Ejemplos:

```text
2026-06-17.csv
2027-01-01.csv
```

Si el usuario ingresa una fecha, el nombre del archivo usa esa fecha.

Si el usuario no ingresa fecha, el nombre del archivo usa la fecha de ayer.

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
- Si la fecha del usuario esta incompleta, informa campos faltantes.
- Si la fecha es invalida, solicita corregirla.
- Si la fecha ingresada es mayor a ayer, solicita otra fecha.
- Si no se descarga el archivo dentro del timeout, informa fallo de descarga.
- Si faltan credenciales SFTP, lanza un error claro.
- Si no hay respuesta en la pregunta de reprocesamiento, finaliza la ejecucion.

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
