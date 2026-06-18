@echo off
title ProtoDeus Boost — Compilador
color 0A
echo.
echo  ========================================
echo   PROTODEUS BOOST — Generador de .exe
echo  ========================================
echo.

:: Usar ruta completa de Python 3.11
set PYTHON=%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe
set PIP=%PYTHON% -m pip
set PYINSTALLER=%PYTHON% -m PyInstaller

:: Verificar Python
%PYTHON% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no encontrado en la ruta especificada.
    echo         Ruta: %PYTHON%
    pause
    exit /b 1
)

echo [1/4] Instalando dependencias...
%PIP% install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] No se pudieron instalar las dependencias.
    pause
    exit /b 1
)
echo       OK

echo.
echo [2/4] Generando icono .ico...
%PYTHON% make_icon.py
echo       OK

echo.
echo [3/4] Compilando con PyInstaller...
%PYINSTALLER% ^
    --onefile ^
    --noconsole ^
    --uac-admin ^
    --name "ProtoDeusBoost" ^
    --icon "assets\icon.ico" ^
    --add-data "assets;assets" ^
    --hidden-import=customtkinter ^
    --hidden-import=psutil ^
    --hidden-import=wmi ^
    --hidden-import=win32com.client ^
    --hidden-import=pywintypes ^
    --collect-all customtkinter ^
    main.py

if %errorlevel% neq 0 (
    echo [ERROR] La compilacion fallo. Revisa los mensajes anteriores.
    pause
    exit /b 1
)

echo.
echo [4/4] Limpiando archivos temporales de compilacion...
if exist "build" rmdir /s /q "build"
if exist "ProtoDeusBoost.spec" del "ProtoDeusBoost.spec"
echo       OK

echo.
echo  ========================================
echo   EXITO! El archivo .exe esta en:
echo   dist\ProtoDeusBoost.exe
echo  ========================================
echo.
pause
