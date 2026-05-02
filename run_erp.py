import os
import sys
import streamlit.web.cli as stcli

# Programın .exe olarak mı yoksa normal mi çalıştığını anlar
if getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))

app_path = os.path.join(current_dir, "pallet_app.py")

if __name__ == "__main__":
    # Tarayıcıyı tetikler ve çalıştırır
    sys.argv = ["streamlit", "run", app_path, "--server.headless=false", "--browser.gatherUsageStats=false"]
    sys.exit(stcli.main())