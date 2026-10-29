# Script PowerShell para compilar SIF PyME en Windows (.exe e Instalador Setup)
$ErrorActionPreference = "Stop"

# Asegurar ejecución desde la raíz del proyecto
Set-Location "$PSScriptRoot\.."

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   SIF PyME - Compilacion de Paquete Ejecutable Windows  " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Activar entorno virtual si existe
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & .\.venv\Scripts\Activate.ps1
} elseif (Test-Path "venv\Scripts\Activate.ps1") {
    & .\venv\Scripts\Activate.ps1
}

# 1. Comprobar instalacion de PyInstaller
try {
    $null = python -m PyInstaller --version
} catch {
    Write-Host "[*] Instalando dependencias necesarias desde requirements.txt..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

# 2. Limpieza de artefactos previos
Write-Host "[*] Cerrando instancias previas si estan abiertas..." -ForegroundColor Yellow
Get-Process -Name "SIF_PyME" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "[*] Limpiando directorios previos build/ y dist/SIF_PyME..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist\SIF_PyME") { Remove-Item -Recurse -Force "dist\SIF_PyME" }

# 3. Compilacion con PyInstaller
Write-Host "[*] Iniciando compilacion con PyInstaller..." -ForegroundColor Yellow
python -m PyInstaller SIF_PyME.spec --clean --noconfirm

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host "  [EXITO] Compilacion completada con exito." -ForegroundColor Green
    Write-Host "  Ejecutable generado en: dist\SIF_PyME\SIF_PyME.exe" -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green

    # 4. Generacion del instalador .exe con Inno Setup si esta disponible
    $isccCandidates = @(
        "iscc",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
    )
    $isccExe = $null
    foreach ($cand in $isccCandidates) {
        if (Get-Command $cand -ErrorAction SilentlyContinue) {
            $isccExe = $cand
            break
        } elseif (Test-Path $cand) {
            $isccExe = $cand
            break
        }
    }

    if ($isccExe) {
        Write-Host ""
        Write-Host "[*] Compilando instalador Setup con Inno Setup..." -ForegroundColor Yellow
        $issPath = if (Test-Path "scripts\installer_windows.iss") { "scripts\installer_windows.iss" } else { "installer_windows.iss" }
        & $isccExe $issPath
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [EXITO] Instalador Windows generado: dist\SIF_PyME_v1.0.0_Windows_Setup.exe" -ForegroundColor Green
        }
    } else {
        Write-Host ""
        Write-Host "[INFO] Inno Setup no esta en el PATH. Si deseas compilar el instalador autoinstalable" -ForegroundColor Cyan
        Write-Host "       (SIF_PyME_v1.0.0_Windows_Setup.exe), instala Inno Setup (https://jrsoftware.org/isdl.php)" -ForegroundColor Cyan
        Write-Host "       y compila el script 'scripts\installer_windows.iss'." -ForegroundColor Cyan
    }
} else {
    Write-Host ""
    Write-Host "[ERROR] La compilacion con PyInstaller fallo con codigo de salida $LASTEXITCODE." -ForegroundColor Red
    exit $LASTEXITCODE
}

