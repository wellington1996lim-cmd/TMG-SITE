import runpy
from pathlib import Path


APP_FILE = Path(__file__).with_name("tmg_app_final.py")

runpy.run_path(str(APP_FILE), run_name="__main__")
