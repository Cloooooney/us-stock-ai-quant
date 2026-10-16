@echo off
rem Double-click to open the analysis app in your browser. Close this window to stop it.
cd /d "%~dp0"
".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
".venv\Scripts\python.exe" -m streamlit run app\main.py --browser.gatherUsageStats false
pause
