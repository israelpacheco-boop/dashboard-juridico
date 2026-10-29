@echo off
setlocal
title Dashboard Juridico - Servidor
cd /d "%~dp0"

rem --- Comprobar que Python esta disponible ---
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo Instala Python 3.10+ desde https://www.python.org/downloads/
    pause
    exit /b 1
)

rem --- Instalar dependencias si Streamlit falta (silencioso) ---
python -c "import streamlit" >nul 2>nul
if errorlevel 1 (
    echo Instalando dependencias por primera vez, un momento...
    python -m pip install --disable-pip-version-check -q -r requirements.txt
)

rem --- Lanzar Streamlit en una ventana minimizada ---
start "Dashboard Juridico" /min cmd /c "python -m streamlit run notas.py --server.headless true --server.port 8501"

rem --- Esperar a que el servidor arranque y abrir el navegador ---
timeout /t 4 /nobreak >nul
start "" "http://localhost:8501"

exit /b 0
