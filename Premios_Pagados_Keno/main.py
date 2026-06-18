from pathlib import Path

from Modules.date_input import preguntar_reprocesamiento
from web.navigation import navigation
from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")


def main() -> None:
    while True:
        navigation()

        if not preguntar_reprocesamiento():
            break


if __name__ == "__main__":
    main()
