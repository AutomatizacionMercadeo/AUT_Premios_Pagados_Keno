from pathlib import Path

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")


def main() -> None:
    from web.navigation import navigation

    navigation()


if __name__ == "__main__":
    main()
