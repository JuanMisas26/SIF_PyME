"""
SIF PyME — Punto de entrada Desktop (macOS / Windows / Linux)
Ejecuta FastAPI + Uvicorn en un hilo en segundo plano y muestra la interfaz
utilizando PySide6 y QWebEngineView sin requerir navegador externo.
"""

import sys
import os
import io
import time
import socket
import urllib.request
import urllib.error
import threading
from pathlib import Path

# Prevenir fallos en ejecutables sin consola (Windows GUI / PyInstaller console=False)
class NullWriter:
    def write(self, s):
        pass

    def flush(self):
        pass

    def isatty(self):
        return False


if sys.stdout is None or not hasattr(sys.stdout, "isatty"):
    sys.stdout = NullWriter()
if sys.stderr is None or not hasattr(sys.stderr, "isatty"):
    sys.stderr = NullWriter()
if sys.stdin is None:
    sys.stdin = io.StringIO()

# ==============================================================================
# Configuración temprana de entorno y plugins de Qt (PyInstaller macOS / Windows)
# Debe ejecutarse antes de importar PySide6 para asegurar resolución de DLLs y plugins QPA
# ==============================================================================
def _configurar_entorno_qt():
    _is_frozen = getattr(sys, "frozen", False)

    if sys.platform == "win32":
        # En Windows empaquetado o con entornos como Anaconda en PATH,
        # registrar carpetas de PySide6 y Shiboken con add_dll_directory y prioridad en PATH
        _candidate_dirs = []
        if hasattr(sys, "_MEIPASS"):
            _base = Path(sys._MEIPASS).resolve()
            _candidate_dirs.extend([_base / "PySide6", _base / "shiboken6", _base])
        _exe_dir = Path(sys.executable).parent.resolve()
        _candidate_dirs.extend([
            _exe_dir / "_internal" / "PySide6",
            _exe_dir / "_internal" / "shiboken6",
            _exe_dir / "_internal",
            _exe_dir / "PySide6",
            _exe_dir / "shiboken6",
            _exe_dir,
        ])
        for _d in _candidate_dirs:
            if _d.is_dir():
                try:
                    os.add_dll_directory(str(_d))
                except Exception:
                    pass
                os.environ["PATH"] = str(_d) + os.pathsep + os.environ.get("PATH", "")

    # Localización y registro del directorio de plugins de Qt (cocoa en macOS, qwindows en Windows)
    if _is_frozen:
        _candidatos_plugins = []
        if hasattr(sys, "_MEIPASS"):
            _m = Path(sys._MEIPASS).resolve()
            _candidatos_plugins.extend([
                _m / "PySide6" / "Qt" / "plugins",
                _m / "PySide6" / "plugins",
                _m / "Qt" / "plugins",
                _m / "plugins",
            ])
        _exe_dir = Path(sys.executable).parent.resolve()
        _candidatos_plugins.extend([
            _exe_dir / "PySide6" / "Qt" / "plugins",
            _exe_dir / "PySide6" / "plugins",
            _exe_dir / "plugins",
            _exe_dir / "_internal" / "PySide6" / "Qt" / "plugins",
            _exe_dir / "_internal" / "PySide6" / "plugins",
        ])
        if sys.platform == "darwin":
            # Estructura del bundle macOS: Contents/MacOS/<exe>
            _contents = _exe_dir.parent
            _candidatos_plugins.extend([
                _contents / "Frameworks" / "PySide6" / "Qt" / "plugins",
                _contents / "Frameworks" / "PySide6" / "plugins",
                _contents / "Resources" / "PySide6" / "Qt" / "plugins",
                _contents / "Resources" / "PySide6" / "plugins",
                _contents / "PlugIns",
            ])

        for _p in _candidatos_plugins:
            if _p.is_dir() and ((_p / "platforms").is_dir() or any(_p.glob("platforms/*"))):
                os.environ["QT_PLUGIN_PATH"] = str(_p)
                break

_configurar_entorno_qt()

from PySide6.QtCore import Qt, QUrl, QTimer, QCoreApplication
from PySide6.QtGui import QIcon, QDesktopServices, QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
    QWebEngineDownloadRequest,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

# Registrar la ruta de plugins en QCoreApplication si fue detectada
if "QT_PLUGIN_PATH" in os.environ:
    try:
        QCoreApplication.addLibraryPath(os.environ["QT_PLUGIN_PATH"])
    except Exception:
        pass

import uvicorn
from app.paths import PDF_BASE_DIR, STATIC_DIR, get_pdf_storage_dir

def obtener_puerto_libre() -> int:
    """Encuentra y reserva temporalmente un puerto libre en localhost (127.0.0.1)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


class ServidorUvicorn(threading.Thread):
    """Hilo secundario para alojar y servir la aplicación FastAPI con Uvicorn."""

    def __init__(self, host: str, port: int):
        super().__init__(daemon=True, name="UvicornBackendThread")
        self.host = host
        self.port = port
        self.config = uvicorn.Config(
            app="main:app",
            host=self.host,
            port=self.port,
            log_level="warning",
            loop="asyncio",
            lifespan="on",
            log_config=None,
        )
        self.server = uvicorn.Server(config=self.config)

    def run(self):
        self.server.run()

    def detener(self):
        """Notifica a Uvicorn el cese de actividad de forma limpia."""
        self.server.should_exit = True


def esperar_servidor_listo(url: str, timeout_segundos: float = 8.0) -> bool:
    """Verifica periódicamente que el servidor HTTP responde antes de cargar la vista."""
    inicio = time.time()
    while time.time() - inicio < timeout_segundos:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.1)
    return False


class PaginaWebEnginePersonalizada(QWebEnginePage):
    """
    Página web personalizada para interceptar ventanas emergentes (window.open)
    y redireccionar enlaces externos o descargas de PDF al visor nativo de macOS.
    """

    def __init__(self, parent=None, host_local="127.0.0.1", puerto=8000):
        super().__init__(parent)
        self.host_local = host_local
        self.puerto = puerto

    def createWindow(self, window_type: QWebEnginePage.WebWindowType) -> QWebEnginePage:
        """
        Intercepta llamadas JavaScript a window.open() (ej. visualización o descarga de PDF).
        Crea una página transitoria para capturar la URL y abrirla en la app nativa o misma ventana.
        """
        pagina_temporal = QWebEnginePage(self.profile(), self)

        def al_cambiar_url(url: QUrl):
            url_str = url.toString()
            # Si apunta a la descarga de PDF, delegar a abrir_pdf_o_externo
            if "/pdf" in url_str or url_str.lower().endswith(".pdf"):
                self.abrir_url_externa(url)
            else:
                # Cargar en la ventana principal
                self.view().load(url)
            pagina_temporal.deleteLater()

        pagina_temporal.urlChanged.connect(al_cambiar_url)
        return pagina_temporal

    def acceptNavigationRequest(
        self, url: QUrl, nav_type: QWebEnginePage.NavigationType, is_main_frame: bool
    ) -> bool:
        """Filtra y valida destinos de navegación."""
        url_str = url.toString()
        es_local = (
            url.host() in ("127.0.0.1", "localhost")
            and url.port() == self.puerto
        ) or url.scheme() == "data"

        # Si el usuario hace clic en un enlace externo a la app local, abrir en el navegador del sistema
        if nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked and not es_local:
            QDesktopServices.openUrl(url)
            return False

        # Si es un enlace directo a descargar/ver PDF
        if "/pdf" in url.path() and nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            self.abrir_url_externa(url)
            return False

        return super().acceptNavigationRequest(url, nav_type, is_main_frame)

    def abrir_url_externa(self, url: QUrl):
        """Descarga o abre el recurso con la aplicación nativa asociada en macOS."""
        QDesktopServices.openUrl(url)


class VentanaPrincipal(QMainWindow):
    """Ventana principal de escritorio que encapsula la aplicación en PySide6."""

    def __init__(self, servidor: ServidorUvicorn, host: str, port: int):
        super().__init__()
        self.servidor = servidor
        self.host = host
        self.port = port
        self.url_base = f"http://{self.host}:{self.port}"

        self.setWindowTitle("SIF PyME — Facturación Local")
        self.resize(1240, 820)
        self.setMinimumSize(960, 640)

        # Asignar icono de ventana
        ruta_icono = STATIC_DIR / "icon.ico"
        if not ruta_icono.exists():
            ruta_icono = STATIC_DIR / "icon.icns"
        if ruta_icono.exists():
            self.setWindowIcon(QIcon(str(ruta_icono)))

        # Centrar ventana en la pantalla activa
        pantalla = QApplication.primaryScreen().availableGeometry()
        x = (pantalla.width() - self.width()) // 2
        y = (pantalla.height() - self.height()) // 2
        self.move(x, y)

        self._configurar_webengine()
        self._configurar_menus()

    def _configurar_webengine(self):
        """Inicializa la vista y el perfil de QWebEngine con gestión de descargas."""
        self.webview = QWebEngineView(self)
        self.setCentralWidget(self.webview)

        perfil = QWebEngineProfile.defaultProfile()
        # Activar soporte de almacenamiento local e inspección
        perfil.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalStorageEnabled, True
        )
        perfil.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True
        )

        # Manejador de descargas nativo de WebEngine
        perfil.downloadRequested.connect(self._al_solicitar_descarga)

        # Asignar página personalizada
        self.pagina_personalizada = PaginaWebEnginePersonalizada(
            self.webview, host_local=self.host, puerto=self.port
        )
        self.webview.setPage(self.pagina_personalizada)

        # Cargar URL de la aplicación
        self.webview.load(QUrl(self.url_base))

    def _al_solicitar_descarga(self, descarga: QWebEngineDownloadRequest):
        """
        Gestiona la descarga de archivos (PDFs de facturas y backups).
        Guarda en el directorio predeterminado y abre con Vista Previa / visor nativo.
        """
        nombre_archivo = descarga.downloadFileName()
        directorio_destino = str(get_pdf_storage_dir())
        ruta_completa = Path(directorio_destino) / nombre_archivo

        descarga.setDownloadDirectory(directorio_destino)
        descarga.setDownloadFileName(nombre_archivo)
        descarga.accept()

        def al_terminar_descarga():
            if ruta_completa.exists():
                # Abre en macOS con Preview.app o visor predeterminado
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta_completa)))

        descarga.isFinishedChanged.connect(al_terminar_descarga)

    def _configurar_menus(self):
        """Crea la barra de menú nativa de macOS."""
        menubar = self.menuBar()

        # Menú Archivo
        menu_archivo = menubar.addMenu("Archivo")
        
        accion_nueva = QAction("Nueva Factura", self)
        accion_nueva.setShortcut(QKeySequence("Ctrl+N"))
        accion_nueva.triggered.connect(lambda: self.webview.load(QUrl(f"{self.url_base}/nueva-factura")))
        menu_archivo.addAction(accion_nueva)

        accion_nuevo_presupuesto = QAction("Nuevo Presupuesto…", self)
        accion_nuevo_presupuesto.triggered.connect(lambda: self.webview.load(QUrl(f"{self.url_base}/nuevo-presupuesto")))
        menu_archivo.addAction(accion_nuevo_presupuesto)

        accion_recargar = QAction("Recargar Página", self)
        accion_recargar.setShortcut(QKeySequence.Refresh)
        accion_recargar.triggered.connect(self.webview.reload)
        menu_archivo.addAction(accion_recargar)

        menu_archivo.addSeparator()

        accion_salir = QAction("Cerrar Ventana", self)
        accion_salir.setShortcut(QKeySequence.Quit)
        accion_salir.triggered.connect(self.close)
        menu_archivo.addAction(accion_salir)

        # Menú Navegación
        menu_nav = menubar.addMenu("Navegación")

        accion_dashboard = QAction("Facturas", self)
        accion_dashboard.triggered.connect(lambda: self.webview.load(QUrl(f"{self.url_base}/")))
        menu_nav.addAction(accion_dashboard)

        accion_presupuestos = QAction("Presupuestos", self)
        accion_presupuestos.triggered.connect(lambda: self.webview.load(QUrl(f"{self.url_base}/presupuestos")))
        menu_nav.addAction(accion_presupuestos)

        accion_clientes = QAction("Clientes", self)
        accion_clientes.triggered.connect(lambda: self.webview.load(QUrl(f"{self.url_base}/clientes")))
        menu_nav.addAction(accion_clientes)

        accion_catalogo = QAction("Catálogo", self)
        accion_catalogo.triggered.connect(lambda: self.webview.load(QUrl(f"{self.url_base}/productos")))
        menu_nav.addAction(accion_catalogo)

        accion_config = QAction("Ajustes…", self)
        accion_config.setShortcut(QKeySequence("Ctrl+,"))
        accion_config.triggered.connect(lambda: self.webview.load(QUrl(f"{self.url_base}/configuracion")))
        menu_nav.addAction(accion_config)

        # Menú Ayuda
        menu_ayuda = menubar.addMenu("Ayuda")
        accion_acerca = QAction("Acerca de SIF PyME", self)
        accion_acerca.triggered.connect(self._mostrar_acerca_de)
        menu_ayuda.addAction(accion_acerca)

    def _mostrar_acerca_de(self):
        QMessageBox.about(
            self,
            "Acerca de SIF PyME",
            "<b>SIF PyME — Sistema de Facturación Local</b><br><br>"
            "Versión 1.0.0<br>"
            "Arquitectura: FastAPI + SQLite + PySide6 WebEngine.<br>"
            "Todos los datos residen localmente en su equipo de forma privada y segura.",
        )

    def closeEvent(self, event):
        """Detiene el backend de Uvicorn al cerrar la ventana de la aplicación."""
        if self.servidor:
            self.servidor.detener()
        event.accept()


def main():
    # En Windows, registrar AppUserModelID para agrupar e identificar la ventana en la barra de tareas
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("sifpyme.facturacion.local.1.0")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("SIF PyME")
    app.setApplicationDisplayName("SIF PyME")
    app.setOrganizationName("SIF")
    app.setOrganizationDomain("sifpyme.local")

    # Asignar icono a nivel de aplicación (barra de tareas y diálogos)
    ruta_icono = STATIC_DIR / "icon.ico"
    if not ruta_icono.exists():
        ruta_icono = STATIC_DIR / "icon.icns"
    if ruta_icono.exists():
        app.setWindowIcon(QIcon(str(ruta_icono)))

    host = "127.0.0.1"
    port = obtener_puerto_libre()

    # Arrancar Uvicorn en hilo secundario (inicializa BD en lifespan)
    servidor = ServidorUvicorn(host=host, port=port)
    servidor.start()

    # Esperar a que el backend esté listo
    url_base = f"http://{host}:{port}/"
    if not esperar_servidor_listo(url_base, timeout_segundos=10.0):
        QMessageBox.critical(
            None,
            "Error de inicio",
            f"No se pudo iniciar el servicio local en el puerto {port}.\n"
            "Verifique los permisos de red local e inténtelo de nuevo.",
        )
        servidor.detener()
        sys.exit(1)

    # Crear y mostrar ventana principal
    ventana = VentanaPrincipal(servidor=servidor, host=host, port=port)
    ventana.show()

    # Asegurar apagado del servidor al terminar Qt
    app.aboutToQuit.connect(servidor.detener)

    codigo_salida = app.exec()
    servidor.detener()
    sys.exit(codigo_salida)


if __name__ == "__main__":
    main()

