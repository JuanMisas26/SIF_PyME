/**
 * macOS Native Controller (AppKit / SwiftUI Desktop Controller)
 * Conecta la interfaz nativa macOS con los endpoints de FastAPI y la base de datos de SIF PyME.
 */

'use strict';

let _selectedFacturaId = null;
let _currentFacturas = [];
let _activeEstadoFilter = '';
let _activeIvaFilter = '';
let _facturasPagination = null;
let _facturasCurrentPage = 1;
let _facturasPageSize = 25;
let _activeFacturasFilters = {};

/**
 * Inicialización al cargar el DOM
 */
document.addEventListener('DOMContentLoaded', () => {
  initMacOSApp();
});

async function initMacOSApp() {
  // Inicializar selector dinámico de años
  inicializarSelectorAnios();

  // Inicializar componentes y cargar datos con el periodo por defecto
  aplicarFiltroPeriodo();
  cargarContadoresSidebar();

  // Buscador con debounce de 250ms
  const searchInput = document.getElementById('mac-search-input');
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        cargarFacturasMacOS({ q: e.target.value.trim(), page: 1 });
      }, 250);
    });
  }

  // Filtro de estado en sub-barra
  const selectEstado = document.getElementById('filter-select-estado');
  if (selectEstado) {
    selectEstado.addEventListener('change', (e) => {
      _activeEstadoFilter = e.target.value;
      aplicarFiltroPeriodo();
    });
  }

  // Filtro segmentado exclusivo de IVA (Todas / Con IVA / Sin IVA)
  const ivaSegmented = document.getElementById('filter-segmented-iva');
  if (ivaSegmented) {
    ivaSegmented.addEventListener('click', (e) => {
      const btn = e.target.closest('.segment-btn');
      if (!btn) return;
      const val = btn.dataset.val || '';

      // Si hace clic en el que ya está activo (que no sea "Todas"), se desactiva y vuelve a "Todas"
      if (btn.classList.contains('active') && val !== '') {
        _activeIvaFilter = '';
        ivaSegmented.querySelectorAll('.segment-btn').forEach(b => b.classList.toggle('active', b.dataset.val === ''));
      } else {
        _activeIvaFilter = val;
        ivaSegmented.querySelectorAll('.segment-btn').forEach(b => b.classList.toggle('active', b === btn));
      }

      aplicarFiltroPeriodo();
    });
  }

  // Filtro de año en sub-barra
  const selectAnio = document.getElementById('filter-select-anio');
  if (selectAnio) {
    selectAnio.addEventListener('change', () => {
      aplicarFiltroPeriodo();
    });
  }

  // Filtro de periodo en sub-barra
  const selectPeriodo = document.getElementById('filter-select-periodo');
  if (selectPeriodo) {
    selectPeriodo.addEventListener('change', () => {
      aplicarFiltroPeriodo();
    });
  }

  // Botón Vista Previa en Inspector
  const btnPreview = document.getElementById('btn-inspector-preview');
  if (btnPreview) {
    btnPreview.addEventListener('click', abrirPdfFacturaInspector);
  }

  // Botón Editar en Inspector
  const btnEdit = document.getElementById('btn-inspector-edit');
  if (btnEdit) {
    btnEdit.addEventListener('click', () => {
      if (!_selectedFacturaId) {
        if (window.Toast) window.Toast.info('Atención', 'Seleccione una factura primero.');
        return;
      }
      window.location.href = `/facturas/${_selectedFacturaId}/editar`;
    });
  }

  // Botón Historial de Versiones en Inspector
  const btnVersiones = document.getElementById('btn-inspector-versiones');
  if (btnVersiones) {
    btnVersiones.addEventListener('click', () => {
      if (!_selectedFacturaId) {
        if (window.Toast) window.Toast.warning('Seleccione una factura', 'Haga clic en una factura de la lista para consultar su historial de versiones.');
        return;
      }
      const factura = _currentFacturas.find(f => f.id === _selectedFacturaId);
      const numero = factura ? factura.numero_factura : `FAC-${_selectedFacturaId}`;
      if (window.VersionHistoryManager) {
        window.VersionHistoryManager.abrir('factura', _selectedFacturaId, numero);
      }
    });
  }

  // Botón Eliminar en Inspector
  const btnDelete = document.getElementById('btn-inspector-delete');
  if (btnDelete) {
    btnDelete.addEventListener('click', async () => {
      if (!_selectedFacturaId) {
        if (window.Toast) window.Toast.info('Atención', 'Seleccione una factura primero.');
        return;
      }
      const factura = _currentFacturas.find(f => f.id === _selectedFacturaId);
      const numero = factura ? factura.numero_factura : `#${_selectedFacturaId}`;
      if (typeof window.eliminarFactura === 'function') {
        await window.eliminarFactura(_selectedFacturaId, numero);
      } else {
        const fnConfirm = window.showMacConfirmDialog || window.showMacConfirm;
        let conf = false;
        if (typeof fnConfirm === 'function') {
          conf = await fnConfirm({
            title: `¿Eliminar la factura ${numero}?`,
            message: 'Esta acción moverá la factura a la papelera de reciclaje.',
            confirmText: 'Eliminar Factura',
            isDestructive: true
          });
        } else {
          conf = confirm(`¿Eliminar la factura ${numero}?`);
        }
        if (!conf) return;
        await apiFetch(`/api/facturas/${_selectedFacturaId}`, { method: 'DELETE' });
        if (window.Toast) window.Toast.success('Factura eliminada', `Factura ${numero} eliminada`);
      }
      _selectedFacturaId = null;
      limpiarInspector();
      aplicarFiltroPeriodo();
      cargarContadoresSidebar();
    });
  }

  // Selector de Estado en Inspector
  const inspectorSelectStatus = document.getElementById('detail-status');
  if (inspectorSelectStatus) {
    inspectorSelectStatus.addEventListener('change', actualizarEstadoFacturaInspector);
  }

  // Configurar botones de ventana (Traffic Lights)
  configurarTrafficLights();
}

/**
 * Carga de facturas desde la API con filtros activos
 */
async function cargarFacturasMacOS(customFilters = {}) {
  const tbody = document.getElementById('mac-invoices-tbody');
  if (!tbody) return;

  if (customFilters.page !== undefined) {
    _facturasCurrentPage = customFilters.page;
  }
  if (customFilters.pageSize !== undefined) {
    _facturasPageSize = customFilters.pageSize;
  }

  for (const [k, v] of Object.entries(customFilters)) {
    if (k !== 'page' && k !== 'pageSize') {
      if (v === null || v === undefined || v === '') {
        delete _activeFacturasFilters[k];
      } else {
        _activeFacturasFilters[k] = v;
      }
    }
  }

  const q = _activeFacturasFilters.q !== undefined ? _activeFacturasFilters.q : (document.getElementById('mac-search-input')?.value.trim() || '');
  const estado = _activeFacturasFilters.estado !== undefined ? _activeFacturasFilters.estado : _activeEstadoFilter;
  const ivaFiltro = _activeFacturasFilters.sin_iva !== undefined ? _activeFacturasFilters.sin_iva : _activeIvaFilter;

  let url = `/api/facturas?paginated=true&page=${_facturasCurrentPage}&page_size=${_facturasPageSize}`;
  if (q) url += `&q=${encodeURIComponent(q)}`;
  if (estado) url += `&estado=${encodeURIComponent(estado)}`;
  if (ivaFiltro === 'SIN_IVA' || ivaFiltro === true || ivaFiltro === '1') {
    url += `&sin_iva=true`;
  } else if (ivaFiltro === 'CON_IVA' || ivaFiltro === false || ivaFiltro === '0') {
    url += `&sin_iva=false`;
  }
  if (_activeFacturasFilters.fecha_desde) url += `&fecha_desde=${encodeURIComponent(_activeFacturasFilters.fecha_desde)}`;
  if (_activeFacturasFilters.fecha_hasta) url += `&fecha_hasta=${encodeURIComponent(_activeFacturasFilters.fecha_hasta)}`;

  try {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 32px; color: var(--mac-text-tertiary);">Cargando facturas...</td></tr>`;
    const res = await apiFetch(url);
    _currentFacturas = res.items || [];

    tbody.innerHTML = '';

    if (!_currentFacturas.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7">
            <div class="empty-state-mac">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>
              <h3>Sin facturas que mostrar</h3>
              <p>No se encontraron registros que coincidan con los filtros aplicados.</p>
            </div>
          </td>
        </tr>
      `;
      limpiarInspector();
      actualizarStatusBar(0, 0, 0);
      if (_facturasPagination) {
        _facturasPagination.render({ page: 1, pageSize: _facturasPageSize, total: 0, totalPages: 1 });
      }
      return;
    }

    let sumBase = 0;
    let sumTotal = 0;
    let primeraFila = null;

    _currentFacturas.forEach((factura, index) => {
      sumBase += Number(factura.base_imponible_total || 0);
      sumTotal += Number(factura.total_factura || 0);

      const tr = document.createElement('tr');
      tr.dataset.id = factura.id;
      if (factura.id === _selectedFacturaId || (!_selectedFacturaId && index === 0)) {
        tr.classList.add('selected');
        primeraFila = factura;
      }

      const estadoClass = (factura.estado || 'borrador').toLowerCase();

      tr.innerHTML = `
        <td style="font-weight: 500;">${factura.numero_factura}</td>
        <td>${formatDate(factura.fecha_emision)}</td>
        <td>${escapeHtml(factura.cliente_razon_social || 'Consumidor Final')}</td>
        <td>${escapeHtml(factura.cliente_nif_cif || '—')}</td>
        <td style="text-align: right;">${formatCurrency(factura.base_imponible_total)}</td>
        <td style="text-align: right; font-weight: 600;">${formatCurrency(factura.total_factura)}</td>
        <td>
          <span class="status-badge">
            <span class="status-dot ${estadoClass}"></span>
            ${factura.estado}
          </span>
          ${(factura.sin_iva || factura.iva_total === 0) ? '<span class="badge" style="display:inline-block; margin-left:6px; font-size:10px; font-weight:600; padding:1px 6px; border-radius:4px; background:#F3E8FF; color:#7E22CE; border:1px solid #E9D5FF;">Sin IVA</span>' : ''}
        </td>
      `;

      tr.addEventListener('click', () => {
        document.querySelectorAll('#mac-invoices-tbody tr').forEach(r => r.classList.remove('selected'));
        tr.classList.add('selected');
        cargarDetalleInspector(factura);
      });

      tbody.appendChild(tr);
    });

    if (primeraFila) {
      cargarDetalleInspector(primeraFila);
    }

    actualizarStatusBar(res.total, sumBase, sumTotal);

    if (!_facturasPagination && window.MacPagination) {
      _facturasPagination = new MacPagination({
        container: 'facturas-pagination-container',
        initialPageSize: _facturasPageSize,
        onPageChange: (newPage) => cargarFacturasMacOS({ page: newPage }),
        onPageSizeChange: (newSize) => {
          _facturasPageSize = newSize;
          cargarFacturasMacOS({ page: 1, pageSize: newSize });
        }
      });
    }
    if (_facturasPagination) {
      _facturasPagination.render({
        page: res.page,
        pageSize: res.page_size,
        total: res.total,
        totalPages: res.total_pages
      });
    }
  } catch (error) {
    console.error('Error al cargar facturas:', error);
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 24px; color: var(--mac-system-red);">Error al cargar datos desde el servidor.</td></tr>`;
  }
}

/**
 * Carga los detalles de la factura seleccionada en el Inspector
 */
function cargarDetalleInspector(factura) {
  if (!factura) return;
  _selectedFacturaId = factura.id;

  const elId = document.getElementById('detail-id');
  const elClient = document.getElementById('detail-client');
  const elCif = document.getElementById('detail-cif');
  const elDate = document.getElementById('detail-date');
  const elBase = document.getElementById('detail-base');
  const elTotal = document.getElementById('detail-total');
  const elStatus = document.getElementById('detail-status');

  if (elId) elId.textContent = factura.numero_factura;
  if (elClient) elClient.value = factura.cliente_razon_social || 'Consumidor Final';
  if (elCif) elCif.value = factura.cliente_nif_cif || '—';
  if (elDate) elDate.value = formatDate(factura.fecha_emision);
  if (elBase) elBase.textContent = formatCurrency(factura.base_imponible_total);
  if (elTotal) elTotal.textContent = formatCurrency(factura.total_factura);

  if (elStatus) {
    elStatus.value = factura.estado;
  }

  const elRegimen = document.getElementById('detail-regimen');
  if (elRegimen) {
    const esSinIva = Boolean(factura.sin_iva || factura.iva_total === 0);
    elRegimen.innerHTML = esSinIva
      ? '<span style="color:#7E22CE; font-weight:600;">Sin IVA (Exenta)</span>'
      : '<span style="color:var(--mac-text-primary);">Régimen General (Con IVA)</span>';
  }
}

/**
 * Limpia el inspector cuando no hay elementos
 */
function limpiarInspector() {
  _selectedFacturaId = null;
  const elId = document.getElementById('detail-id');
  const elClient = document.getElementById('detail-client');
  const elCif = document.getElementById('detail-cif');
  const elDate = document.getElementById('detail-date');
  const elTotal = document.getElementById('detail-total');

  if (elId) elId.textContent = '—';
  if (elClient) elClient.value = '';
  if (elCif) elCif.value = '';
  if (elDate) elDate.value = '';
  if (elTotal) elTotal.textContent = '0,00 €';
  const elRegimen = document.getElementById('detail-regimen');
  if (elRegimen) elRegimen.textContent = '—';
}

/**
 * Modifica el estado de la factura seleccionada en tiempo real vía API
 */
async function actualizarEstadoFacturaInspector() {
  if (!_selectedFacturaId) return;
  const select = document.getElementById('detail-status');
  if (!select) return;

  const nuevoEstado = select.value;

  try {
    await apiFetch(`/api/facturas/${_selectedFacturaId}/estado`, {
      method: 'PUT',
      body: { estado: nuevoEstado }
    });

    if (window.Toast) {
      window.Toast.success('Estado Actualizado', `Factura actualizada a ${nuevoEstado}`);
    }

    // Actualizar visualmente la fila seleccionada
    const row = document.querySelector(`#mac-invoices-tbody tr[data-id="${_selectedFacturaId}"]`);
    if (row) {
      const statusBadge = row.querySelector('.status-badge');
      if (statusBadge) {
        const cls = nuevoEstado.toLowerCase();
        statusBadge.innerHTML = `<span class="status-dot ${cls}"></span> ${nuevoEstado}`;
      }
    }

    // Actualizar contadores del sidebar
    cargarContadoresSidebar();
  } catch (error) {
    console.error('Error al actualizar estado:', error);
    if (window.Toast) {
      window.Toast.error('Error', error.message || 'No se pudo actualizar el estado');
    }
  }
}

/**
 * Abre o descarga el PDF de la factura seleccionada
 */
function abrirPdfFacturaInspector() {
  if (!_selectedFacturaId) {
    if (window.Toast) window.Toast.info('Atención', 'Seleccione una factura primero.');
    return;
  }
  const url = `/api/facturas/${_selectedFacturaId}/pdf`;
  window.open(url, '_blank');
}

/**
 * Actualiza los contadores del Sidebar (Source List)
 */
async function cargarContadoresSidebar() {
  if (typeof window.actualizarContadoresSidebar === 'function') {
    return window.actualizarContadoresSidebar();
  }
}

/**
 * Filtrado directo desde los enlaces del Sidebar
 */
function filtrarPorCategoriaSidebar(tipo, elementoClick) {
  document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
  if (elementoClick) elementoClick.classList.add('active');

  const selectEstado = document.getElementById('filter-select-estado');

  if (tipo === 'todas') {
    _activeEstadoFilter = '';
    if (selectEstado) selectEstado.value = '';
    cargarFacturasMacOS();
  } else if (tipo === 'pendientes') {
    _activeEstadoFilter = 'Emitida';
    if (selectEstado) selectEstado.value = 'Emitida';
    cargarFacturasMacOS({ estado: 'Emitida' });
  } else if (tipo === 'cobradas') {
    _activeEstadoFilter = 'Pagada';
    if (selectEstado) selectEstado.value = 'Pagada';
    cargarFacturasMacOS({ estado: 'Pagada' });
  }
}

/**
 * Inicializa el selector de años dinámicamente según el año actual
 */
function inicializarSelectorAnios() {
  const selectAnio = document.getElementById('filter-select-anio');
  if (!selectAnio) return;

  const currentYear = new Date().getFullYear();
  const anios = [];
  // Rango desde el año siguiente hasta 4 años atrás
  for (let y = currentYear + 1; y >= currentYear - 4; y--) {
    anios.push(y);
  }

  selectAnio.innerHTML = `
    <option value="TODOS">Todos los años</option>
    ${anios.map(y => `<option value="${y}" ${y === currentYear ? 'selected' : ''}>${y}</option>`).join('')}
  `;

  // Actualizar el subtítulo de la ventana
  const subtitleEl = document.getElementById('window-subtitle-fiscal') || document.querySelector('.window-subtitle');
  if (subtitleEl) {
    subtitleEl.textContent = `Ejercicio Fiscal ${currentYear}`;
  }
}

/**
 * Filtro dinámico por año y periodo (anual, trimestral o mensual)
 */
function aplicarFiltroPeriodo() {
  const selectAnio = document.getElementById('filter-select-anio');
  const selectPeriodo = document.getElementById('filter-select-periodo');

  const anioVal = selectAnio ? selectAnio.value : String(new Date().getFullYear());
  const periodoVal = selectPeriodo ? selectPeriodo.value : 'ANUAL';

  const subtitleEl = document.getElementById('window-subtitle-fiscal') || document.querySelector('.window-subtitle');
  if (subtitleEl) {
    subtitleEl.textContent = anioVal === 'TODOS' ? 'Todos los ejercicios fiscales' : `Ejercicio Fiscal ${anioVal}`;
  }

  let desde = null;
  let hasta = null;

  if (anioVal !== 'TODOS') {
    const anio = parseInt(anioVal, 10);
    if (periodoVal === 'T1') {
      desde = `${anio}-01-01`;
      hasta = `${anio}-03-31`;
    } else if (periodoVal === 'T2') {
      desde = `${anio}-04-01`;
      hasta = `${anio}-06-30`;
    } else if (periodoVal === 'T3') {
      desde = `${anio}-07-01`;
      hasta = `${anio}-09-30`;
    } else if (periodoVal === 'T4') {
      desde = `${anio}-10-01`;
      hasta = `${anio}-12-31`;
    } else if (periodoVal === 'ANUAL') {
      desde = `${anio}-01-01`;
      hasta = `${anio}-12-31`;
    } else if (periodoVal && periodoVal.startsWith('M')) {
      const mes = periodoVal.substring(1);
      const ultimoDia = new Date(anio, parseInt(mes, 10), 0).getDate();
      desde = `${anio}-${mes}-01`;
      hasta = `${anio}-${mes}-${String(ultimoDia).padStart(2, '0')}`;
    }
  }

  cargarFacturasMacOS({ fecha_desde: desde, fecha_hasta: hasta });
}

/**
 * Actualiza los datos de la barra inferior (NSStatusBar)
 */
function actualizarStatusBar(cantidad, sumaBase, sumaTotal) {
  const elCount = document.getElementById('status-facturas-count');
  const elBase = document.getElementById('status-base-sum');
  const elTotal = document.getElementById('status-total-sum');

  if (elCount) elCount.textContent = `${cantidad} factura${cantidad === 1 ? '' : 's'}`;
  if (elBase) elBase.textContent = formatCurrency(sumaBase);
  if (elTotal) elTotal.textContent = formatCurrency(sumaTotal);
}

