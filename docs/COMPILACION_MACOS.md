# Guía de Compilación en macOS (Terminal) — SIF PyME

Guía paso a paso para compilar la aplicación en macOS directamente desde la aplicación **Terminal**, sin depender de VS Code ni de entornos gráficos de desarrollo.

---

## 1. Requisitos Previos

Abre la aplicación **Terminal** en tu Mac (`Cmd + Espacio`, escribe `Terminal` y pulsa `Enter`).

### A. Herramientas de línea de comandos de Apple (Xcode CLI)
Instala las herramientas de compilación básicas de Apple si aún no las tienes:
```bash
xcode-select --install
```
*(Si ya están instaladas, el sistema te avisará de que ya se encuentran presentes. Este paquete incluye también `git`).*

### B. Python 3.10 o superior
Verifica que cuentas con una versión compatible de Python:
```bash
python3 --version
```

> **¿No tienes Python instalado en el Mac?**
> Puedes instalarlo rápidamente con cualquiera de estas opciones:
> 
> * **Vía instalador oficial (Directo en Terminal)**:
>   ```bash
>   curl -O https://www.python.org/ftp/python/3.11.9/python-3.11.9-macos11.pkg
>   sudo installer -pkg python-3.11.9-macos11.pkg -target /
>   rm python-3.11.9-macos11.pkg
>   ```
> * **Vía Homebrew**:
>   ```bash
>   brew install python@3.11
>   ```
> * O descargando el instalador gráfico `.pkg` desde [python.org/downloads](https://www.python.org/downloads/).

---

## 2. Obtener el Código del Proyecto (Clonar Repositorio)

Si aún no tienes el proyecto en tu Mac, clónalo directamente desde GitHub:

```bash
# Navegar a donde quieras guardar el proyecto (por ejemplo, el Escritorio)
cd ~/Desktop

# Clonar el repositorio
git clone https://github.com/JuanMisas26/factura.git

# Entrar en la carpeta del proyecto
cd factura
```

*(Si ya tienes la carpeta transferida o descargada, simplemente accede a ella con `cd /ruta/donde/este/factura`)*.

---

## 3. Preparación del Entorno Virtual y Dependencias

Crea un entorno virtual aislado e instala todas las dependencias requeridas:

```bash
# 1. Crear entorno virtual
python3 -m venv .venv

# 2. Activar el entorno virtual
source .venv/bin/activate

# 3. Actualizar el gestor de paquetes pip
pip install --upgrade pip

# 4. Instalar todas las dependencias del proyecto (incluye PySide6, PyInstaller y Pillow)
pip install -r requirements.txt
```

---

## 4. Compilación Automatizada

El repositorio incluye un script preparado para compilar y empaquetar el software en macOS:

```bash
# Asignar permisos de ejecución al script (solo la primera vez)
chmod +x build_macos.sh

# Ejecutar el empaquetado
./build_macos.sh
```

### ¿Qué realiza este script automáticamente?
1. Limpia compilaciones anteriores (`build/` y `dist/`).
2. Verifica dependencias y activa el entorno virtual `.venv`.
3. Ejecuta PyInstaller con el archivo de especificación multiplataforma `SIF_PyME.spec`.
4. Firma la aplicación de forma local (firma ad-hoc).
5. Genera la imagen de disco instalable `.dmg` con acceso directo a `/Applications`.

---

## 5. Archivos Generados

Una vez finalizado el proceso, los artefactos estarán dentro del directorio `dist/`:

| Archivo | Tipo | Descripción |
|---|---|---|
| `dist/SIF PyME.app` | Paquete de aplicación | Ejecutable nativo de macOS listo para abrir. |
| `dist/SIF_PyME.dmg` | Imagen de disco instalable | Instalador estándar con arrastre a la carpeta Aplicaciones. |

Para abrir la carpeta con los ejecutables en el **Finder**:
```bash
open dist/
```

---

## 6. Resolución de Problemas y Permisos

### Gatekeeper bloquea la apertura ("No se puede abrir porque el desarrollador no ha sido verificado")
Al compilarse en local sin una cuenta de pago de Apple Developer Program, macOS puede marcar la aplicación con atributo de cuarentena.

Puedes desbloquearla fácilmente con **cualquiera de estas dos opciones**:

* **Opción A (Terminal - Recomendada)**:
  ```bash
  xattr -cr "dist/SIF PyME.app"
  ```
  *(O si ya la moviste a Aplicaciones: `xattr -cr "/Applications/SIF PyME.app"`)*.

* **Opción B (Finder)**:
  Haz clic derecho sobre `SIF PyME.app` > selecciona **Abrir** > pulsa en el botón **Abrir** en el cuadro de diálogo.

---

## 7. Firma Oficial con Apple Developer ID (Opcional)

Si dispones de un certificado oficial de desarrollador de Apple, puedes firmar la aplicación antes de ejecutar el script exportando tu identidad:

```bash
export APPLE_SIGNING_IDENTITY="Developer ID Application: Tu Nombre (TEAMID)"
./build_macos.sh
```

