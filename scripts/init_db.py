import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from job_agent.storage.db import init_db

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
