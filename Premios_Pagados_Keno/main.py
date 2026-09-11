from pathlib import Path

from datetime import date

from Modules.date_input import preguntar_reprocesamiento
from Modules.envio_correo import EnvioCorreo
from web.navigation import navigation
from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")


def main() -> None:
    while True:
        print("[INFO] Ejecutando flujo principal.")
        fecha_ejecucion = date.today()
        navigation()

        try:
            destinatarios = [
                "aprendiz.estadistico@gruporeditos.com",
                "aprendiz.cumplimiento@gruporeditos.com"
            ]  # Agregar las direcciones de correo reales.
            EnvioCorreo().enviar_si_corresponde(destinatarios, fecha_ejecucion)
        except Exception:
            print("[ERROR] El flujo termino correctamente, pero fallo la notificacion por correo. Revise destinatarios, firma, conexion SQL y SMTP.")
            raise RuntimeError("No se pudo completar la notificacion por correo.") from None

        if not preguntar_reprocesamiento():
            print("[INFO] Ejecucion finalizada.")
            break

        print("[INFO] Reiniciando procesamiento.")


if __name__ == "__main__":
    main()
