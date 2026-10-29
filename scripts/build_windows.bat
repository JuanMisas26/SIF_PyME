@echo off
chcp 65001 > nul
cd /d "%~dp0\.."

echo ========================================================
echo   SIF PyME — Compilación de Paquete Ejecutable Windows
echo ========================================================
echo.

:: Activar entorno virtual si existe
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

:: Verificar si pyinstaller está instalado
python -m PyInstaller --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] PyInstaller no está instalado en el entorno de Python actual.
    echo [*] Instalando dependencias necesarias...
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] No se pudieron instalar las dependencias.
        pause
        exit /b 1
    )
)

echo [*] Cerrando instancias previas si están abiertas...
taskkill /f /im SIF_PyME.exe >nul 2>&1

echo [*] Limpiando carpetas previas build/ y dist/ ...
if exist build rmdir /s /q build
if exist dist\SIF_PyME rmdir /s /q dist\SIF_PyME

echo [*] Compilando aplicación con PyInstaller (SIF_PyME.spec)...
python -m PyInstaller SIF_PyME.spec --clean --noconfirm

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================================
    echo   [EXITO] Compilación completada con éxito.
    echo   Ubicación del ejecutable:
    echo   dist\SIF_PyME\SIF_PyME.exe
    echo ========================================================

    :: Verificar si Inno Setup está instalado
    set "ISCC_EXE="
    if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles%\Inno Setup 6\ISCC.exe"
    if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

    if defined ISCC_EXE (
        echo.
        echo [*] Generando instalador Setup con Inno Setup...
        if exist scripts\installer_windows.iss (
            "%ISCC_EXE%" scripts\installer_windows.iss
        ) else (
            "%ISCC_EXE%" installer_windows.iss
        )
        if %ERRORLEVEL% equ 0 (
            echo   [EXITO] Instalador creado en dist\SIF_PyME_v1.0.0_Windows_Setup.exe
        )
    ) else (
        echo.
        echo [INFO] Inno Setup no detectado en las rutas estándar.
        echo        Para generar el instalador instalable (Setup .exe), instala Inno Setup 6.
    )
) else (
    echo.
    echo [ERROR] La compilación falló. Revisa los mensajes de error anteriores.
    pause
    exit /b %ERRORLEVEL%
)

