from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
DATABASE_URL = f"sqlite:///{PROJECT_ROOT / 'data' / 'mail_agent.sqlite3'}"
