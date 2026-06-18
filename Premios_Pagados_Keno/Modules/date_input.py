import msvcrt
import time
from datetime import date


MONTHS = {
    "1": 1,
    "01": 1,
    "enero": 1,
    "2": 2,
    "02": 2,
    "febrero": 2,
    "3": 3,
    "03": 3,
    "marzo": 3,
    "4": 4,
    "04": 4,
    "abril": 4,
    "5": 5,
    "05": 5,
    "mayo": 5,
    "6": 6,
    "06": 6,
    "junio": 6,
    "7": 7,
    "07": 7,
    "julio": 7,
    "8": 8,
    "08": 8,
    "agosto": 8,
    "9": 9,
    "09": 9,
    "septiembre": 9,
    "setiembre": 9,
    "10": 10,
    "octubre": 10,
    "11": 11,
    "noviembre": 11,
    "12": 12,
    "diciembre": 12,
}

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

INPUT_TIMEOUT_SECONDS = 10


def input_con_timeout(prompt: str, timeout_seconds: int = INPUT_TIMEOUT_SECONDS) -> str | None:
    print(prompt, end="", flush=True)
    chars = []
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        if msvcrt.kbhit():
            char = msvcrt.getwch()

            if char in ("\r", "\n"):
                print()
                return "".join(chars)
            if char == "\003":
                raise KeyboardInterrupt
            if char == "\b":
                if chars:
                    chars.pop()
                    print("\b \b", end="", flush=True)
                continue
            if char in ("\x00", "\xe0"):
                msvcrt.getwch()
                continue

            chars.append(char)
            print(char, end="", flush=True)

        time.sleep(0.05)

    print()
    return None


def normalizar_mes(month_value: str) -> str:
    return month_value.strip().casefold()


def formatear_fecha_para_input(report_date: date) -> str:
    month_name = MONTH_NAMES[report_date.month]
    return f"{report_date.day} de {month_name} de {report_date.year}"


def obtener_campos_faltantes(
    day_value: str,
    month_value: str,
    year_value: str,
) -> list[str]:
    missing_fields = []

    if not day_value:
        missing_fields.append("dia")
    if not month_value:
        missing_fields.append("mes")
    if not year_value:
        missing_fields.append("anio")

    return missing_fields


def preguntar_fecha_reporte() -> tuple[date, str] | None:
    print(
        "Fecha del reporte. Deja los campos vacios o espera "
        f"{INPUT_TIMEOUT_SECONDS} segundos para usar 'Ayer'."
    )

    while True:
        day_value = input_con_timeout("Dia: ")
        if day_value is None:
            print("No se recibio input. Se usara 'Ayer'.")
            return None

        month_value = input_con_timeout("Mes (numero o nombre): ")
        if month_value is None:
            print("No se recibio input. Se usara 'Ayer'.")
            return None

        year_value = input_con_timeout("Año: ")
        if year_value is None:
            print("No se recibio input. Se usara 'Ayer'.")
            return None

        day_value = day_value.strip()
        month_value = normalizar_mes(month_value)
        year_value = year_value.strip()

        if not day_value and not month_value and not year_value:
            return None

        missing_fields = obtener_campos_faltantes(day_value, month_value, year_value)
        if missing_fields:
            print(
                "Faltan datos por ingresar: "
                f"{', '.join(missing_fields)}. "
                "Completa dia, mes y anio, o deja los tres campos vacios para usar 'Ayer'."
            )
            continue

        try:
            day = int(day_value)
            year = int(year_value)
            month = MONTHS[month_value]
            report_date = date(year, month, day)

            return report_date, formatear_fecha_para_input(report_date)
        except KeyError:
            print("Mes invalido. Usa un numero del 1 al 12 o el nombre del mes.")
        except ValueError:
            print("Fecha invalida. Revisa dia, mes y anio.")
