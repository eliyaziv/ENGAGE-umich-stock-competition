import os
from pathlib import Path
import shutil
from datetime import datetime, timedelta
import streamlit as st



def main():

    path = Path.home() / ".config" / "localStoragePy"

    for namespace in path.iterdir():
        if namespace.name.startswith("my_app_"):
            modified_timestamp = namespace.stat().st_mtime
            modified_time = datetime.fromtimestamp(modified_timestamp)

            if modified_time <= datetime.now()  - timedelta(minutes = 120):
                shutil.rmtree(namespace)
    
    with open("last_cleanup.txt", "w") as f:
        f.write(str(datetime.now().isoformat()))
