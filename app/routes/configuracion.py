import os
import sys
import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException

from app.database import get_configuracion, set_configuracion
from app.models import ConfiguracionData, ConfiguracionResponse, OnboardingRequest
from app.paths import get_suggested_storage_paths, get_pdf_storage_dir, DESKTOP_DIR

router = APIRouter()


def _evaluar_configuracion(config: dict[str, str]) -> tuple[bool, list[str]]:
    faltantes = []
    if not config.get("nombre", "").strip():
        faltantes.append("Nombre o Razón Social")
    if not config.get("nif", "").strip():
        faltantes.append("NIF/CIF")
    return len(faltantes) == 0, faltantes


def _crear_acceso_directo_escritorio() -> tuple[bool, str]:
    """Crea un Alias de macOS o acceso directo en el Escritorio."""
    if sys.platform == "darwin":
        app_path = "/Applications/SIF PyME.app"
        script = f'''
        tell application "Finder"
            try
                set appFile to POSIX file "{app_path}" as alias
                set deskFolder to path to desktop folder
                make new alias file to appFile at deskFolder with properties {{name:"SIF PyME"}}
            end try
        end tell
        '''
        try:
            if Path(app_path).exists():
                res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                if res.returncode == 0:
                    return True, "Alias de macOS creado en el Escritorio"
            
            # Fallback a enlace simbólico si la app no está en /Applications o si osascript falla
            desktop_link = DESKTOP_DIR / "SIF PyME"
            if not desktop_link.exists():
                target = app_path if Path(app_path).exists() else sys.argv[0]
                os.symlink(target, desktop_link)
                return True, "Enlace directo creado en el Escritorio"
            return True, "El acceso directo ya existe en el Escritorio"
        except Exception as e:
            return False, f"No se pudo crear el acceso directo: {str(e)}"
    elif sys.platform == "win32":
        try:
            exe_target = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath("desktop.py")
            shortcut_path = DESKTOP_DIR / "SIF PyME.lnk"
            ps_script = f'$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut("{shortcut_path}"); $s.TargetPath = "{exe_target}"; $s.Save()'
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True)
            return True, "Acceso directo creado en el Escritorio de Windows"
        except Exception as e:
            return False, f"Error al crear acceso directo en Windows: {str(e)}"
    else:
        return True, "Plataforma no requiere alias de escritorio"


@router.get("/configuracion", response_model=ConfiguracionResponse)
def obtener_configuracion():
    """Obtiene la configuración actual del emisor y los parámetros por defecto."""
    config_raw = get_configuracion()
    
    # Cast tipos numéricos si existen
    iva = float(config_raw.get("iva_defecto", 21.0)) if config_raw.get("iva_defecto") else 21.0
    irpf = float(config_raw.get("irpf_defecto", 0.0)) if config_raw.get("irpf_defecto") else 0.0
    
    datos = ConfiguracionData(
        nombre=config_raw.get("nombre", ""),
        nif=config_raw.get("nif", ""),
        direccion=config_raw.get("direccion", ""),
        codigo_postal=config_raw.get("codigo_postal", ""),
        ciudad=config_raw.get("ciudad", ""),
        provincia=config_raw.get("provincia", ""),
        telefono=config_raw.get("telefono", ""),
        email=config_raw.get("email", ""),
        web=config_raw.get("web", ""),
        iban=config_raw.get("iban", ""),
        serie_defecto=config_raw.get("serie_defecto", "Factura Nº"),
        numero_inicio_factura=int(config_raw.get("numero_inicio_factura", 1)) if (config_raw.get("numero_inicio_factura") and str(config_raw.get("numero_inicio_factura")).isdigit()) else 1,
        serie_sin_iva=config_raw.get("serie_sin_iva", "Factura Sin IVA Nº"),
        numero_inicio_factura_sin_iva=int(config_raw.get("numero_inicio_factura_sin_iva", 1)) if (config_raw.get("numero_inicio_factura_sin_iva") and str(config_raw.get("numero_inicio_factura_sin_iva")).isdigit()) else 1,
        iva_defecto=iva,
        irpf_defecto=irpf,
        presupuesto_instagram=config_raw.get("presupuesto_instagram", os.getenv("DEFAULT_PRESUPUESTO_INSTAGRAM", "")),
        presupuesto_email=config_raw.get("presupuesto_email", os.getenv("DEFAULT_PRESUPUESTO_EMAIL", "")),
        presupuesto_bienvenida_titulo=config_raw.get("presupuesto_bienvenida_titulo", "Bienvenidos"),
        presupuesto_bienvenida_subtitulo=config_raw.get("presupuesto_bienvenida_subtitulo", "Propuesta de servicios y condiciones comerciales"),
        presupuesto_bienvenida_texto=config_raw.get("presupuesto_bienvenida_texto", ""),
        presupuesto_proceso_titulo=config_raw.get("presupuesto_proceso_titulo", "Proceso de trabajo"),
        presupuesto_proceso_subtitulo=config_raw.get("presupuesto_proceso_subtitulo", "Fases del proyecto y tiempos de ejecución"),
        proceso_fase1_titulo=config_raw.get("proceso_fase1_titulo", "Planificación y requerimientos"),
        proceso_fase1_puntos=config_raw.get("proceso_fase1_puntos", "• Definición del alcance\n• Elaboración de propuesta\n• Aprobación y confirmación\n• Calendario de trabajo"),
        proceso_fase2_titulo=config_raw.get("proceso_fase2_titulo", "Desarrollo inicial"),
        proceso_fase2_puntos=config_raw.get("proceso_fase2_puntos", "• Ejecución de tareas iniciales\n• Presentación de avances\n• Selección de opciones\n• Primera revisión"),
        proceso_fase3_titulo=config_raw.get("proceso_fase3_titulo", "Revisiones y ajustes"),
        proceso_fase3_puntos=config_raw.get("proceso_fase3_puntos", "• Aplicación de comentarios\n• Validación de especificaciones\n• Control de calidad\n• Aprobación final"),
        proceso_fase4_titulo=config_raw.get("proceso_fase4_titulo", "Entrega y cierre"),
        proceso_fase4_puntos=config_raw.get("proceso_fase4_puntos", "• Puesta en marcha / Entrega final\n• Validación de conformidad\n• Soporte y garantía\n• Facturación final"),
        presupuesto_proceso_cierre=config_raw.get("presupuesto_proceso_cierre", ""),
        factura_condiciones=config_raw.get("factura_condiciones", ""),
        presupuesto_condiciones=config_raw.get("presupuesto_condiciones", ""),
        pdf_storage_dir=config_raw.get("pdf_storage_dir", str(get_pdf_storage_dir())),
        factura_incluir_portada=config_raw.get("factura_incluir_portada", "false"),
        onboarding_completado=config_raw.get("onboarding_completado", "false")
    )
    
    es_valida, faltantes = _evaluar_configuracion(config_raw)
    return ConfiguracionResponse(
        datos=datos,
        es_valida=es_valida,
        campos_faltantes=faltantes
    )


@router.put("/configuracion", response_model=ConfiguracionResponse)
@router.post("/configuracion", response_model=ConfiguracionResponse)
def guardar_configuracion(config_in: ConfiguracionData):
    """Guarda o actualiza la configuración del emisor y parámetros."""
    valores = {
        "nombre": config_in.nombre or "",
        "nif": config_in.nif or "",
        "direccion": config_in.direccion or "",
        "codigo_postal": config_in.codigo_postal or "",
        "ciudad": config_in.ciudad or "",
        "provincia": config_in.provincia or "",
        "telefono": config_in.telefono or "",
        "email": config_in.email or "",
        "web": config_in.web or "",
        "iban": config_in.iban or "",
        "serie_defecto": config_in.serie_defecto or "Factura Nº",
        "numero_inicio_factura": str(config_in.numero_inicio_factura if config_in.numero_inicio_factura and config_in.numero_inicio_factura >= 1 else 1),
        "serie_sin_iva": config_in.serie_sin_iva or "Factura Sin IVA Nº",
        "numero_inicio_factura_sin_iva": str(config_in.numero_inicio_factura_sin_iva if config_in.numero_inicio_factura_sin_iva and config_in.numero_inicio_factura_sin_iva >= 1 else 1),
        "iva_defecto": str(config_in.iva_defecto if config_in.iva_defecto is not None else 21.0),
        "irpf_defecto": str(config_in.irpf_defecto if config_in.irpf_defecto is not None else 0.0),
        "presupuesto_instagram": config_in.presupuesto_instagram or "",
        "presupuesto_email": config_in.presupuesto_email or "",
        "presupuesto_bienvenida_titulo": config_in.presupuesto_bienvenida_titulo or "",
        "presupuesto_bienvenida_subtitulo": config_in.presupuesto_bienvenida_subtitulo or "",
        "presupuesto_bienvenida_texto": config_in.presupuesto_bienvenida_texto or "",
        "presupuesto_proceso_titulo": config_in.presupuesto_proceso_titulo or "",
        "presupuesto_proceso_subtitulo": config_in.presupuesto_proceso_subtitulo or "",
        "proceso_fase1_titulo": config_in.proceso_fase1_titulo or "",
        "proceso_fase1_puntos": config_in.proceso_fase1_puntos or "",
        "proceso_fase2_titulo": config_in.proceso_fase2_titulo or "",
        "proceso_fase2_puntos": config_in.proceso_fase2_puntos or "",
        "proceso_fase3_titulo": config_in.proceso_fase3_titulo or "",
        "proceso_fase3_puntos": config_in.proceso_fase3_puntos or "",
        "proceso_fase4_titulo": config_in.proceso_fase4_titulo or "",
        "proceso_fase4_puntos": config_in.proceso_fase4_puntos or "",
        "presupuesto_proceso_cierre": config_in.presupuesto_proceso_cierre or "",
        "factura_condiciones": config_in.factura_condiciones or "",
        "presupuesto_condiciones": config_in.presupuesto_condiciones or "",
        "factura_incluir_portada": config_in.factura_incluir_portada or "false",
    }

    if config_in.pdf_storage_dir:
        # Asegurar que el directorio sea accesible y válido
        p = Path(config_in.pdf_storage_dir).expanduser().resolve()
        try:
            p.mkdir(parents=True, exist_ok=True)
            valores["pdf_storage_dir"] = str(p)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"No se pudo crear o acceder a la carpeta: {str(e)}")

    if config_in.onboarding_completado:
        valores["onboarding_completado"] = config_in.onboarding_completado
    
    set_configuracion(valores)
    
    config_guardada = get_configuracion()
    es_valida, faltantes = _evaluar_configuracion(config_guardada)
    
    return ConfiguracionResponse(
        datos=config_in,
        es_valida=es_valida,
        campos_faltantes=faltantes
    )


@router.get("/configuracion/rutas-sugeridas")
def obtener_rutas_sugeridas():
    """Devuelve las opciones sugeridas para almacenamiento de facturas y estado del sistema."""
    return get_suggested_storage_paths()


@router.post("/configuracion/crear-acceso-directo")
def crear_acceso_directo():
    """Crea el acceso directo / alias en el Escritorio del usuario."""
    exito, mensaje = _crear_acceso_directo_escritorio()
    return {"ok": exito, "mensaje": mensaje}


@router.post("/configuracion/onboarding")
def completar_onboarding(datos: OnboardingRequest):
    """
    Guarda los datos del asistente de primera apertura (Onboarding):
    - Datos fiscales básicos del emisor
    - Carpeta de almacenamiento para PDFs de facturas
    - Creación opcional del acceso directo en el Escritorio
    """
    valores = {
        "nombre": datos.nombre.strip(),
        "nif": datos.nif.strip(),
        "direccion": (datos.direccion or "").strip(),
        "codigo_postal": (datos.codigo_postal or "").strip(),
        "ciudad": (datos.ciudad or "").strip(),
        "provincia": (datos.provincia or "").strip(),
        "email": (datos.email or "").strip(),
        "telefono": (datos.telefono or "").strip(),
        "iban": (datos.iban or "").strip(),
        "onboarding_completado": "true"
    }

    # Procesar carpeta de facturas
    ruta_almacenamiento = datos.pdf_storage_dir.strip() if datos.pdf_storage_dir else ""
    if ruta_almacenamiento:
        p = Path(ruta_almacenamiento).expanduser().resolve()
        try:
            p.mkdir(parents=True, exist_ok=True)
            valores["pdf_storage_dir"] = str(p)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"No se pudo acceder a la carpeta de facturas: {str(e)}")
    
    set_configuracion(valores)

    # Crear acceso directo en el escritorio si el usuario lo solicitó
    alias_msg = "Omitido"
    if datos.crear_acceso_escritorio:
        _, alias_msg = _crear_acceso_directo_escritorio()

    return {
        "ok": True,
        "mensaje": "Configuración inicial guardada con éxito",
        "alias_escritorio": alias_msg,
        "pdf_storage_dir": valores.get("pdf_storage_dir", str(get_pdf_storage_dir()))
    }


@router.get("/configuracion/presupuesto")
def obtener_configuracion_presupuesto():
    """Obtiene los textos y parámetros editoriales de los documentos."""
    cfg = get_configuracion()
    return {
        "presupuesto_instagram": cfg.get("presupuesto_instagram", os.getenv("DEFAULT_PRESUPUESTO_INSTAGRAM", "")),
        "presupuesto_email": cfg.get("presupuesto_email") or cfg.get("email", os.getenv("DEFAULT_PRESUPUESTO_EMAIL", "")),
        "presupuesto_bienvenida_titulo": cfg.get("presupuesto_bienvenida_titulo", "Bienvenidos"),
        "presupuesto_bienvenida_subtitulo": cfg.get("presupuesto_bienvenida_subtitulo", "Propuesta de servicios y condiciones comerciales"),
        "presupuesto_bienvenida_texto": cfg.get("presupuesto_bienvenida_texto", ""),
        "presupuesto_proceso_titulo": cfg.get("presupuesto_proceso_titulo", "Proceso de trabajo"),
        "presupuesto_proceso_subtitulo": cfg.get("presupuesto_proceso_subtitulo", "Fases del proyecto y tiempos de ejecución"),
        "proceso_fase1_titulo": cfg.get("proceso_fase1_titulo", "Planificación y requerimientos"),
        "proceso_fase1_puntos": cfg.get("proceso_fase1_puntos", "• Definición del alcance\n• Elaboración de propuesta\n• Aprobación y confirmación\n• Calendario de trabajo"),
        "proceso_fase2_titulo": cfg.get("proceso_fase2_titulo", "Desarrollo inicial"),
        "proceso_fase2_puntos": cfg.get("proceso_fase2_puntos", "• Ejecución de tareas iniciales\n• Presentación de avances\n• Selección de opciones\n• Primera revisión"),
        "proceso_fase3_titulo": cfg.get("proceso_fase3_titulo", "Revisiones y ajustes"),
        "proceso_fase3_puntos": cfg.get("proceso_fase3_puntos", "• Aplicación de comentarios\n• Validación de especificaciones\n• Control de calidad\n• Aprobación final"),
        "proceso_fase4_titulo": cfg.get("proceso_fase4_titulo", "Entrega y cierre"),
        "proceso_fase4_puntos": cfg.get("proceso_fase4_puntos", "• Puesta en marcha / Entrega final\n• Validación de conformidad\n• Soporte y garantía\n• Facturación final"),
        "presupuesto_proceso_cierre": cfg.get("presupuesto_proceso_cierre", ""),
        "factura_condiciones": cfg.get("factura_condiciones", ""),
        "presupuesto_condiciones": cfg.get("presupuesto_condiciones", "")
    }


@router.put("/configuracion/presupuesto")
def guardar_configuracion_presupuesto(data: dict):
    """Guarda los textos y parámetros editoriales de los documentos."""
    campos = [
        "presupuesto_instagram", "presupuesto_email",
        "presupuesto_bienvenida_titulo", "presupuesto_bienvenida_subtitulo",
        "presupuesto_bienvenida_texto",
        "presupuesto_proceso_titulo", "presupuesto_proceso_subtitulo",
        "proceso_fase1_titulo", "proceso_fase1_puntos",
        "proceso_fase2_titulo", "proceso_fase2_puntos",
        "proceso_fase3_titulo", "proceso_fase3_puntos",
        "proceso_fase4_titulo", "proceso_fase4_puntos",
        "presupuesto_proceso_cierre",
        "factura_condiciones", "presupuesto_condiciones"
    ]
    valores = {k: str(data.get(k, "")).strip() for k in campos if k in data}
    if valores:
        set_configuracion(valores)
    return {"message": "Configuración editorial guardada correctamente", "datos": obtener_configuracion_presupuesto()}
