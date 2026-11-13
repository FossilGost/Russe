"""Daily verified backups for the Compose backup service."""
# Fixed local Python script only; no shell or user-controlled arguments.
import subprocess  # nosec B404
import sys
import time
from pathlib import Path

while True:
    result = subprocess.run([sys.executable, str(Path(__file__).with_name("backup.py")), "/backups"], check=False)  # nosec B603
    if result.returncode:
        print("Sauvegarde échouée : vérifier les journaux et l’espace disque.", flush=True)
    time.sleep(86400 if result.returncode == 0 else 300)
