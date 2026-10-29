/**
 * SIF PyME — Asistente de Primera Apertura (Onboarding Wizard)
 * Estética nativa Apple HIG (macOS Sheets / Stepper)
 */

(function () {
  let currentStep = 1;
  const totalSteps = 4;
  let rutasSugeridas = null;

  async function checkOnboardingStatus() {
    // Si el usuario ya está en Ajustes, no solapar con el asistente de onboarding
    if (window.location.pathname.startsWith('/configuracion')) {
      return;
    }
    try {
      const res = await fetch('/api/configuracion');
      if (!res.ok) return;
      const data = await res.json();

      // Si el onboarding no está completado o no hay datos de emisor válidos
      const yaCompletado = data.datos && data.datos.onboarding_completado === 'true';
      if (!yaCompletado && !data.es_valida) {
        await cargarRutasSugeridas();
        abrirOnboarding();
      }
    } catch (e) {
      console.warn('No se pudo verificar el estado de Onboarding:', e);
    }
  }

  async function cargarRutasSugeridas() {
    try {
      const res = await fetch('/api/configuracion/rutas-sugeridas');
      if (res.ok) {
        rutasSugeridas = await res.json();
        actualizarOpcionesDeRutas();
      }
    } catch (e) {
      console.warn('Error al cargar rutas sugeridas:', e);
    }
  }

  function actualizarOpcionesDeRutas() {
    if (!rutasSugeridas) return;

    const optLocal = document.getElementById('onboard-path-local-text');
    if (optLocal) optLocal.textContent = rutasSugeridas.local_default || '~/Documents/Facturas/PDFs';

    const cardICloud = document.getElementById('onboard-card-icloud');
    const optICloud = document.getElementById('onboard-path-icloud-text');
    if (rutasSugeridas.icloud && cardICloud && optICloud) {
      cardICloud.style.display = 'flex';
      optICloud.textContent = rutasSugeridas.icloud;
    } else if (cardICloud) {
      cardICloud.style.display = 'none';
    }

    const inputCustom = document.getElementById('onboard-custom-path');
    if (inputCustom && !inputCustom.value) {
      inputCustom.value = rutasSugeridas.local_default || '';
    }
  }

  function abrirOnboarding() {
    const sheet = document.getElementById('onboarding-sheet-overlay');
    if (!sheet) return;
    sheet.classList.add('active');
    setStep(1);
  }

  function cerrarOnboarding() {
    const sheet = document.getElementById('onboarding-sheet-overlay');
    if (sheet) sheet.classList.remove('active');
  }

  function setStep(step) {
    currentStep = step;
    for (let i = 1; i <= totalSteps; i++) {
      const stepEl = document.getElementById(`onboard-step-${i}`);
      const indicatorEl = document.getElementById(`onboard-indicator-${i}`);
      if (stepEl) {
        stepEl.style.display = i === step ? 'block' : 'none';
      }
      if (indicatorEl) {
        indicatorEl.classList.toggle('active', i === step);
        indicatorEl.classList.toggle('completed', i < step);
      }
    }
  }

  function getRutaSeleccionada() {
    const selectedRadio = document.querySelector('input[name="onboard_storage_option"]:checked');
    if (!selectedRadio) return rutasSugeridas?.local_default || '';

    if (selectedRadio.value === 'local') {
      return rutasSugeridas?.local_default || '';
    } else if (selectedRadio.value === 'icloud') {
      return rutasSugeridas?.icloud || '';
    } else {
      const customInput = document.getElementById('onboard-custom-path');
      return customInput ? customInput.value.trim() : '';
    }
  }

  async function finalizarOnboarding() {
    const btnFinalizar = document.getElementById('btn-onboard-finalizar');
    const errBox = document.getElementById('onboard-error-msg');
    if (errBox) errBox.style.display = 'none';

    const nombre = (document.getElementById('onboard-nombre')?.value || '').trim();
    const nif = (document.getElementById('onboard-nif')?.value || '').trim();
    const direccion = (document.getElementById('onboard-direccion')?.value || '').trim();
    const cp = (document.getElementById('onboard-cp')?.value || '').trim();
    const ciudad = (document.getElementById('onboard-ciudad')?.value || '').trim();
    const email = (document.getElementById('onboard-email')?.value || '').trim();
    const iban = (document.getElementById('onboard-iban')?.value || '').trim();
    const crearAcceso = document.getElementById('onboard-crear-acceso')?.checked ?? true;
    const rutaFacturas = getRutaSeleccionada();

    if (!nombre) {
      mostrarError('Por favor, introduce el Nombre o Razón Social de tu empresa o actividad.');
      setStep(3);
      return;
    }
    if (!nif) {
      mostrarError('Por favor, introduce un NIF o CIF válido para el emisor.');
      setStep(3);
      return;
    }

    if (btnFinalizar) {
      btnFinalizar.disabled = true;
      btnFinalizar.textContent = 'Configurando…';
    }

    try {
      const payload = {
        nombre: nombre,
        nif: nif,
        direccion: direccion,
        codigo_postal: cp,
        ciudad: ciudad,
        email: email,
        iban: iban,
        pdf_storage_dir: rutaFacturas,
        crear_acceso_escritorio: crearAcceso
      };

      const res = await fetch('/api/configuracion/onboarding', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.mensaje || 'Error al guardar configuración');
      }

      cerrarOnboarding();
      if (window.Toast) {
        Toast.success('¡Todo listo!', 'Tu entorno de facturación ha sido configurado correctamente.');
      }

      const alertContainer = document.getElementById('global-config-alert');
      if (alertContainer) {
        alertContainer.className = 'hidden';
        alertContainer.innerHTML = '';
      }

      // Si estamos en la página de configuración o inicio, refrescar
      if (window.location.pathname === '/' || window.location.pathname.startsWith('/configuracion')) {
        setTimeout(() => { window.location.reload(); }, 600);
      }
    } catch (err) {
      mostrarError(err.message || 'Error inesperado al guardar');
    } finally {
      if (btnFinalizar) {
        btnFinalizar.disabled = false;
        btnFinalizar.textContent = 'Comenzar a usar SIF PyME';
      }
    }
  }

  function mostrarError(msg) {
    const errBox = document.getElementById('onboard-error-msg');
    if (errBox) {
      errBox.textContent = msg;
      errBox.style.display = 'block';
    } else {
      alert(msg);
    }
  }

  // Exponer API global de onboarding
  window.OnboardingAssistant = {
    open: () => {
      cargarRutasSugeridas();
      abrirOnboarding();
    },
    close: cerrarOnboarding,
    next: () => setStep(Math.min(totalSteps, currentStep + 1)),
    prev: () => setStep(Math.max(1, currentStep - 1)),
    setStep: setStep,
    finish: finalizarOnboarding
  };

  document.addEventListener('DOMContentLoaded', () => {
    checkOnboardingStatus();

    // Manejar toggle de campo personalizado en selector de rutas
    document.querySelectorAll('input[name="onboard_storage_option"]').forEach(radio => {
      radio.addEventListener('change', (e) => {
        const customContainer = document.getElementById('onboard-custom-path-container');
        if (customContainer) {
          customContainer.style.display = e.target.value === 'custom' ? 'block' : 'none';
        }
      });
    });
  });
})();

