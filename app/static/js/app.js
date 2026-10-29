'use strict';

// ============================================================
//  API ERROR & HELPER
// ============================================================
class ApiError extends Error {
  constructor(data, status = 500, extraErrors = []) {
    let msg = `HTTP ${status}`;
    let errors = Array.isArray(extraErrors) ? extraErrors : [];
    let code = data?.error_code || `HTTP_${status}`;

    if (typeof data === 'string') {
      msg = data;
    } else if (typeof data?.detail === 'string') {
      msg = data.detail;
    } else if (Array.isArray(data?.detail)) {
      msg = data.detail.map(d => (typeof d === 'string' ? d : (d.msg || JSON.stringify(d)))).join('\n');
    }
    if (Array.isArray(data?.errors) && data.errors.length > 0) {
      errors = data.errors;
    }

    super(msg);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.errors = errors;
    this.data = data;
  }
}

// Expose ApiError and apiFetch globally on window
if (typeof window !== 'undefined') {
  window.ApiError = ApiError;
}

async function apiFetch(url, options = {}) {
  const defaults = {
    headers: { 'Content-Type': 'application/json' },
  };
  const config = { ...defaults, ...options };
  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }
  const res = await fetch(url, config);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(errData, res.status);
  }
  if (res.status === 204) return null;
  return res.json();
}

if (typeof window !== 'undefined') {
  window.apiFetch = apiFetch;
}

// ============================================================
//  MACOS HIG PAGINATION COMPONENT
// ============================================================
class MacPagination {
  /**
   * @param {Object} options
   * @param {string|HTMLElement} options.container - Selector or DOM element
   * @param {Function} options.onPageChange - (newPage) => void
   * @param {Function} [options.onPageSizeChange] - (newPageSize) => void
   * @param {number} [options.initialPageSize=25]
   */
  constructor({ container, onPageChange, onPageSizeChange, initialPageSize = 25, total = 0, page = 1, pageSize = null }) {
    this.container = typeof container === 'string' ? document.getElementById(container) : container;
    this.onPageChange = onPageChange;
    this.onPageSizeChange = onPageSizeChange;
    this.page = page || 1;
    this.pageSize = pageSize || initialPageSize;
    this.total = total || 0;
    this.totalPages = 1;
  }

  render(params = {}) {
    if (!this.container) return;
    const { page, pageSize, total, totalPages } = params || {};
    this.page = page !== undefined ? page : (this.page || 1);
    this.pageSize = pageSize !== undefined ? pageSize : (this.pageSize || 25);
    this.total = total !== undefined ? total : (this.total || 0);
    this.totalPages = totalPages !== undefined ? totalPages : Math.max(1, Math.ceil(this.total / this.pageSize));

    const hasPrev = this.page > 1;
    const hasNext = this.page < this.totalPages;
    const idPrefix = this.container.id || 'mac-pag';

    this.container.innerHTML = `
      <div class="mac-pagination">
        <div class="mac-pagination-size-wrap">
          <select class="mac-pagination-select" id="${idPrefix}-pagesize" title="Elementos por página">
            <option value="25" ${this.pageSize === 25 ? 'selected' : ''}>25 / pág.</option>
            <option value="50" ${this.pageSize === 50 ? 'selected' : ''}>50 / pág.</option>
            <option value="100" ${this.pageSize === 100 ? 'selected' : ''}>100 / pág.</option>
          </select>
        </div>
        <div class="mac-segmented-nav">
          <button type="button" class="mac-page-btn btn-prev" ${!hasPrev ? 'disabled' : ''} title="Página anterior">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"></polyline></svg>
            Anterior
          </button>
          <span class="mac-page-indicator">
            ${this.page} / ${this.totalPages}
          </span>
          <button type="button" class="mac-page-btn btn-next" ${!hasNext ? 'disabled' : ''} title="Página siguiente">
            Siguiente
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"></polyline></svg>
          </button>
        </div>
      </div>
    `;

    const select = this.container.querySelector(`#${idPrefix}-pagesize`);
    if (select) {
      select.addEventListener('change', (e) => {
        const newSize = parseInt(e.target.value, 10);
        this.pageSize = newSize;
        if (this.onPageSizeChange) this.onPageSizeChange(newSize);
        else if (this.onPageChange) this.onPageChange(1);
      });
    }

    const btnPrev = this.container.querySelector('.btn-prev');
    if (btnPrev && hasPrev) {
      btnPrev.addEventListener('click', () => {
        if (this.onPageChange) this.onPageChange(this.page - 1);
      });
    }

    const btnNext = this.container.querySelector('.btn-next');
    if (btnNext && hasNext) {
      btnNext.addEventListener('click', () => {
        if (this.onPageChange) this.onPageChange(this.page + 1);
      });
    }
  }
}

if (typeof window !== 'undefined') {
  window.MacPagination = MacPagination;
}


function clearFormErrors(form) {
  if (!form) return;
  form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
  form.querySelectorAll('.field-error-msg').forEach(el => el.remove());
  const alertBox = form.querySelector('[id$="-alert"]');
  if (alertBox) {
    alertBox.classList.add('hidden');
    alertBox.innerHTML = '';
  }
}

function displayFormErrors(form, error, defaultTitle = 'Error al guardar') {
  if (!form) return;
  clearFormErrors(form);

  const alertBox = form.querySelector('[id$="-alert"]');
  if (error.errors && error.errors.length > 0) {
    let listHtml = '<ul style="margin:4px 0 0 16px; padding:0; line-height:1.5">';
    error.errors.forEach(err => {
      const fieldName = err.field;
      const inputEl = form.elements[fieldName] || form.querySelector(`[name="${fieldName}"]`);
      if (inputEl) {
        inputEl.classList.add('is-invalid');
        const errorSpan = document.createElement('div');
        errorSpan.className = 'field-error-msg';
        errorSpan.textContent = err.message;
        inputEl.parentNode.appendChild(errorSpan);
      }
      listHtml += `<li>${err.message}</li>`;
    });
    listHtml += '</ul>';

    if (alertBox) {
      alertBox.innerHTML = `<strong>⚠️ Errores de validación:</strong>${listHtml}`;
      alertBox.classList.remove('hidden');
    }
    Toast.error('Datos incorrectos', 'Revise los campos señalados en rojo');
  } else {
    const isConflict = error.code === 'CONFLICT' || error.status === 409;
    const title = isConflict ? 'Registro duplicado' : defaultTitle;
    if (alertBox) {
      alertBox.innerHTML = `<strong>⚠️ ${isConflict ? 'Conflicto' : 'Atención'}:</strong> ${error.message}`;
      alertBox.classList.remove('hidden');
    }
    Toast.error(title, error.message);
  }
}

// ============================================================
//  TOAST NOTIFICATIONS
// ============================================================
const Toast = {
  container: null,
  init() {
    this.container = document.getElementById('toast-container');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toast-container';
      document.body.appendChild(this.container);
    }
  },
  show(title, message = '', type = 'info', duration = 4000) {
    if (!this.container) this.init();
    const icons = { success: '✓', error: '✕', info: 'ℹ', warning: '!' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
      <div class="toast-content">
        <div class="toast-title">${title}</div>
        ${message ? `<div class="toast-message">${message}</div>` : ''}
      </div>
      <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;
    this.container.appendChild(toast);
    setTimeout(() => toast.remove(), duration);
  },
  success(title, msg) { this.show(title, msg, 'success'); },
  error(title, msg) { this.show(title, msg, 'error', 6000); },
  info(title, msg) { this.show(title, msg, 'info'); },
  warning(title, msg) { this.show(title, msg, 'warning'); },
};

function showToast(msg, type = 'info') {
  if (type === 'danger' || type === 'error') {
    Toast.error('Aviso', msg);
  } else if (type === 'success') {
    Toast.success('Éxito', msg);
  } else if (type === 'warning') {
    Toast.warning('Atención', msg);
  } else {
    Toast.info('Información', msg);
  }
}

if (typeof window !== 'undefined') {
  window.Toast = Toast;
  window.showToast = showToast;
}

// ============================================================
//  LOADING OVERLAY
// ============================================================
const Loading = {
  overlay: null,
  show(text = 'Procesando...') {
    if (!this.overlay) {
      this.overlay = document.getElementById('loading-overlay');
    }
    if (this.overlay) {
      const textEl = this.overlay.querySelector('.loading-text');
      if (textEl) textEl.textContent = text;
      this.overlay.classList.add('show');
    }
  },
  hide() {
    if (this.overlay) this.overlay.classList.remove('show');
  },
};

if (typeof window !== 'undefined') {
  window.Loading = Loading;
}

// ============================================================
//  AUTOCOMPLETE
// ============================================================
class Autocomplete {
  constructor(inputEl, dropdownEl, options = {}) {
    if (dropdownEl && !(dropdownEl instanceof HTMLElement) && typeof dropdownEl === 'object') {
      options = dropdownEl;
      dropdownEl = null;
    }
    this.input = inputEl;
    if (!dropdownEl && inputEl) {
      dropdownEl = inputEl.parentNode ? inputEl.parentNode.querySelector('.autocomplete-dropdown') : null;
      if (!dropdownEl && inputEl.parentNode) {
        dropdownEl = document.createElement('div');
        dropdownEl.className = 'autocomplete-dropdown';
        inputEl.parentNode.appendChild(dropdownEl);
      }
    }
    this.dropdown = dropdownEl;
    this.onSelect = options.onSelect || (() => {});
    this.fetchUrl = options.fetchUrl || options.endpoint || '/api/clientes';
    this.renderItem = options.renderItem || this._defaultRender;
    this.onNoResults = options.onNoResults || null;
    this.onCreateClick = options.onCreateClick || null;
    this.minChars = options.minChars || 2;
    this.debounceMs = options.debounceMs || 250;
    this._debounceTimer = null;
    this._activeIdx = -1;
    this._items = [];
    this._lastQuery = '';
    this._bind();
  }

  _bind() {
    this.input.addEventListener('input', () => this._onInput());
    this.input.addEventListener('keydown', (e) => this._onKeydown(e));
    document.addEventListener('click', (e) => {
      const wrapper = this.input.closest('.autocomplete-wrapper');
      if (wrapper && !wrapper.contains(e.target)) {
        this.close();
      }
    });
  }

  _onInput() {
    clearTimeout(this._debounceTimer);
    const q = this.input.value.trim();
    this._lastQuery = q;
    if (q.length < this.minChars) { this.close(); return; }
    this._debounceTimer = setTimeout(() => this._fetch(q), this.debounceMs);
  }

  async _fetch(q) {
    try {
      const items = await apiFetch(`${this.fetchUrl}?q=${encodeURIComponent(q)}`);
      this._items = items;
      this._render();
    } catch (e) {
      console.error('Autocomplete fetch error:', e);
    }
  }

  _render() {
    this.dropdown.innerHTML = '';
    if (!this._items.length) {
      if (this.onNoResults) {
        this.dropdown.innerHTML = this.onNoResults(this._lastQuery);
        this.dropdown.classList.add('show');
        const createBtn = this.dropdown.querySelector('.btn-dropdown-create');
        if (createBtn) {
          createBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.close();
            if (this.onCreateClick) this.onCreateClick(this._lastQuery);
          });
        }
      } else {
        this.dropdown.innerHTML = '<div class="autocomplete-no-results">Sin resultados</div>';
        this.dropdown.classList.add('show');
      }
      return;
    }
    this._items.forEach((item, idx) => {
      const el = document.createElement('div');
      el.className = 'autocomplete-item';
      el.innerHTML = this.renderItem(item);
      el.addEventListener('click', () => this._select(idx));
      this.dropdown.appendChild(el);
    });
    this._activeIdx = -1;
    this.dropdown.classList.add('show');
  }

  _defaultRender(item) {
    const idStr = item.nif_cif ? item.nif_cif : 'Particular';
    const telStr = item.telefono ? ` · 📞 ${item.telefono}` : '';
    const emailStr = item.email ? ` · ✉️ ${item.email}` : '';
    const locStr = [item.ciudad, item.provincia].filter(Boolean).join(', ');
    return `<div class="item-name">${item.razon_social}</div>
            <div class="item-sub">${idStr}${telStr}${emailStr}${locStr ? ' · ' + locStr : ''}</div>`;
  }

  _select(idx) {
    const item = this._items[idx];
    this.onSelect(item);
    this.input.value = item.razon_social || item.descripcion || '';
    this.close();
  }

  _onKeydown(e) {
    const items = this.dropdown.querySelectorAll('.autocomplete-item');
    if (!this.dropdown.classList.contains('show') || !items.length) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this._activeIdx = Math.min(this._activeIdx + 1, items.length - 1);
      this._highlight(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      this._activeIdx = Math.max(this._activeIdx - 1, 0);
      this._highlight(items);
    } else if (e.key === 'Enter' && this._activeIdx >= 0) {
      e.preventDefault();
      this._select(this._activeIdx);
    } else if (e.key === 'Escape') {
      this.close();
    }
  }

  _highlight(items) {
    items.forEach((el, i) => el.classList.toggle('active', i === this._activeIdx));
    if (this._activeIdx >= 0) items[this._activeIdx].scrollIntoView({ block: 'nearest' });
  }

  close() {
    this.dropdown.classList.remove('show');
    this._activeIdx = -1;
  }
}

if (typeof window !== 'undefined') {
  window.Autocomplete = Autocomplete;
}

// ============================================================
//  FORMAT HELPERS
// ============================================================
function escapeHtml(text) {
  if (text === null || text === undefined) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatCurrency(amount) {
  return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(amount || 0);
}

if (typeof window !== 'undefined') {
  window.escapeHtml = escapeHtml;
  window.formatCurrency = formatCurrency;
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr + 'T00:00:00').toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
  } catch { return dateStr; }
}

function badgeHtml(estado) {
  const cls = estado.toLowerCase();
  return `<span class="badge badge-${cls}">${estado}</span>`;
}

// ============================================================
//  MACOS NATIVE CONFIRM / ALERT DIALOG (NSAlert)
// ============================================================
function showMacConfirmDialog({
  title = 'Confirmar acción',
  message = '',
  detailHtml = '',
  confirmText = 'Continuar',
  cancelText = 'Cancelar',
  isDestructive = true,
  isDanger = undefined,
  onConfirm = null
} = {}) {
  const destructive = (isDanger !== undefined) ? !!isDanger : !!isDestructive;
  return new Promise((resolve) => {
    const modal = document.getElementById('mac-confirm-modal');
    if (!modal) {
      const ok = window.confirm(message || title);
      if (ok && typeof onConfirm === 'function') {
        try { onConfirm(); } catch (e) { console.error(e); }
      }
      resolve(ok);
      return;
    }

    const titleEl = document.getElementById('mac-confirm-title');
    const bodyEl = document.getElementById('mac-confirm-body');
    const okBtn = document.getElementById('mac-confirm-btn-ok');
    const cancelBtn = document.getElementById('mac-confirm-btn-cancel');
    const iconContainer = document.getElementById('mac-confirm-icon-container');

    if (titleEl) titleEl.textContent = title;
    if (bodyEl) {
      if (detailHtml) {
        bodyEl.innerHTML = detailHtml;
      } else {
        bodyEl.textContent = message;
      }
    }

    if (okBtn) {
      okBtn.textContent = confirmText;
      okBtn.className = destructive ? 'btn-native btn-danger' : 'btn-native btn-primary';
    }
    if (cancelBtn) {
      cancelBtn.textContent = cancelText;
    }

    if (iconContainer) {
      const iconSvg = document.getElementById('mac-confirm-icon-svg');
      if (destructive) {
        iconContainer.style.background = '#FEE2E2';
        iconContainer.style.color = 'var(--mac-system-red)';
        if (iconSvg) {
          iconSvg.innerHTML = `
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          `;
        }
      } else {
        iconContainer.style.background = '#EFF6FF';
        iconContainer.style.color = 'var(--mac-accent)';
        if (iconSvg) {
          iconSvg.innerHTML = `
            <polyline points="1 4 1 10 7 10"></polyline>
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
          `;
        }
      }
    }

    const cleanup = () => {
      modal.classList.remove('show');
      okBtn.removeEventListener('click', onOk);
      cancelBtn.removeEventListener('click', onCancel);
      modal.removeEventListener('click', onBackdrop);
      window.removeEventListener('keydown', onKey);
    };

    const onOk = async () => {
      cleanup();
      if (typeof onConfirm === 'function') {
        try {
          await onConfirm();
        } catch (err) {
          console.error('Error en onConfirm:', err);
        }
      }
      resolve(true);
    };

    const onCancel = () => {
      cleanup();
      resolve(false);
    };

    const onBackdrop = (e) => {
      if (e.target === modal) {
        cleanup();
        resolve(false);
      }
    };

    const onKey = (e) => {
      if (e.key === 'Escape') {
        cleanup();
        resolve(false);
      }
    };

    okBtn.addEventListener('click', onOk);
    cancelBtn.addEventListener('click', onCancel);
    modal.addEventListener('click', onBackdrop);
    window.addEventListener('keydown', onKey);

    modal.classList.add('show');
    okBtn.focus();
  });
}
window.showMacConfirmDialog = showMacConfirmDialog;
window.showMacConfirm = showMacConfirmDialog;

// ============================================================
//  INVOICE LINES CALCULATOR & MANAGER (PRESUPUESTOS STYLE)
// ============================================================
const LineasManager = {
  container: null,
  lineasData: [],
  catalogoProductos: [],
  defaultIva: 21,
  defaultIrpf: 0,
  sinIva: false,
  descuentoSeleccionado: null,
  descuentoVisible: true,
  descuentoImporteTotal: 0.0,
  descuentosDisponibles: [],

  async cargarDescuentos() {
    try {
      const res = await fetch('/api/descuentos?activo=true');
      if (res.ok) {
        this.descuentosDisponibles = await res.json();
        const select = document.getElementById('factura-select-descuento');
        if (select) {
          const currentVal = select.value;
          select.innerHTML = '<option value="">(Sin descuento)</option>' + this.descuentosDisponibles.map(d => {
            const valStr = d.tipo === 'porcentaje' ? `${d.valor}%` : `${formatCurrency(d.valor)}`;
            const ambito = d.aplica_a === 'productos' ? '🎯 Específico' : '🌐 Global';
            return `<option value="${d.id}">${escapeHtml(d.nombre)} (${valStr} - ${ambito})</option>`;
          }).join('');
          if (currentVal) select.value = currentVal;
        }
      }
    } catch (e) {
      console.warn('No se pudo cargar la lista de promociones:', e);
    }
  },

  onSelectDescuento(id) {
    if (!id) {
      this.descuentoSeleccionado = null;
    } else {
      this.descuentoSeleccionado = this.descuentosDisponibles.find(d => d.id == id) || null;
    }
    this.aplicarDescuento();
    this.recalcular();
  },

  setDescuentoVisible(visible) {
    this.descuentoVisible = Boolean(visible);
    const btnVis = document.getElementById('btn-descuento-visible');
    const btnOcu = document.getElementById('btn-descuento-oculto');
    if (btnVis) btnVis.classList.toggle('active', this.descuentoVisible);
    if (btnOcu) btnOcu.classList.toggle('active', !this.descuentoVisible);
    this.aplicarDescuento();
    this.recalcular();
  },

  lineaAplicaDescuento(linea, desc) {
    if (!linea || !desc) return false;
    if (desc.aplica_a === 'todos') return true;
    if (desc.aplica_a === 'productos' && Array.isArray(desc.producto_ids)) {
      return Boolean(linea.producto_id && desc.producto_ids.includes(linea.producto_id));
    }
    return false;
  },

  aplicarDescuento() {
    const badge = document.getElementById('badge-promo-activa');
    const panelConfig = document.getElementById('panel-descuento-config');
    const infoDetalle = document.getElementById('info-descuento-detalle');

    if (!this.descuentoSeleccionado) {
      if (badge) badge.style.display = 'none';
      if (panelConfig) panelConfig.style.display = 'none';
      this.lineasData.forEach((l, idx) => {
        if (!l) return;
        if (l.precio_unitario_original !== undefined && l.precio_unitario_original !== null) {
          l.precio_unitario = l.precio_unitario_original;
          l.precio_unitario_original = null;
          const inp = document.getElementById(`precio-input-${idx}`);
          if (inp) inp.value = l.precio_unitario.toFixed(2);
        }
      });
      return;
    }

    const desc = this.descuentoSeleccionado;
    if (badge) {
      badge.style.display = 'inline-block';
      badge.textContent = this.descuentoVisible ? 'Aplicado' : 'Aplicado (Oculto)';
    }
    if (panelConfig) panelConfig.style.display = 'block';

    if (infoDetalle) {
      if (desc.aplica_a === 'productos') {
        const nombresProds = desc.productos_nombres && desc.productos_nombres.length > 0
          ? desc.productos_nombres.join(', ')
          : 'productos vinculados';
        infoDetalle.innerHTML = this.descuentoVisible
          ? `Descuento del <strong>${desc.tipo === 'porcentaje' ? desc.valor + '%' : formatCurrency(desc.valor)}</strong> desglosado en el resumen para: <em>${escapeHtml(nombresProds)}</em>.`
          : `Precios unitarios <strong>autocalculados (netos)</strong> solo en: <em>${escapeHtml(nombresProds)}</em>. En el PDF final no aparecerá ninguna mención a descuentos.`;
      } else {
        infoDetalle.innerHTML = this.descuentoVisible
          ? `Descuento global del <strong>${desc.tipo === 'porcentaje' ? desc.valor + '%' : formatCurrency(desc.valor)}</strong> desglosado en el resumen de totales.`
          : `Precios unitarios <strong>autocalculados (netos)</strong> en todas las líneas. En el PDF final no aparecerá ninguna mención a descuentos.`;
      }
    }

    if (!this.descuentoVisible) {
      // Modo Oculto: Recalcular precios unitarios únicamente de las líneas aplicables
      this.lineasData.forEach((l, idx) => {
        if (!l) return;
        const aplica = this.lineaAplicaDescuento(l, desc);
        if (aplica) {
          if (l.precio_unitario_original === undefined || l.precio_unitario_original === null) {
            l.precio_unitario_original = l.precio_unitario;
          }
          let nuevoPrecio = l.precio_unitario_original;
          if (desc.tipo === 'porcentaje') {
            nuevoPrecio = Math.round(l.precio_unitario_original * (1 - desc.valor / 100) * 100) / 100;
          } else if (desc.tipo === 'fijo') {
            const cant = l.cantidad || 1;
            nuevoPrecio = Math.max(0, Math.round((l.precio_unitario_original - (desc.valor / cant)) * 100) / 100);
          }
          l.precio_unitario = nuevoPrecio;
          const inp = document.getElementById(`precio-input-${idx}`);
          if (inp) inp.value = nuevoPrecio.toFixed(2);
        } else {
          if (l.precio_unitario_original !== undefined && l.precio_unitario_original !== null) {
            l.precio_unitario = l.precio_unitario_original;
            l.precio_unitario_original = null;
            const inp = document.getElementById(`precio-input-${idx}`);
            if (inp) inp.value = l.precio_unitario.toFixed(2);
          }
        }
      });
    } else {
      // Modo Visible: Restaurar precios unitarios originales
      this.lineasData.forEach((l, idx) => {
        if (!l) return;
        if (l.precio_unitario_original !== undefined && l.precio_unitario_original !== null) {
          l.precio_unitario = l.precio_unitario_original;
          const inp = document.getElementById(`precio-input-${idx}`);
          if (inp) inp.value = l.precio_unitario.toFixed(2);
        }
      });
    }
  },

  getDescuentoInfo() {
    if (!this.descuentoSeleccionado) {
      return { id: null, nombre: null, tipo: null, valor: 0.0, importe_total: 0.0, visible: true };
    }
    return {
      id: this.descuentoSeleccionado.id,
      nombre: this.descuentoSeleccionado.nombre,
      tipo: this.descuentoSeleccionado.tipo,
      valor: this.descuentoSeleccionado.valor,
      importe_total: this.descuentoImporteTotal || 0.0,
      visible: this.descuentoVisible
    };
  },

  setSinIva(val) {
    this.sinIva = Boolean(val);
    const chk = document.getElementById('check-sin-iva');
    if (chk && chk.checked !== this.sinIva) {
      chk.checked = this.sinIva;
    }
    const btnCon = document.getElementById('btn-factura-con-iva');
    const btnSin = document.getElementById('btn-factura-sin-iva');
    if (btnCon) btnCon.classList.toggle('active', !this.sinIva);
    if (btnSin) btnSin.classList.toggle('active', this.sinIva);

    const badge = document.getElementById('badge-sin-iva-active');
    if (badge) {
      badge.style.display = this.sinIva ? 'inline-block' : 'none';
    }

    if (!this.sinIva && this.lineasData) {
      this.lineasData.forEach(l => {
        if (!l) return;
        if (!l.porcentaje_iva || l.porcentaje_iva <= 0) {
          l.porcentaje_iva = l.porcentaje_iva_original || this.defaultIva || 21.0;
        }
      });
    }

    this.recalcular();
  },

  calcularPrecioSugerido(prod, cantidad, varianteId = null) {
    if (!prod) return 0.0;
    let precio = (prod.precio_unitario_base !== undefined && prod.precio_unitario_base !== null) ? Number(prod.precio_unitario_base) : 0.0;

    // 1. Tramos por volumen
    if (prod.escalados && prod.escalados.length > 0 && cantidad > 0) {
      const sorted = [...prod.escalados].sort((a, b) => Number(b.cantidad_minima || 0) - Number(a.cantidad_minima || 0));
      for (const esc of sorted) {
        const cMin = Number(esc.cantidad_minima || 0);
        const cMax = esc.cantidad_maxima !== null && esc.cantidad_maxima !== undefined ? Number(esc.cantidad_maxima) : null;
        if (cantidad >= cMin && (cMax === null || cantidad <= cMax)) {
          precio = Number(esc.precio_unitario || 0);
          break;
        }
      }
    }

    // 2. Variante seleccionada
    if (varianteId && prod.variantes && prod.variantes.length > 0) {
      const v = prod.variantes.find(x => x.id == varianteId);
      if (v) {
        if (v.precio_fijo !== null && v.precio_fijo !== undefined) {
          precio = Number(v.precio_fijo);
        } else if (v.precio_adicional) {
          precio += Number(v.precio_adicional);
        }
      }
    }

    return Math.round(precio * 100) / 100;
  },

  async init(containerEl) {
    this.container = containerEl;
    this.lineasData = [];
    await Promise.all([this.cargarCatalogo(), this.cargarDescuentos()]);

    // Event listener para cerrar desplegables de autocompletado al hacer click fuera
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.autocomplete-wrapper')) {
        document.querySelectorAll('.autocomplete-dropdown.show').forEach(el => el.classList.remove('show'));
      }
    });

    // Event listener para cerrar desplegables de autocompletado con tecla Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        document.querySelectorAll('.autocomplete-dropdown.show').forEach(el => el.classList.remove('show'));
      }
    });

    // Añadir una primera línea por defecto si la tabla está vacía y no estamos en edición
    const isEditing = Boolean(window.FACTURA_EDITING_ID || window.location.pathname.match(/\/facturas\/\d+\/editar/));
    if (this.lineasData.length === 0 && !isEditing) {
      this.addLinea();
    }
  },

  setLineas(lineas) {
    this.lineasData = [];
    if (this.container) this.container.innerHTML = '';
    if (!lineas || lineas.length === 0) {
      this.addLinea();
      return;
    }
    lineas.forEach(l => {
      let desc = l.descripcion || '';
      let mat = l.detalle_material || '';
      // Separar si venía concatenado como 'Nombre (Detalle)' de versiones anteriores
      if (!mat && desc) {
        const parenMatch = desc.match(/^(.*?)\s*\(([^()]+)\)$/);
        if (parenMatch) {
          desc = parenMatch[1].trim();
          mat = parenMatch[2].trim();
        }
      }
      this.addLinea({
        producto_id: l.producto_id,
        descripcion: desc,
        detalle_material: mat,
        cantidad: l.cantidad,
        precio_unitario: l.precio_unitario,
        porcentaje_descuento: l.porcentaje_descuento,
        porcentaje_iva: l.porcentaje_iva,
        porcentaje_irpf: l.porcentaje_irpf,
        precio_unitario_original: l.precio_unitario_original || null
      });
    });
  },

  async cargarCatalogo() {
    try {
      const res = await fetch('/api/productos');
      if (res.ok) {
        this.catalogoProductos = await res.json();
      }
    } catch (e) {
      console.warn('No se pudo cargar el catálogo de productos:', e);
    }
  },

  addLinea(prefill = {}) {
    const idx = this.lineasData.length;
    const precio = prefill.precio_unitario_base !== undefined ? prefill.precio_unitario_base : (prefill.precio_unitario || 0);
    const esNegativo = (precio < 0);
    const ivaPrefill = (prefill.porcentaje_iva !== undefined && prefill.porcentaje_iva !== null && !isNaN(Number(prefill.porcentaje_iva)))
      ? Number(prefill.porcentaje_iva)
      : (this.defaultIva !== undefined ? this.defaultIva : 21.0);

    const data = {
      producto_id: prefill.producto_id || null,
      descripcion: prefill.descripcion || '',
      detalle_material: prefill.detalle_material || '',
      cantidad: prefill.cantidad !== undefined ? prefill.cantidad : 100,
      precio_unitario: precio,
      porcentaje_descuento: prefill.porcentaje_descuento || 0,
      porcentaje_iva: ivaPrefill,
      porcentaje_iva_original: ivaPrefill,
      porcentaje_irpf: prefill.porcentaje_irpf !== undefined ? prefill.porcentaje_irpf : this.defaultIrpf,
      precio_unitario_original: (prefill.precio_unitario_original !== undefined && prefill.precio_unitario_original !== null) ? prefill.precio_unitario_original : null,
    };
    this.lineasData.push(data);

    const row = document.createElement('tr');
    row.id = `linea-row-${idx}`;
    row.dataset.idx = idx;
    row.innerHTML = this._rowHtml(idx, data);
    this.container.appendChild(row);

    const emptyMsg = document.getElementById('empty-lineas');
    if (emptyMsg) emptyMsg.style.display = 'none';

    this.recalcular();
    return idx;
  },

  _rowHtml(idx, data) {
    const sub = (data.cantidad * data.precio_unitario) || 0;
    return `
      <td style="padding: 6px 6px; vertical-align: middle; box-sizing: border-box;">
        <div class="autocomplete-wrapper" style="position: relative; width: 100%; min-width: 0;">
          <div style="display: flex; gap: 4px; align-items: center; width: 100%; min-width: 0;">
            <input type="text"
                   class="form-control form-control-sm desc-producto-input"
                   id="desc-input-${idx}"
                   style="flex: 1; min-width: 0; font-size: 12px; padding: 5px 8px;"
                   value="${escapeHtml(data.descripcion)}"
                   oninput="LineasManager.onProductoInput(${idx}, this.value)"
                   onfocus="LineasManager.onProductoFocus(${idx})"
                   placeholder="Buscar del catálogo o escribir uno nuevo…"
                   autocomplete="off">
            <button type="button"
                    class="btn btn-secondary btn-sm"
                    style="padding: 3px 6px; font-size: 11px; white-space: nowrap; flex-shrink: 0;"
                    title="Ver catálogo de productos de la base de datos"
                    onclick="LineasManager.toggleCatalogoDropdown(event, ${idx})">
              Catálogo
            </button>
          </div>
          <div class="autocomplete-dropdown" id="ac-producto-drop-${idx}"></div>
        </div>
      </td>
      <td style="padding: 6px 6px; vertical-align: middle; box-sizing: border-box;">
        <input type="text"
               class="form-control form-control-sm"
               id="mat-input-${idx}"
               style="width: 100%; min-width: 0; font-size: 12px; padding: 5px 8px;"
               value="${escapeHtml(data.detalle_material || '')}"
               oninput="LineasManager.actualizarLinea(${idx}, 'detalle_material', this.value)"
               placeholder="Detalle o especificación…">
      </td>
      <td style="padding: 6px 4px; vertical-align: middle; box-sizing: border-box;">
        <input type="number"
               class="form-control form-control-sm"
               id="cant-input-${idx}"
               style="width: 100%; min-width: 0; text-align: center; font-size: 12px; padding: 5px 4px;"
               value="${data.cantidad}"
               min="1"
               step="1"
               oninput="LineasManager.actualizarLinea(${idx}, 'cantidad', parseFloat(this.value) || 0)">
      </td>
      <td style="padding: 6px 4px; vertical-align: middle; box-sizing: border-box;">
        <input type="number"
               class="form-control form-control-sm"
               id="precio-input-${idx}"
               style="width: 100%; min-width: 0; text-align: right; font-size: 12px; padding: 5px 4px;"
               value="${data.precio_unitario}"
               step="0.01"
               oninput="LineasManager.actualizarLinea(${idx}, 'precio_unitario', parseFloat(this.value) || 0)">
      </td>
      <td id="subtotal-cell-${idx}" style="padding: 6px 6px; text-align: right; font-weight: 600; font-size: 12px; color: var(--color-gray-900); white-space: nowrap; vertical-align: middle; box-sizing: border-box;">
        ${formatCurrency(sub)}
      </td>
      <td style="padding: 6px 2px; text-align: center; vertical-align: middle; box-sizing: border-box;">
        <button type="button"
                class="btn btn-danger btn-sm"
                style="padding: 2px 6px; font-size: 13px; line-height: 1;"
                onclick="LineasManager.removeLinea(${idx})"
                title="Quitar producto">&times;</button>
      </td>
    `;
  },

  onProductoFocus(idx) {
    const input = document.getElementById(`desc-input-${idx}`);
    const q = input ? input.value.trim() : '';
    this.renderProductoDropdown(idx, q);
    if (input) {
      setTimeout(() => {
        input.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }, 60);
    }
  },

  onProductoInput(idx, val) {
    if (!this.lineasData[idx]) return;
    this.lineasData[idx].descripcion = val;
    this.renderProductoDropdown(idx, val.trim());
  },

  toggleCatalogoDropdown(e, idx) {
    e.stopPropagation();
    const drop = document.getElementById(`ac-producto-drop-${idx}`);
    if (!drop) return;
    if (drop.classList.contains('show')) {
      drop.classList.remove('show');
    } else {
      document.querySelectorAll('.autocomplete-dropdown.show').forEach(el => el.classList.remove('show'));
      this.renderProductoDropdown(idx, '', true);
    }
  },

  renderProductoDropdown(idx, q = '', forceShowAll = false) {
    const drop = document.getElementById(`ac-producto-drop-${idx}`);
    if (!drop) return;

    // Cerrar cualquier otro desplegable de producto abierto
    document.querySelectorAll('.autocomplete-dropdown.show').forEach(el => {
      if (el !== drop) el.classList.remove('show');
    });

    const lowerQ = (q || '').toLowerCase();
    let matches = [];
    if (forceShowAll || !lowerQ) {
      matches = this.catalogoProductos;
    } else {
      matches = this.catalogoProductos.filter(c =>
        (c.nombre && c.nombre.toLowerCase().includes(lowerQ)) ||
        (c.descripcion && c.descripcion.toLowerCase().includes(lowerQ)) ||
        (c.codigo && c.codigo.toLowerCase().includes(lowerQ))
      );
    }

    let html = '';

    if (matches.length > 0) {
      html += `<div style="padding: 6px 10px; font-size: 11px; font-weight: 700; color: var(--color-gray-500); background: #f8fafc; border-bottom: 1px solid var(--color-gray-200);">
        PRODUCTOS EN BASE DE DATOS (${matches.length})
      </div>`;

      matches.slice(0, 15).forEach(c => {
        const tieneEscalados = c.escalados && c.escalados.length > 0;
        const escBadge = tieneEscalados ? `<span style="background: #ECFDF5; color: #065F46; padding: 1px 4px; border-radius: 3px; font-size: 10px; margin-left: 4px;">${c.escalados.length} tramos volumen</span>` : '';
        html += `
          <div class="autocomplete-item" onclick="LineasManager.seleccionarProducto(${idx}, ${c.id})">
            <div class="item-name">${escapeHtml(c.nombre || c.descripcion)} ${escBadge}</div>
            <div class="item-sub">
              ${c.nombre && c.descripcion ? `<span style="color: #475569;">${escapeHtml(c.descripcion)}</span> · ` : ''}
              
              <strong>${formatCurrency(c.precio_unitario_base)}</strong>
              <span style="color: var(--color-gray-500);">(IVA ${c.porcentaje_iva}%)</span>
            </div>
          </div>
        `;
        if (c.variantes && c.variantes.length > 0) {
          c.variantes.forEach(v => {
            const extra = v.precio_adicional > 0 ? ` (+${formatCurrency(v.precio_adicional)})` : (v.precio_fijo !== null && v.precio_fijo !== undefined ? ` (${formatCurrency(v.precio_fijo)})` : '');
            const colorDot = v.color_hex ? `<span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${v.color_hex}; border: 1px solid rgba(0,0,0,0.2); vertical-align: middle; margin-right: 4px;"></span>` : '';
            html += `
              <div class="autocomplete-item" style="padding-left: 24px; background: #FAFAFB; border-left: 3px solid var(--mac-accent);" onclick="LineasManager.seleccionarProducto(${idx}, ${c.id}, ${v.id})">
                <div class="item-name" style="font-size: 12px; color: var(--mac-text-primary);">
                  ${colorDot}↳ <span style="color: var(--mac-text-secondary);">${escapeHtml(v.tipo_atributo)}:</span> <strong>${escapeHtml(v.valor)}</strong> ${extra}
                </div>
              </div>
            `;
          });
        }
      });
    }

    if (q) {
      html += `
        <div class="autocomplete-item" style="border-top: 1px dashed #cbd5e1; background: #fffdf5;" onclick="LineasManager.usarComoNuevoProducto(${idx})">
          <div class="item-name" style="color: #b45309; font-weight: 600;">
            Usar «${escapeHtml(q)}» como concepto personalizado
          </div>
          <div class="item-sub" style="color: #92400e;">
            Concepto libre para esta factura
          </div>
        </div>
      `;

      const exactMatch = this.catalogoProductos.some(c => ((c.nombre || '').toLowerCase() === lowerQ) || ((c.descripcion || '').toLowerCase() === lowerQ));
      if (!exactMatch) {
        html += `
          <div style="padding: 8px 10px; background: #f0fdf4; border-top: 1px solid #bbf7d0; text-align: center;">
            <button type="button" class="btn btn-sm btn-outline" style="font-size: 11px; padding: 4px 8px; width: 100%; border-color: #16a34a; color: #15803d;" onclick="LineasManager.guardarNuevoProductoEnBD(event, ${idx})">
              Guardar «${escapeHtml(q)}» en catálogo
            </button>
          </div>
        `;
      }
    } else if (matches.length === 0) {
      html += `
        <div style="padding: 14px; text-align: center; color: var(--color-gray-500); font-size: 12px;">
          No hay productos guardados aún en la base de datos.<br>
          <span style="font-size: 11px;">Puedes escribir cualquier concepto nuevo directamente.</span>
        </div>
      `;
    }

    drop.innerHTML = html;
    drop.classList.add('show');

    // Posicionamiento inteligente: si no cabe abajo de la pantalla, abrir hacia arriba
    const inputEl = document.getElementById(`desc-input-${idx}`);
    if (inputEl) {
      const rect = inputEl.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      if (spaceBelow < 280 && rect.top > 240) {
        drop.style.top = 'auto';
        drop.style.bottom = 'calc(100% + 4px)';
        drop.style.boxShadow = '0 -8px 24px rgba(0, 0, 0, 0.16)';
      } else {
        drop.style.top = 'calc(100% + 4px)';
        drop.style.bottom = 'auto';
        drop.style.boxShadow = 'var(--shadow-lg)';
      }
    }
  },

  seleccionarProducto(idx, productoId, varianteId = null) {
    const c = this.catalogoProductos.find(x => x.id == productoId);
    if (!c || !this.lineasData[idx]) return;

    const l = this.lineasData[idx];
    const tieneNombre = Boolean(c.nombre && c.nombre.trim());
    const tieneDesc = Boolean(c.descripcion && c.descripcion.trim());

    let nombreFinal = '';
    let detalleFinal = '';

    if (tieneNombre && tieneDesc) {
      nombreFinal = c.nombre.trim();
      detalleFinal = (c.nombre.trim() === c.descripcion.trim()) ? '' : c.descripcion.trim();
    } else if (tieneNombre) {
      nombreFinal = c.nombre.trim();
      detalleFinal = '';
    } else if (tieneDesc) {
      nombreFinal = c.descripcion.trim();
      detalleFinal = '';
    }

    l.producto_id = c.id;
    l.variante_id = varianteId;

    if (varianteId && c.variantes && c.variantes.length > 0) {
      const v = c.variantes.find(x => x.id == varianteId);
      if (v) {
        const extraVar = `${v.tipo_atributo}: ${v.valor}`;
        detalleFinal = detalleFinal ? `${extraVar} · ${detalleFinal}` : extraVar;
      }
    }

    const cantActual = l.cantidad || 100;
    const precioSugerido = this.calcularPrecioSugerido(c, cantActual, varianteId);

    l.descripcion = nombreFinal;
    l.detalle_material = detalleFinal;
    l.precio_unitario = precioSugerido;
    l.porcentaje_iva = c.porcentaje_iva !== undefined ? c.porcentaje_iva : this.defaultIva;
    l.porcentaje_irpf = c.aplica_irpf ? (c.porcentaje_irpf || this.defaultIrpf) : 0;

    const descInput = document.getElementById(`desc-input-${idx}`);
    if (descInput) descInput.value = nombreFinal;

    const matInput = document.getElementById(`mat-input-${idx}`);
    if (matInput) matInput.value = detalleFinal;

    const precioInput = document.getElementById(`precio-input-${idx}`);
    if (precioInput) precioInput.value = l.precio_unitario.toFixed(2);

    const drop = document.getElementById(`ac-producto-drop-${idx}`);
    if (drop) drop.classList.remove('show');

    this.recalcular();
    Toast.success('Producto seleccionado', `${nombreFinal} (${formatCurrency(l.precio_unitario)})`);
  },

  usarComoNuevoProducto(idx, nombre) {
    if (!this.lineasData[idx]) return;
    if (nombre === undefined) {
      const descInput = document.getElementById(`desc-input-${idx}`);
      nombre = descInput ? descInput.value.trim() : '';
    }
    this.lineasData[idx].descripcion = nombre;
    this.lineasData[idx].detalle_material = '';
    this.lineasData[idx].producto_id = null;

    const descInput = document.getElementById(`desc-input-${idx}`);
    if (descInput) descInput.value = nombre;

    const matInput = document.getElementById(`mat-input-${idx}`);
    if (matInput) matInput.value = '';

    const drop = document.getElementById(`ac-producto-drop-${idx}`);
    if (drop) drop.classList.remove('show');
  },
  async guardarNuevoProductoEnBD(e, idx, nombre) {
    e.stopPropagation();
    if (nombre === undefined) {
      const descInput = document.getElementById(`desc-input-${idx}`);
      nombre = descInput ? descInput.value.trim() : '';
    }
    const l = this.lineasData[idx];
    const precio = l ? (l.precio_unitario || 0.0) : 0.0;
    const detalle = l ? (l.detalle_material || '') : '';

    try {
      const res = await fetch('/api/productos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nombre: nombre,
          descripcion: detalle || nombre,
          precio_unitario_base: precio,
          porcentaje_iva: this.defaultIva,
          aplica_irpf: false
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Error al guardar en catálogo');
      }

      const nuevoProducto = await res.json();
      this.catalogoProductos.push(nuevoProducto);
      Toast.success('Catálogo actualizado', `¡Producto "${nombre}" guardado en la base de datos!`);
      this.seleccionarProducto(idx, nuevoProducto.id);
      if (typeof window.actualizarContadoresSidebar === 'function') {
        window.actualizarContadoresSidebar();
      }
    } catch (err) {
      Toast.warning('Aviso', err.message);
    }
  },

  actualizarLinea(idx, campo, val) {
    if (!this.lineasData[idx]) return;
    this.lineasData[idx][campo] = val;

    if (campo === 'cantidad') {
      const prodId = this.lineasData[idx].producto_id;
      if (prodId) {
        const prod = this.catalogoProductos.find(p => p.id == prodId);
        if (prod && prod.escalados && prod.escalados.length > 0) {
          const varId = this.lineasData[idx].variante_id || null;
          const nuevoPrecio = this.calcularPrecioSugerido(prod, val, varId);
          if (nuevoPrecio !== undefined && nuevoPrecio !== this.lineasData[idx].precio_unitario) {
            this.lineasData[idx].precio_unitario = nuevoPrecio;
            const precioInput = document.getElementById(`precio-input-${idx}`);
            if (precioInput) precioInput.value = nuevoPrecio.toFixed(2);
            Toast.info('Tarifa por volumen', `Aplicado escalado: ${formatCurrency(nuevoPrecio)}/ud para ${val} uds.`);
          }
        }
      }
    }
    this.recalcular();
  },

  removeLinea(idx) {
    this.lineasData[idx] = null;
    const row = document.getElementById(`linea-row-${idx}`);
    if (row) row.remove();

    const activas = this.lineasData.filter(l => l !== null);
    const emptyMsg = document.getElementById('empty-lineas');
    if (emptyMsg) {
      emptyMsg.style.display = activas.length === 0 ? 'block' : 'none';
    }

    this.recalcular();
  },

  recalcular() {
    let subtotalBruto = 0, baseTotal = 0, ivaTotal = 0, irpfTotal = 0;
    const esSinIvaGlobal = Boolean(this.sinIva);
    const desc = this.descuentoSeleccionado;
    const esVisible = Boolean(this.descuentoVisible);

    // 1. Calcular subtotales por línea y base aplicable a descuento
    let baseAplicableDescuento = 0;
    let subtotalBrutoOriginal = 0;
    this.lineasData.forEach((linea, idx) => {
      if (!linea) return;
      const cant = linea.cantidad || 0;
      const precio = linea.precio_unitario || 0;
      const precioOrig = (linea.precio_unitario_original !== undefined && linea.precio_unitario_original !== null)
        ? linea.precio_unitario_original
        : precio;
      const subtotal = Math.round(cant * precio * 100) / 100;
      subtotalBruto += subtotal;
      subtotalBrutoOriginal += Math.round(cant * precioOrig * 100) / 100;

      if (desc && this.lineaAplicaDescuento(linea, desc)) {
        baseAplicableDescuento += subtotal;
      }

      const cell = document.getElementById(`subtotal-cell-${idx}`);
      if (cell) cell.textContent = formatCurrency(subtotal);
    });

    let importeDescuento = 0;
    if (desc) {
      if (esVisible) {
        if (desc.tipo === 'porcentaje') {
          importeDescuento = Math.round(baseAplicableDescuento * (desc.valor / 100) * 100) / 100;
        } else if (desc.tipo === 'fijo') {
          importeDescuento = Math.min(baseAplicableDescuento, desc.valor);
        }
      } else {
        importeDescuento = Math.max(0, Math.round((subtotalBrutoOriginal - subtotalBruto) * 100) / 100);
      }
    }
    this.descuentoImporteTotal = importeDescuento;

    baseTotal = (desc && esVisible) ? Math.max(0, Math.round((subtotalBruto - importeDescuento) * 100) / 100) : subtotalBruto;

    // 2. Calcular impuestos proporcionales
    const factorDescuento = (subtotalBruto > 0 && desc && esVisible) ? (baseTotal / subtotalBruto) : 1.0;

    this.lineasData.forEach((linea) => {
      if (!linea) return;
      const cant = linea.cantidad || 0;
      const precio = linea.precio_unitario || 0;
      const subtotalLinea = Math.round(cant * precio * 100) / 100;
      const subtotalAjustado = Math.round(subtotalLinea * factorDescuento * 100) / 100;

      const ivaPct = esSinIvaGlobal
        ? 0
        : ((linea.porcentaje_iva !== undefined && linea.porcentaje_iva !== null && !isNaN(Number(linea.porcentaje_iva)))
            ? Number(linea.porcentaje_iva)
            : (linea.porcentaje_iva_original !== undefined ? linea.porcentaje_iva_original : (this.defaultIva || 21.0)));
      const irpfPct = linea.porcentaje_irpf !== undefined && linea.porcentaje_irpf !== null ? linea.porcentaje_irpf : this.defaultIrpf;

      const iva = esSinIvaGlobal ? 0 : Math.round(subtotalAjustado * ivaPct / 100 * 100) / 100;
      const irpf = Math.round(subtotalAjustado * irpfPct / 100 * 100) / 100;

      ivaTotal += iva;
      irpfTotal += irpf;
    });

    const total = Math.round((baseTotal + ivaTotal - irpfTotal) * 100) / 100;

    // Actualizar panel de desglose
    const filaBruto = document.getElementById('fila-subtotal-bruto');
    const filaDto = document.getElementById('fila-descuento-aplicado');
    const lblDto = document.getElementById('label-descuento-totales');
    const valDto = document.getElementById('total-descuento-importe');
    const valBruto = document.getElementById('total-subtotal-bruto');

    if (desc && importeDescuento > 0) {
      if (filaBruto) filaBruto.style.display = 'flex';
      if (filaDto) filaDto.style.display = 'flex';
      if (valBruto) valBruto.textContent = formatCurrency(esVisible ? subtotalBruto : subtotalBrutoOriginal);
      if (lblDto) lblDto.textContent = esVisible ? `Descuento (${desc.nombre})` : `Descuento (${desc.nombre}) (oculto)`;
      if (valDto) valDto.textContent = `-${formatCurrency(importeDescuento)}`;
    } else {
      if (filaBruto) filaBruto.style.display = 'none';
      if (filaDto) filaDto.style.display = 'none';
    }

    // Update totals panel
    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = formatCurrency(val); };
    setEl('total-base', baseTotal);
    const ivaEl = document.getElementById('total-iva');
    if (ivaEl) {
      ivaEl.textContent = esSinIvaGlobal ? '0,00 € (Exento)' : formatCurrency(ivaTotal);
    }
    setEl('total-irpf', irpfTotal);
    setEl('total-final', total);
  },

  getLineas() {
    const esSinIvaGlobal = Boolean(this.sinIva);
    const desc = this.descuentoSeleccionado;
    const descId = desc ? desc.id : null;
    return this.lineasData
      .filter(l => l !== null && (l.descripcion || '').trim())
      .map(l => {
        return {
          producto_id: l.producto_id || null,
          descripcion: (l.descripcion || '').trim(),
          detalle_material: (l.detalle_material || '').trim() || null,
          cantidad: l.cantidad || 100,
          precio_unitario: l.precio_unitario || 0,
          porcentaje_descuento: l.porcentaje_descuento || 0,
          porcentaje_iva: esSinIvaGlobal
            ? 0.0
            : ((l.porcentaje_iva !== undefined && l.porcentaje_iva !== null && !isNaN(Number(l.porcentaje_iva)))
                ? Number(l.porcentaje_iva)
                : (l.porcentaje_iva_original !== undefined ? l.porcentaje_iva_original : (this.defaultIva || 21.0))),
          porcentaje_irpf: l.porcentaje_irpf !== undefined ? l.porcentaje_irpf : this.defaultIrpf,
          descuento_id: (desc && this.lineaAplicaDescuento(l, desc)) ? descId : null,
          precio_unitario_original: l.precio_unitario_original || null,
        };
      });
  },
};
window.LineasManager = LineasManager;

function setSinIvaFactura(esSinIva) {
  LineasManager.setSinIva(esSinIva);
}
window.setSinIvaFactura = setSinIvaFactura;

function toggleSinIvaFactura(checked) {
  LineasManager.setSinIva(checked);
}
window.toggleSinIvaFactura = toggleSinIvaFactura;

// ============================================================
//  DASHBOARD PAGE
// ============================================================
async function initDashboard() {
  await Promise.all([loadStats(), loadRecentInvoices()]);
}

async function loadStats() {
  try {
    const facturas = await apiFetch('/api/facturas?page_size=200');
    const stats = {
      total: facturas.length,
      emitidas: facturas.filter(f => f.estado === 'Emitida').length,
      pagadas: facturas.filter(f => f.estado === 'Pagada').length,
      vencidas: facturas.filter(f => f.estado === 'Vencida').length,
      pendienteAmount: facturas
        .filter(f => ['Emitida', 'Vencida'].includes(f.estado))
        .reduce((sum, f) => sum + f.total_factura, 0),
      cobradoAmount: facturas
        .filter(f => f.estado === 'Pagada')
        .reduce((sum, f) => sum + f.total_factura, 0),
    };
    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    setEl('stat-total', stats.total);
    setEl('stat-emitidas', stats.emitidas);
    setEl('stat-pagadas', stats.pagadas);
    setEl('stat-vencidas', stats.vencidas);
    setEl('stat-pendiente', formatCurrency(stats.pendienteAmount));
    setEl('stat-cobrado', formatCurrency(stats.cobradoAmount));
  } catch (e) {
    console.error('Error loading stats:', e);
  }
}

async function loadRecentInvoices(filters = {}) {
  const tableBody = document.getElementById('facturas-tbody');
  if (!tableBody) return;

  try {
    let url = '/api/facturas?page_size=25';
    if (filters.estado) url += `&estado=${filters.estado}`;
    if (filters.q) url += `&q=${encodeURIComponent(filters.q)}`;
    if (filters.fecha_desde) url += `&fecha_desde=${filters.fecha_desde}`;
    if (filters.fecha_hasta) url += `&fecha_hasta=${filters.fecha_hasta}`;

    const facturas = await apiFetch(url);
    tableBody.innerHTML = '';

    if (!facturas.length) {
      tableBody.innerHTML = `
        <tr><td colspan="8">
          <div class="empty-state">
            <div class="empty-icon">📄</div>
            <h3>Sin facturas</h3>
            <p>No se encontraron facturas con los filtros aplicados.</p>
          </div>
        </td></tr>
      `;
      return;
    }

    facturas.forEach(f => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="font-mono text-primary">${escapeHtml(f.numero_factura)}</td>
        <td>${formatDate(f.fecha_emision)}</td>
        <td>${escapeHtml(f.cliente_razon_social || '—')}</td>
        <td class="hide-mobile">${escapeHtml(f.cliente_nif_cif || '—')}</td>
        <td class="text-right">${formatCurrency(f.base_imponible_total)}</td>
        <td class="text-right font-mono">${formatCurrency(f.total_factura)}</td>
        <td>${badgeHtml(f.estado)}</td>
        <td>
          <div class="flex gap-2">
            <a href="/api/facturas/${f.id}/pdf" target="_blank" class="btn btn-sm btn-outline" title="Descargar PDF">PDF</a>
            <button class="btn btn-sm btn-secondary btn-cambiar-estado" data-id="${f.id}" data-estado="${escapeHtml(f.estado)}" data-numero="${escapeHtml(f.numero_factura)}" title="Cambiar estado">⚙️</button>
            <button class="btn btn-sm btn-danger btn-eliminar-factura" data-id="${f.id}" data-numero="${escapeHtml(f.numero_factura)}" title="Eliminar factura">🗑️</button>
          </div>
        </td>
      `;
      tableBody.appendChild(tr);
    });

    if (!tableBody._hasActionsListener) {
      tableBody._hasActionsListener = true;
      tableBody.addEventListener('click', (e) => {
        const btnEstado = e.target.closest('.btn-cambiar-estado');
        if (btnEstado) {
          const id = parseInt(btnEstado.dataset.id, 10);
          const estado = btnEstado.dataset.estado;
          const numero = btnEstado.dataset.numero;
          openEstadoModal(id, estado, numero);
          return;
        }
        const btnEliminar = e.target.closest('.btn-eliminar-factura');
        if (btnEliminar) {
          const id = parseInt(btnEliminar.dataset.id, 10);
          const numero = btnEliminar.dataset.numero;
          eliminarFactura(id, numero);
          return;
        }
      });
    }
  } catch (e) {
    Toast.error('Error', 'No se pudieron cargar las facturas');
    console.error(e);
  }
}

async function eliminarFactura(id, numero) {
  const confirmado = await showMacConfirmDialog({
    title: `¿Eliminar factura ${numero}?`,
    detailHtml: `
      <p style="margin: 0 0 8px 0;">
        ¿Deseas mover a la papelera la factura <strong class="font-mono">${escapeHtml(numero)}</strong>?
      </p>
      <p style="margin: 0; font-size: 12px; color: var(--mac-text-secondary); line-height: 1.45;">
        Esta acción realizará un <strong>borrado</strong>. Si la factura proviene de un presupuesto, este volverá al estado <em>Aceptado</em>.
      </p>
    `,
    confirmText: 'Eliminar Factura',
    cancelText: 'Cancelar',
    isDestructive: true
  });

  if (!confirmado) return;

  try {
    const res = await apiFetch(`/api/facturas/${id}`, { method: 'DELETE' });
    Toast.success('Factura eliminada', res.message || `Factura ${numero} eliminada`);
    loadStats();
    loadRecentInvoices();
    actualizarContadoresSidebar();
  } catch (err) {
    Toast.error('Error', err.message || 'No se pudo eliminar la factura');
  }
}

// ============================================================
//  ESTADO MODAL
// ============================================================
let _estadoFacturaId = null;

function openEstadoModal(facturaId, estadoActual, numero) {
  _estadoFacturaId = facturaId;
  const modal = document.getElementById('estado-modal');
  if (!modal) return;
  document.getElementById('modal-numero-factura').textContent = numero;
  document.getElementById('select-estado').value = estadoActual;
  modal.classList.add('show');
}

function closeEstadoModal() {
  const modal = document.getElementById('estado-modal');
  if (modal) modal.classList.remove('show');
  _estadoFacturaId = null;
}

async function guardarEstado() {
  if (!_estadoFacturaId) return;
  const estado = document.getElementById('select-estado').value;
  try {
    await apiFetch(`/api/facturas/${_estadoFacturaId}/estado`, {
      method: 'PUT',
      body: { estado },
    });
    Toast.success('Estado actualizado', `Factura marcada como ${estado}`);
    closeEstadoModal();
    loadRecentInvoices(getActiveFilters());
    loadStats();
    actualizarContadoresSidebar();
  } catch (e) {
    Toast.error('Error', e.message);
  }
}

function getActiveFilters() {
  return {
    estado: document.getElementById('filter-estado')?.value || '',
    q: document.getElementById('filter-search')?.value || '',
    fecha_desde: document.getElementById('filter-desde')?.value || '',
    fecha_hasta: document.getElementById('filter-hasta')?.value || '',
  };
}

// ============================================================
//  NUEVA FACTURA PAGE
// ============================================================
let _selectedCliente = null;

async function initNuevaFactura() {
  // Comprobar configuración del emisor y aplicar valores por defecto
  const configRes = await verificarConfiguracionGlobal();
  if (configRes) {
    if (configRes.datos && configRes.datos.iva_defecto !== undefined) {
      LineasManager.defaultIva = parseFloat(configRes.datos.iva_defecto);
    }
    if (configRes.datos && configRes.datos.irpf_defecto !== undefined) {
      LineasManager.defaultIrpf = parseFloat(configRes.datos.irpf_defecto);
    }

    if (!configRes.es_valida) {
      const btnEmitir = document.getElementById('btn-emitir');
      if (btnEmitir) {
        btnEmitir.disabled = true;
        btnEmitir.classList.remove('btn-success');
        btnEmitir.classList.add('btn-secondary');
        btnEmitir.title = 'Debe configurar los datos de la empresa antes de emitir facturas.';
        const btnText = btnEmitir.querySelector('.btn-text');
        if (btnText) btnText.textContent = '⚠️ Emisión Bloqueada (Faltan Datos Fiscales)';
      }
      const warningBox = document.getElementById('nueva-factura-config-warning');
      if (warningBox) warningBox.classList.remove('hidden');
    }
  }

  // Initialize invoice lines manager
  const tbody = document.getElementById('lineas-tbody');
  if (tbody) await LineasManager.init(tbody);

  // Set today's date
  const fechaEmision = document.getElementById('fecha_emision');
  if (fechaEmision && !fechaEmision.value) {
    fechaEmision.value = new Date().toISOString().split('T')[0];
  }

  // Client autocomplete with in-situ creation support
  const clienteInput = document.getElementById('cliente-search');
  const clienteDropdown = document.getElementById('cliente-dropdown');
  if (clienteInput && clienteDropdown) {
    new Autocomplete(clienteInput, clienteDropdown, {
      fetchUrl: '/api/clientes',
      minChars: 2,
      onSelect: (cliente) => {
        seleccionarClienteEnFactura(cliente);
      },
      onNoResults: (q) => `
        <div class="autocomplete-no-results" style="padding:10px 12px; text-align:center">
          <div style="margin-bottom:6px; color:var(--gray-600)">No se encontró ningún cliente existente para <strong>${q}</strong>.</div>
          <button type="button" class="btn btn-sm btn-primary w-full btn-dropdown-create" style="justify-content:center; padding:6px 10px">
            ➕ Crear "${q}" como nuevo cliente
          </button>
        </div>
      `,
      onCreateClick: (q) => {
        openQuickClienteModal(q);
      }
    });
  }

  // Modal rápido de cliente in-situ
  document.getElementById('btn-quick-crear-cliente')?.addEventListener('click', () => {
    openQuickClienteModal(clienteInput?.value.trim() || '');
  });
  document.getElementById('btn-close-quick-cliente-modal')?.addEventListener('click', closeQuickClienteModal);
  document.getElementById('btn-cancel-quick-cliente')?.addEventListener('click', closeQuickClienteModal);
  document.getElementById('form-quick-cliente')?.addEventListener('submit', submitQuickCliente);

  // Add line buttons
  document.getElementById('btn-add-linea')?.addEventListener('click', () => {
    LineasManager.addLinea();
  });
  document.getElementById('btn-add-linea-bottom')?.addEventListener('click', () => {
    LineasManager.addLinea();
  });

  // Form submission
  document.getElementById('form-nueva-factura')?.addEventListener('submit', submitFactura);

  // Checkbox Sin IVA
  const chkSinIva = document.getElementById('check-sin-iva');
  if (chkSinIva) {
    chkSinIva.addEventListener('change', (e) => {
      LineasManager.setSinIva(e.target.checked);
    });
  }

  // Si estamos en modo edición, cargar datos existentes
  const editMatch = window.location.pathname.match(/\/facturas\/(\d+)\/editar/);
  const editingId = window.FACTURA_EDITING_ID || (editMatch ? parseInt(editMatch[1]) : null);
  if (editingId) {
    window.FACTURA_EDITING_ID = editingId;
    await cargarFacturaParaEditar(editingId);
  }
}

async function cargarFacturaParaEditar(facturaId) {
  try {
    Loading.show('Cargando factura para editar...');
    const factura = await apiFetch(`/api/facturas/${facturaId}`);

    if (factura.cliente_id) {
      document.getElementById('cliente_id').value = factura.cliente_id;
      document.getElementById('cliente-search').value = factura.cliente_razon_social || '';
      const clienteObj = {
        id: factura.cliente_id,
        razon_social: factura.cliente_razon_social,
        nif_cif: factura.cliente_nif_cif,
        telefono: factura.cliente_telefono,
        email: factura.cliente_email,
        direccion: factura.cliente_direccion,
        ciudad: factura.cliente_ciudad,
        provincia: factura.cliente_provincia,
        forma_pago_defecto: factura.cliente_forma_pago
      };
      seleccionarClienteEnFactura(clienteObj);
    }

    if (factura.fecha_emision) {
      document.getElementById('fecha_emision').value = factura.fecha_emision;
    }
    if (factura.fecha_vencimiento) {
      document.getElementById('fecha_vencimiento').value = factura.fecha_vencimiento;
    }
    if (factura.estado) {
      const selectEstado = document.getElementById('estado');
      if (selectEstado) selectEstado.value = factura.estado;
    }
    if (factura.observaciones) {
      document.getElementById('observaciones').value = factura.observaciones;
    }

    if (factura.lineas && factura.lineas.length > 0) {
      LineasManager.setLineas(factura.lineas);
    }

    if (factura.sin_iva !== undefined || factura.iva_total === 0) {
      const chkSinIva = document.getElementById('check-sin-iva');
      const esSinIva = Boolean(factura.sin_iva || factura.iva_total === 0);
      if (chkSinIva) {
        chkSinIva.checked = esSinIva;
      }
      LineasManager.setSinIva(esSinIva);
    }

    if (factura.descuento_id) {
      if (!LineasManager.descuentosDisponibles || LineasManager.descuentosDisponibles.length === 0) {
        await LineasManager.cargarDescuentos();
      }
      const selectDesc = document.getElementById('factura-select-descuento');
      if (selectDesc) {
        selectDesc.value = factura.descuento_id;
      }
      LineasManager.descuentoVisible = (factura.descuento_visible !== 0 && factura.descuento_visible !== false);
      const btnVis = document.getElementById('btn-descuento-visible');
      const btnOcu = document.getElementById('btn-descuento-oculto');
      if (btnVis) btnVis.classList.toggle('active', LineasManager.descuentoVisible);
      if (btnOcu) btnOcu.classList.toggle('active', !LineasManager.descuentoVisible);
      LineasManager.onSelectDescuento(factura.descuento_id);
    }
  } catch (err) {
    console.error('Error al cargar factura para editar:', err);
    Toast.error('Error', 'No se pudo cargar la factura: ' + err.message);
  } finally {
    Loading.hide();
  }
}

function seleccionarClienteEnFactura(cliente) {
  _selectedCliente = cliente;
  document.getElementById('cliente_id').value = cliente.id;
  document.getElementById('cliente-search').value = cliente.razon_social;

  // Fill client preview
  const setInfo = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val || '—'; };
  setInfo('cliente-nif', cliente.nif_cif ? cliente.nif_cif : 'Particular (Sin NIF)');
  setInfo('cliente-tel', cliente.telefono);
  setInfo('cliente-email', cliente.email);
  setInfo('cliente-dir', [cliente.direccion, cliente.ciudad, cliente.provincia].filter(Boolean).join(', '));
  setInfo('cliente-pago', cliente.forma_pago_defecto);
  document.getElementById('cliente-info')?.classList.remove('hidden');
}

let _quickClienteContext = 'factura';

function openQuickClienteModal(arg1 = '', arg2 = '') {
  let prefillName = '';
  if (arg1 === 'presupuesto' || arg1 === 'factura') {
    _quickClienteContext = arg1;
    prefillName = arg2 || '';
  } else {
    prefillName = arg1 || '';
    if (document.getElementById('pres-cliente-id')) {
      _quickClienteContext = 'presupuesto';
    } else {
      _quickClienteContext = 'factura';
    }
  }

  const modal = document.getElementById('quick-cliente-modal');
  if (!modal) {
    console.warn('No se encontró el elemento #quick-cliente-modal');
    return;
  }
  const form = document.getElementById('form-quick-cliente');
  if (form) {
    form.reset();
    clearFormErrors(form);
    if (prefillName) {
      const inputName = document.getElementById('quick_razon_social');
      if (inputName) inputName.value = prefillName;
    }
  }
  modal.classList.add('show');
  setTimeout(() => {
    document.getElementById('quick_razon_social')?.focus();
  }, 100);
}

function closeQuickClienteModal() {
  const modal = document.getElementById('quick-cliente-modal');
  if (modal) modal.classList.remove('show');
}

let _isSubmittingQuickCliente = false;

async function submitQuickCliente(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  if (_isSubmittingQuickCliente) return false;
  _isSubmittingQuickCliente = true;

  const form = e && e.target ? (e.target.tagName === 'FORM' ? e.target : document.getElementById('form-quick-cliente')) : document.getElementById('form-quick-cliente');
  if (!form) {
    _isSubmittingQuickCliente = false;
    return false;
  }
  clearFormErrors(form);

  const data = Object.fromEntries(new FormData(form));
  // Limpiar campos vacíos
  if (data.nif_cif && !data.nif_cif.trim()) delete data.nif_cif;
  if (data.telefono && !data.telefono.trim()) delete data.telefono;
  if (data.email && !data.email.trim()) delete data.email;

  const btnSubmit = document.getElementById('btn-submit-quick-cliente');
  if (btnSubmit) {
    btnSubmit.disabled = true;
    btnSubmit.style.pointerEvents = 'none';
  }

  try {
    const nuevoCliente = await apiFetch('/api/clientes', { method: 'POST', body: data });
    Toast.success('Cliente creado', `Se ha registrado y seleccionado a "${nuevoCliente.razon_social}"`);
    closeQuickClienteModal();

    if (_quickClienteContext === 'presupuesto' || document.getElementById('pres-cliente-id')) {
      if (typeof window.seleccionarCliente === 'function') {
        window.seleccionarCliente(nuevoCliente);
      } else if (typeof window.seleccionarClienteEnFactura === 'function') {
        window.seleccionarClienteEnFactura(nuevoCliente);
      }
    } else {
      seleccionarClienteEnFactura(nuevoCliente);
    }
    actualizarContadoresSidebar();
  } catch (err) {
    displayFormErrors(form, err, 'Error al crear cliente');
  } finally {
    setTimeout(() => {
      _isSubmittingQuickCliente = false;
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.style.pointerEvents = '';
      }
    }, 400);
  }
}

// Exponer en window para que botones inline onclick siempre funcionen
window.openQuickClienteModal = openQuickClienteModal;
window.closeQuickClienteModal = closeQuickClienteModal;
window.submitQuickCliente = submitQuickCliente;

let _isSubmittingFactura = false;

async function submitFactura(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }

  if (_isSubmittingFactura) return;
  _isSubmittingFactura = true;

  const clienteId = document.getElementById('cliente_id')?.value;
  if (!clienteId) {
    _isSubmittingFactura = false;
    Toast.warning('Cliente requerido', 'Seleccione un cliente del autocompletado o créelo con el botón Nuevo Cliente');
    return;
  }

  const lineas = LineasManager.getLineas();
  if (!lineas.length) {
    _isSubmittingFactura = false;
    Toast.warning('Sin líneas', 'Añada al menos una línea a la factura');
    return;
  }

  const sinIvaChecked = document.getElementById('check-sin-iva')?.checked || false;
  const descInfo = LineasManager.getDescuentoInfo();
  const payload = {
    cliente_id: parseInt(clienteId),
    fecha_emision: document.getElementById('fecha_emision')?.value,
    fecha_vencimiento: document.getElementById('fecha_vencimiento')?.value || null,
    observaciones: document.getElementById('observaciones')?.value || null,
    estado: document.getElementById('estado')?.value || 'Emitida',
    sin_iva: sinIvaChecked,
    descuento_id: descInfo.id,
    descuento_nombre: descInfo.nombre,
    descuento_tipo: descInfo.tipo,
    descuento_valor: descInfo.valor,
    descuento_importe_total: descInfo.importe_total,
    descuento_visible: descInfo.visible,
    lineas: lineas,
  };

  const isEdit = Boolean(window.FACTURA_EDITING_ID);
  const btn = document.getElementById('btn-emitir');
  const btnSide = document.getElementById('btn-emitir-side');
  const btnText = btn?.querySelector('.btn-text');
  const btnSideText = btnSide?.querySelector('.btn-text');

  if (btn) btn.disabled = true;
  if (btnSide) btnSide.disabled = true;
  const msgLoading = isEdit ? 'Actualizando factura y PDF...' : 'Generando factura y PDF...';
  if (btnText) btnText.textContent = isEdit ? 'Guardando...' : 'Generando...';
  if (btnSideText) btnSideText.textContent = isEdit ? 'Guardando...' : 'Generando...';
  Loading.show(msgLoading);

  try {
    const url = isEdit ? `/api/facturas/${window.FACTURA_EDITING_ID}` : '/api/facturas';
    const method = isEdit ? 'PUT' : 'POST';

    const result = await apiFetch(url, { method, body: payload });

    const esSuerte = !isEdit && ((Math.random() < 0.05) || (e && e.shiftKey) || window.__forceMoneyRain);
    if (esSuerte && window.triggerMoneyRain) {
      window.triggerMoneyRain();
      Toast.success(
        '🍀 ¡Día de Suerte!',
        `${result.numero_factura} emitida con lluvia de la fortuna · Total: ${formatCurrency(result.total_factura)}`
      );
    } else {
      Toast.success(
        isEdit ? '¡Factura actualizada!' : '¡Factura emitida!',
        `${result.numero_factura} · Total: ${formatCurrency(result.total_factura)}`
      );
    }

    // Open PDF in new tab and redirect (más tiempo si hay celebración visual)
    const redirectDelay = esSuerte ? 3600 : 1000;
    setTimeout(() => {
      window.open(`/api/facturas/${result.id}/pdf`, '_blank');
      window.location.href = '/';
    }, redirectDelay);
  } catch (err) {
    Toast.error(isEdit ? 'Error al actualizar factura' : 'Error al emitir factura', err.message);
    if (btn) btn.disabled = false;
    if (btnSide) btnSide.disabled = false;
    const origText = isEdit ? 'Guardar Cambios y Descargar PDF' : 'Emitir Factura y Descargar PDF';
    if (btnText) btnText.textContent = origText;
    if (btnSideText) btnSideText.textContent = origText;
  } finally {
    _isSubmittingFactura = false;
    Loading.hide();
  }
}

// ============================================================
//  CLIENTES PAGE
// ============================================================
async function initClientesPage() {
  await loadClientes();

  document.getElementById('filter-search-cliente')?.addEventListener('input', debounce(() => {
    loadClientes(1, document.getElementById('filter-search-cliente').value);
  }, 300));

  document.getElementById('btn-nuevo-cliente')?.addEventListener('click', () => {
    openClienteModal();
  });

  document.getElementById('form-cliente')?.addEventListener('submit', submitCliente);
  document.getElementById('btn-close-cliente-modal')?.addEventListener('click', closeClienteModal);
  document.getElementById('btn-cancel-cliente-modal')?.addEventListener('click', closeClienteModal);
}

let _clientesPagination = null;
let _clientesCurrentPage = 1;
let _clientesPageSize = 25;
let _clientesSearchQuery = '';

async function loadClientes(page = 1, q = null) {
  const tbody = document.getElementById('clientes-tbody');
  if (!tbody) return;
  if (q !== null) _clientesSearchQuery = q;
  _clientesCurrentPage = page;

  try {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 32px; color: var(--mac-text-tertiary);">Cargando directorio de clientes...</td></tr>';
    let url = `/api/clientes?paginated=true&page=${_clientesCurrentPage}&page_size=${_clientesPageSize}`;
    if (_clientesSearchQuery) url += `&q=${encodeURIComponent(_clientesSearchQuery)}`;

    const res = await apiFetch(url);
    const clientes = res.items || [];
    tbody.innerHTML = '';
    if (!clientes.length) {
      tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state"><div class="empty-icon">👥</div><h3>Sin clientes</h3><p>No se encontraron clientes que coincidan con la búsqueda.</p></div></td></tr>';
    } else {
      clientes.forEach(c => {
        const tr = document.createElement('tr');
        const nifDisplay = c.nif_cif
          ? `<span class="font-mono">${escapeHtml(c.nif_cif)}</span>`
          : `<span class="badge badge-borrador">Particular</span>`;
        tr.innerHTML = `
          <td>${nifDisplay}</td>
          <td><strong>${escapeHtml(c.razon_social)}</strong></td>
          <td class="hide-mobile">${escapeHtml(c.telefono || '—')}</td>
          <td class="hide-mobile">${escapeHtml(c.ciudad || '—')}</td>
          <td class="hide-mobile">${escapeHtml(c.email || '—')}</td>
          <td class="hide-mobile">${escapeHtml(c.forma_pago_defecto || '—')}</td>
          <td>
            <div class="flex gap-2">
              <button class="btn btn-sm btn-outline btn-editar-cliente" data-id="${c.id}">Editar</button>
              <button class="btn btn-sm btn-danger btn-eliminar-cliente" data-id="${c.id}" data-nombre="${escapeHtml(c.razon_social)}" style="opacity:0.7">Eliminar</button>
            </div>
          </td>
        `;
        tbody.appendChild(tr);
      });

      if (!tbody._hasActionsListener) {
        tbody._hasActionsListener = true;
        tbody.addEventListener('click', (e) => {
          const btnEditar = e.target.closest('.btn-editar-cliente');
          if (btnEditar) {
            const id = parseInt(btnEditar.dataset.id, 10);
            editCliente(id);
            return;
          }
          const btnEliminar = e.target.closest('.btn-eliminar-cliente');
          if (btnEliminar) {
            const id = parseInt(btnEliminar.dataset.id, 10);
            const nombre = btnEliminar.dataset.nombre;
            deleteCliente(id, nombre);
            return;
          }
        });
      }
    }

    const countEl = document.getElementById('status-clientes-count');
    if (countEl) {
      countEl.textContent = `${res.total} cliente${res.total === 1 ? '' : 's'}`;
    }

    if (!_clientesPagination) {
      _clientesPagination = new MacPagination({
        container: 'clientes-pagination-container',
        initialPageSize: _clientesPageSize,
        onPageChange: (newPage) => loadClientes(newPage),
        onPageSizeChange: (newSize) => {
          _clientesPageSize = newSize;
          loadClientes(1);
        }
      });
    }
    _clientesPagination.render({
      page: res.page,
      pageSize: res.page_size,
      total: res.total,
      totalPages: res.total_pages
    });
  } catch (e) {
    Toast.error('Error', 'No se pudieron cargar los clientes: ' + e.message);
  }
}

let _editingClienteId = null;

function openClienteModal(data = null) {
  _editingClienteId = data?.id || null;
  const modal = document.getElementById('cliente-modal');
  if (!modal) return;
  document.getElementById('modal-cliente-title').textContent = data ? 'Editar Cliente' : 'Nuevo Cliente';
  const form = document.getElementById('form-cliente');
  if (form) {
    form.reset();
    clearFormErrors(form);
  }
  if (data) {
    for (const [k, v] of Object.entries(data)) {
      const el = form.elements[k];
      if (el && v !== null && v !== undefined) el.value = v;
    }
  }
  modal.classList.add('show');
}

function closeClienteModal() {
  document.getElementById('cliente-modal')?.classList.remove('show');
  _editingClienteId = null;
}

async function editCliente(id) {
  try {
    const c = await apiFetch(`/api/clientes/${id}`);
    openClienteModal(c);
  } catch (e) { Toast.error('Error', e.message); }
}

async function deleteCliente(id, nombre) {
  try {
    let title = `¿Eliminar a ${nombre}?`;
    let detailHtml = `<p style="margin: 0 0 8px 0;">¿Estás seguro de que deseas mover a la papelera el cliente <strong>${escapeHtml(nombre)}</strong>?</p>`;
    let isCascade = false;

    try {
      const asociados = await apiFetch(`/api/clientes/${id}/asociados`);
      if (asociados.total_facturas > 0 || asociados.total_presupuestos > 0) {
        isCascade = true;
        title = `Eliminar cliente y documentos`;
        detailHtml = `
          <p style="margin: 0 0 10px 0; color: var(--mac-text-primary); font-weight: 500;">
            El cliente <strong>${escapeHtml(nombre)}</strong> tiene documentos activos vinculados:
          </p>
          <div style="background: #FFF8E6; border: 1px solid rgba(255, 149, 0, 0.35); border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; font-size: 12.5px;">
            <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 4px;">
              <span style="font-weight: 700; color: #B45309;">• Facturas vinculadas:</span>
              <span class="font-mono" style="font-weight: 600; color: var(--mac-text-primary);">${asociados.total_facturas}</span>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
              <span style="font-weight: 700; color: #B45309;">• Presupuestos vinculados:</span>
              <span class="font-mono" style="font-weight: 600; color: var(--mac-text-primary);">${asociados.total_presupuestos}</span>
            </div>
          </div>
          <p style="margin: 0; font-size: 12px; color: var(--mac-system-red); line-height: 1.45;">
            <strong>Aviso de borrado en cascada:</strong> Si continúas, <u>también se eliminarán </u> todas sus facturas y presupuestos asociados. Podrán restaurarse más adelante desde la papelera si es necesario.
          </p>
        `;
      }
    } catch (e) {
      detailHtml = `<p style="margin: 0;">¿Estás seguro de que deseas mover a la papelera el cliente <strong>${escapeHtml(nombre)}</strong> y sus documentos asociados?</p>`;
    }

    const confirmado = await showMacConfirmDialog({
      title: title,
      detailHtml: detailHtml,
      confirmText: isCascade ? 'Eliminar Todo en Cascada' : 'Eliminar Cliente',
      cancelText: 'Cancelar',
      isDestructive: true
    });

    if (!confirmado) return;

    const res = await apiFetch(`/api/clientes/${id}`, { method: 'DELETE' });
    let detailMsg = 'Movido a papelera';
    if (res.facturas_eliminadas || res.presupuestos_eliminados) {
      detailMsg += ` (${res.facturas_eliminadas || 0} facturas y ${res.presupuestos_eliminados || 0} presupuestos)`;
    }
    Toast.success('Cliente eliminado', detailMsg);
    loadClientes();
    actualizarContadoresSidebar();
  } catch (e) {
    Toast.error('Error', e.message);
  }
}

async function submitCliente(e) {
  e.preventDefault();
  const form = e.target;
  clearFormErrors(form);
  const data = Object.fromEntries(new FormData(form));

  // Limpiar campos vacíos
  if (data.nif_cif && !data.nif_cif.trim()) delete data.nif_cif;
  if (data.telefono && !data.telefono.trim()) delete data.telefono;
  if (data.email && !data.email.trim()) delete data.email;

  try {
    if (_editingClienteId) {
      await apiFetch(`/api/clientes/${_editingClienteId}`, { method: 'PUT', body: data });
      Toast.success('Cliente actualizado', 'Los datos han sido guardados correctamente');
    } else {
      await apiFetch('/api/clientes', { method: 'POST', body: data });
      Toast.success('Cliente creado', 'Cliente registrado correctamente');
    }
    closeClienteModal();
    loadClientes();
    actualizarContadoresSidebar();
  } catch (e) {
    displayFormErrors(form, e, 'Error al guardar cliente');
  }
}

// ============================================================
//  ProductoS PAGE
// ============================================================
async function initProductosPage() {
  await loadProductos();
  document.getElementById('filter-search-producto')?.addEventListener('input', debounce(() => {
    loadProductos(1, document.getElementById('filter-search-producto').value);
  }, 300));
  document.getElementById('btn-nuevo-producto')?.addEventListener('click', () => openProductoModal());
  document.getElementById('form-producto')?.addEventListener('submit', submitProducto);
  document.getElementById('btn-close-producto-modal')?.addEventListener('click', closeProductoModal);
  document.getElementById('btn-cancel-producto-modal')?.addEventListener('click', closeProductoModal);
}

let _currentProductoEscalados = [];
let _currentProductoVariantes = [];

function switchProductoTab(tab) {
  ['general', 'escalados', 'variantes'].forEach(t => {
    const btn = document.getElementById(`tab-btn-prod-${t}`);
    const content = document.getElementById(`prod-tab-content-${t}`);
    if (btn) btn.classList.toggle('active', t === tab);
    if (content) content.style.display = (t === tab) ? 'block' : 'none';
  });
}

function actualizarBadgesModalProducto() {
  const badgeEsc = document.getElementById('badge-count-escalados');
  if (badgeEsc) {
    badgeEsc.textContent = _currentProductoEscalados.length;
    badgeEsc.style.display = _currentProductoEscalados.length > 0 ? 'inline-block' : 'none';
  }
  const badgeVar = document.getElementById('badge-count-variantes');
  if (badgeVar) {
    badgeVar.textContent = _currentProductoVariantes.length;
    badgeVar.style.display = _currentProductoVariantes.length > 0 ? 'inline-block' : 'none';
  }
}

function renderEscaladosTable() {
  const tbody = document.getElementById('escalados-tbody');
  const empty = document.getElementById('escalados-empty');
  if (!tbody) return;
  tbody.innerHTML = '';
  if (!_currentProductoEscalados.length) {
    if (empty) empty.style.display = 'block';
  } else {
    if (empty) empty.style.display = 'none';
    _currentProductoEscalados.forEach((esc, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="padding: 4px 6px;">
          <input type="number" class="form-control form-control-sm" min="1" step="1" value="${esc.cantidad_minima || 1}" oninput="_currentProductoEscalados[${idx}].cantidad_minima = parseFloat(this.value) || 1" placeholder="Mínimo">
        </td>
        <td style="padding: 4px 6px;">
          <input type="number" class="form-control form-control-sm" min="1" step="1" value="${esc.cantidad_maxima !== null && esc.cantidad_maxima !== undefined ? esc.cantidad_maxima : ''}" oninput="_currentProductoEscalados[${idx}].cantidad_maxima = this.value ? parseFloat(this.value) : null" placeholder="En adelante…">
        </td>
        <td style="padding: 4px 6px;">
          <input type="number" class="form-control form-control-sm" min="0" step="0.01" style="text-align: right;" value="${esc.precio_unitario || 0}" oninput="_currentProductoEscalados[${idx}].precio_unitario = parseFloat(this.value) || 0" placeholder="0,00">
        </td>
        <td style="padding: 4px 6px; text-align: center;">
          <button type="button" class="btn-icon" style="color: var(--mac-system-red); font-size: 13px;" onclick="eliminarFilaEscalado(${idx})" title="Eliminar tramo">✕</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }
  actualizarBadgesModalProducto();
}

function agregarFilaEscalado(data = null) {
  let min = 1;
  if (_currentProductoEscalados.length > 0) {
    const last = _currentProductoEscalados[_currentProductoEscalados.length - 1];
    min = (last.cantidad_maxima ? Number(last.cantidad_maxima) + 1 : Number(last.cantidad_minima) + 50);
  }
  _currentProductoEscalados.push({
    cantidad_minima: data?.cantidad_minima || min,
    cantidad_maxima: data?.cantidad_maxima !== undefined ? data.cantidad_maxima : null,
    precio_unitario: data?.precio_unitario !== undefined ? data.precio_unitario : 0.0
  });
  renderEscaladosTable();
}

function eliminarFilaEscalado(idx) {
  _currentProductoEscalados.splice(idx, 1);
  renderEscaladosTable();
}

function renderVariantesTable() {
  const tbody = document.getElementById('variantes-tbody');
  const empty = document.getElementById('variantes-empty');
  if (!tbody) return;
  tbody.innerHTML = '';
  if (!_currentProductoVariantes.length) {
    if (empty) empty.style.display = 'block';
  } else {
    if (empty) empty.style.display = 'none';
    _currentProductoVariantes.forEach((v, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="padding: 4px 6px;">
          <select class="form-control form-control-sm" onchange="_currentProductoVariantes[${idx}].tipo_atributo = this.value">
            <option value="Color" ${v.tipo_atributo === 'Color' ? 'selected' : ''}>Color</option>
            <option value="Acabado" ${v.tipo_atributo === 'Acabado' ? 'selected' : ''}>Acabado</option>
            <option value="Tamaño" ${v.tipo_atributo === 'Tamaño' ? 'selected' : ''}>Tamaño</option>
            <option value="Papel" ${v.tipo_atributo === 'Papel' ? 'selected' : ''}>Papel</option>
            <option value="Otro" ${v.tipo_atributo === 'Otro' ? 'selected' : ''}>Otro</option>
          </select>
        </td>
        <td style="padding: 4px 6px;">
          <input type="text" class="form-control form-control-sm" value="${escapeHtml(v.valor || '')}" oninput="_currentProductoVariantes[${idx}].valor = this.value" placeholder="Ej. Kraft / Blanco Roto">
        </td>
        <td style="padding: 4px 6px; text-align: center;">
          <input type="color" style="width: 26px; height: 24px; padding: 0; border: none; background: transparent; cursor: pointer; vertical-align: middle;" value="${v.color_hex || '#556B2F'}" onchange="_currentProductoVariantes[${idx}].color_hex = this.value">
        </td>
        <td style="padding: 4px 6px;">
          <input type="number" class="form-control form-control-sm" step="0.01" style="text-align: right;" value="${v.precio_adicional || 0}" oninput="_currentProductoVariantes[${idx}].precio_adicional = parseFloat(this.value) || 0" placeholder="0,00">
        </td>
        <td style="padding: 4px 6px; text-align: center;">
          <button type="button" class="btn-icon" style="color: var(--mac-system-red); font-size: 13px;" onclick="eliminarFilaVariante(${idx})" title="Eliminar variante">✕</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }
  actualizarBadgesModalProducto();
}

function agregarFilaVariante(data = null) {
  _currentProductoVariantes.push({
    tipo_atributo: data?.tipo_atributo || 'Color',
    valor: data?.valor || '',
    sku_variante: data?.sku_variante || '',
    precio_adicional: data?.precio_adicional || 0.0,
    precio_fijo: data?.precio_fijo || null,
    color_hex: data?.color_hex || '#556B2F'
  });
  renderVariantesTable();
}

function eliminarFilaVariante(idx) {
  _currentProductoVariantes.splice(idx, 1);
  renderVariantesTable();
}

if (typeof window !== 'undefined') {
  window.switchProductoTab = switchProductoTab;
  window.agregarFilaEscalado = agregarFilaEscalado;
  window.eliminarFilaEscalado = eliminarFilaEscalado;
  window.agregarFilaVariante = agregarFilaVariante;
  window.eliminarFilaVariante = eliminarFilaVariante;
}

let _productosPagination = null;
let _productosCurrentPage = 1;
let _productosPageSize = 25;
let _productosSearchQuery = '';

async function loadProductos(page = 1, q = null) {
  const tbody = document.getElementById('productos-tbody');
  if (!tbody) return;
  if (q !== null) _productosSearchQuery = q;
  _productosCurrentPage = page;

  try {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 32px; color: var(--mac-text-tertiary);">Cargando catálogo...</td></tr>';
    let url = `/api/productos?paginated=true&page=${_productosCurrentPage}&page_size=${_productosPageSize}`;
    if (_productosSearchQuery) url += `&q=${encodeURIComponent(_productosSearchQuery)}`;

    const res = await apiFetch(url);
    const productos = res.items || [];
    tbody.innerHTML = '';
    if (!productos.length) {
      tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state"><div class="empty-icon">📦</div><h3>Sin productos</h3><p>No se encontraron productos que coincidan con la búsqueda.</p></div></td></tr>';
    } else {
      productos.forEach(c => {
        const tr = document.createElement('tr');
        const nombreDisplay = c.nombre ? escapeHtml(c.nombre) : `<span style="color:var(--mac-text-secondary);">${escapeHtml(c.descripcion)}</span>`;
        const descDisplay = escapeHtml(c.descripcion || '—');

        // Badges para variantes
        let varBadges = '';
        if (c.variantes && c.variantes.length > 0) {
          varBadges = `<div style="display: flex; gap: 4px; flex-wrap: wrap; align-items: center;">`;
          c.variantes.slice(0, 3).forEach(v => {
            const dot = v.color_hex ? `<span style="display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: ${v.color_hex}; border: 1px solid rgba(0,0,0,0.15); margin-right: 3px;"></span>` : '';
            varBadges += `<span class="badge" style="font-size: 10px; padding: 1px 5px; background: #F3F4F6; color: var(--mac-text-primary); border: 1px solid var(--mac-separator-subtle);">${dot}${escapeHtml(v.valor)}</span>`;
          });
          if (c.variantes.length > 3) {
            varBadges += `<span class="badge" style="font-size: 10px; padding: 1px 4px; background: #E5E7EB; color: #4B5563;">+${c.variantes.length - 3}</span>`;
          }
          varBadges += `</div>`;
        } else {
          varBadges = `<span style="color: var(--mac-text-tertiary); font-size: 11px;">—</span>`;
        }

        // Badge para escalados de precio
        let escBadge = '';
        if (c.escalados && c.escalados.length > 0) {
          escBadge = `<div style="font-size: 10px; color: #059669; font-weight: 600; margin-top: 2px;">• ${c.escalados.length} tramos volumen</div>`;
        }

        tr.innerHTML = `
          <td style="font-weight: 600; white-space: normal; word-break: break-word; line-height: 1.35; max-width: 240px;">${nombreDisplay}</td>
          <td>${varBadges}</td>
          <td class="col-producto-desc" style="color: var(--mac-text-secondary); max-width: 380px; min-width: 200px; white-space: normal; word-break: break-word; overflow-wrap: break-word; line-height: 1.4;" title="${descDisplay}">
            ${descDisplay}
          </td>
          <td class="text-right" style="font-weight: 500; white-space: nowrap;">
            ${formatCurrency(c.precio_unitario_base)}
            ${escBadge}
          </td>
          <td class="text-center" style="white-space: nowrap;">${c.porcentaje_iva}%</td>
          <td class="text-center" style="white-space: nowrap;">${c.aplica_irpf ? c.porcentaje_irpf + '%' : '—'}</td>
          <td style="text-align: right; white-space: nowrap;">
            <div style="display: inline-flex; gap: 4px; justify-content: flex-end;">
              <button type="button" class="btn-native btn-edit-prod" style="height: 22px; font-size: 11px; padding: 0 6px;">Editar</button>
              <button type="button" class="btn-native btn-danger btn-delete-prod" style="height: 22px; font-size: 11px; padding: 0 6px;">Eliminar</button>
            </div>
          </td>
        `;
        tr.querySelector('.btn-edit-prod').addEventListener('click', () => editProducto(c.id));
        tr.querySelector('.btn-delete-prod').addEventListener('click', () => deleteProducto(c.id, c.nombre || c.descripcion || ''));
        tbody.appendChild(tr);
      });
    }

    const countEl = document.getElementById('status-productos-count');
    if (countEl) {
      countEl.textContent = `${res.total} producto${res.total === 1 ? '' : 's'}`;
    }

    if (!_productosPagination) {
      _productosPagination = new MacPagination({
        container: 'productos-pagination-container',
        initialPageSize: _productosPageSize,
        onPageChange: (newPage) => loadProductos(newPage),
        onPageSizeChange: (newSize) => {
          _productosPageSize = newSize;
          loadProductos(1);
        }
      });
    }
    _productosPagination.render({
      page: res.page,
      pageSize: res.page_size,
      total: res.total,
      totalPages: res.total_pages
    });

    if (typeof window.actualizarContadoresSidebar === 'function') {
      window.actualizarContadoresSidebar();
    }
  } catch (e) { Toast.error('Error', 'No se pudieron cargar los productos'); }
}

let _editingProductoId = null;

function openProductoModal(data = null) {
  _editingProductoId = data?.id || null;
  const modal = document.getElementById('producto-modal');
  if (!modal) return;
  document.getElementById('modal-producto-title').textContent = data ? 'Editar Producto' : 'Nuevo Producto';
  const form = document.getElementById('form-producto');
  if (form) {
    form.reset();
    clearFormErrors(form);
  }
  if (data) {
    for (const [k, v] of Object.entries(data)) {
      const el = form.elements[k];
      if (el && v !== null && v !== undefined) el.value = v;
    }
    const irpfCheck = form.querySelector('[name=aplica_irpf]');
    if (irpfCheck) irpfCheck.checked = !!data.aplica_irpf;
  }

  // Cargar escalados y variantes
  switchProductoTab('general');
  _currentProductoEscalados = (data?.escalados || []).map(e => ({ ...e }));
  _currentProductoVariantes = (data?.variantes || []).map(v => ({ ...v }));
  renderEscaladosTable();
  renderVariantesTable();

  modal.classList.add('show');
}

function closeProductoModal() {
  document.getElementById('producto-modal')?.classList.remove('show');
  _editingProductoId = null;
  _currentProductoEscalados = [];
  _currentProductoVariantes = [];
}

async function editProducto(id) {
  try {
    const c = await apiFetch(`/api/productos/${id}`);
    openProductoModal(c);
  } catch (e) { Toast.error('Error', e.message); }
}

async function deleteProducto(id, nombreProducto = '') {
  let nombre = nombreProducto;
  if (!nombre) {
    const c = await apiFetch(`/api/productos/${id}`).catch(() => null);
    nombre = c ? (c.nombre || c.descripcion || `#${id}`) : `#${id}`;
  }

  const fnConfirm = window.showMacConfirmDialog || window.showMacConfirm;
  let ok = false;
  if (typeof fnConfirm === 'function') {
    ok = await fnConfirm({
      title: `¿Eliminar "${nombre}"?`,
      detailHtml: `
        <p style="margin: 0 0 8px 0;">
          ¿Deseas eliminar el producto <strong style="color: var(--mac-text-primary);">${escapeHtml(nombre)}</strong> del catálogo?
        </p>
        <p style="margin: 0; font-size: 12px; color: var(--mac-text-secondary); line-height: 1.45;">
          Esta acción eliminará el producto del catálogo para futuras selecciones. Las facturas y presupuestos emitidos anteriormente conservarán todos sus datos intactos.
        </p>
      `,
      confirmText: 'Eliminar Producto',
      cancelText: 'Cancelar',
      isDestructive: true
    });
  } else {
    ok = confirm(`¿Eliminar el producto "${nombre}"?`);
  }
  if (!ok) return;

  try {
    await apiFetch(`/api/productos/${id}`, { method: 'DELETE' });
    Toast.success('Producto eliminado', `El producto "${nombre}" ha sido eliminado del catálogo.`);
    loadProductos();
    if (typeof window.actualizarContadoresSidebar === 'function') {
      window.actualizarContadoresSidebar();
    }
  } catch (e) { Toast.error('Error al eliminar', e.message); }
}

async function submitProducto(e) {
  e.preventDefault();
  const form = e.target;
  clearFormErrors(form);

  const rawCodigo = form.elements['codigo']?.value?.trim() || '';
  const rawNombre = form.elements['nombre']?.value?.trim() || '';
  const rawDesc = form.elements['descripcion']?.value?.trim() || '';
  const rawPrecioStr = form.elements['precio_unitario_base']?.value?.trim();

  // Validación de campos obligatorios marcados con *
  const clientErrors = [];
  if (!rawNombre) {
    clientErrors.push({ field: 'nombre', message: "El campo 'Nombre del producto' no puede estar vacío." });
  }
  if (!rawDesc) {
    clientErrors.push({ field: 'descripcion', message: "El campo 'Descripción / Detalle Técnico' no puede estar vacío." });
  }
  if (!rawPrecioStr || isNaN(parseFloat(rawPrecioStr)) || parseFloat(rawPrecioStr) < 0) {
    clientErrors.push({ field: 'precio_unitario_base', message: "El campo 'Precio Base' es obligatorio y debe ser mayor o igual a 0." });
  }

  if (clientErrors.length > 0) {
    displayFormErrors(form, { errors: clientErrors }, 'Campos requeridos');
    return;
  }

  const data = {
    nombre: rawNombre,
    descripcion: rawDesc,
    precio_unitario_base: parseFloat(rawPrecioStr),
    porcentaje_iva: parseFloat(form.elements['porcentaje_iva']?.value) || 21,
    porcentaje_irpf: parseFloat(form.elements['porcentaje_irpf']?.value) || 0,
    aplica_irpf: form.querySelector('[name=aplica_irpf]')?.checked || false,
    escalados: _currentProductoEscalados.filter(e => e.cantidad_minima && e.precio_unitario !== undefined),
    variantes: _currentProductoVariantes.filter(v => v.valor && v.valor.trim())
  };
  if (rawCodigo) data.codigo = rawCodigo;

  try {
    if (_editingProductoId) {
      await apiFetch(`/api/productos/${_editingProductoId}`, { method: 'PUT', body: data });
      Toast.success('Producto actualizado', 'Cambios guardados');
    } else {
      await apiFetch('/api/productos', { method: 'POST', body: data });
      Toast.success('Producto creado', 'Nuevo producto añadido al catálogo');
    }
    closeProductoModal();
    loadProductos();
    if (typeof window.actualizarContadoresSidebar === 'function') {
      window.actualizarContadoresSidebar();
    }
  } catch (e) {
    displayFormErrors(form, e, 'Error al guardar producto');
  }
}

// ============================================================
//  UTILITIES
// ============================================================
function debounce(fn, ms) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

async function verificarConfiguracionGlobal() {
  try {
    const res = await fetch('/api/configuracion');
    if (!res.ok) return null;
    const data = await res.json();
    const alertContainer = document.getElementById('global-config-alert');
    if (alertContainer) {
      if (!data.es_valida) {
        alertContainer.className = 'alert-banner';
        alertContainer.innerHTML = `
          <div class="alert-banner-content">
            <span class="status-dot vencida" style="display:inline-block; margin-right:8px;"></span>
            <span><strong>Ajustes pendientes:</strong> Complete los datos fiscales del emisor (Razón social y NIF) en Ajustes para habilitar la emisión de facturas oficiales.</span>
          </div>
          <a href="/configuracion" class="btn-native btn-primary" style="font-size:12px;">Ir a Ajustes</a>
        `;
      } else {
        alertContainer.className = 'hidden';
        alertContainer.innerHTML = '';
      }
    }
    return data;
  } catch (e) {
    console.error('Error comprobando configuración global:', e);
    return null;
  }
}

// ============================================================
//  ROUTER / PAGE INIT
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  Toast.init();
  verificarConfiguracionGlobal();

  const path = window.location.pathname;

  // Highlight active nav link
  document.querySelectorAll('.navbar-nav a').forEach(a => {
    if (a.getAttribute('href') === path) a.classList.add('active');
  });

  // Filters on dashboard
  document.getElementById('filter-search')?.addEventListener('input', debounce(() => {
    loadRecentInvoices(getActiveFilters());
  }, 300));

  document.getElementById('filter-estado')?.addEventListener('change', () => {
    loadRecentInvoices(getActiveFilters());
  });

  document.getElementById('filter-desde')?.addEventListener('change', () => {
    loadRecentInvoices(getActiveFilters());
  });

  document.getElementById('filter-hasta')?.addEventListener('change', () => {
    loadRecentInvoices(getActiveFilters());
  });

  // Page-specific init
  const isEditFactura = /^\/facturas\/\d+\/editar\/?$/.test(path);
  if (path === '/' || path === '') initDashboard();
  else if (path === '/nueva-factura' || isEditFactura) initNuevaFactura();
  else if (path === '/clientes') initClientesPage();
  else if (path === '/productos') initProductosPage();

  // Sincronizar contadores de la barra lateral nativa en todas las páginas
  actualizarContadoresSidebar();

  // Close modals on overlay click
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.classList.remove('show');
    });
  });
});

// ============================================================
//  CONTADORES GLOBALES DE BARRA LATERAL (SOURCE LIST)
// ============================================================
async function actualizarContadoresSidebar() {
  try {
    const setBadge = (id, val) => {
      const el = document.getElementById(id);
      if (el && val !== undefined && val !== null) {
        el.textContent = String(val);
      }
    };

    const data = await apiFetch('/api/contadores').catch(async () => {
      // Fallback si /api/contadores fallara
      const [f, p, c, prod] = await Promise.all([
        apiFetch('/api/facturas?page_size=200').catch(() => []),
        apiFetch('/api/presupuestos').catch(() => []),
        apiFetch('/api/clientes').catch(() => []),
        apiFetch('/api/productos').catch(() => [])
      ]);
      return {
        facturas: Array.isArray(f) ? f.length : 0,
        presupuestos: Array.isArray(p) ? p.length : 0,
        clientes: Array.isArray(c) ? c.length : 0,
        productos: Array.isArray(prod) ? prod.length : 0
      };
    });

    if (data) {
      setBadge('sidebar-badge-facturas', data.facturas);
      setBadge('sidebar-badge-total', data.facturas);
      setBadge('sidebar-badge-presupuestos', data.presupuestos);
      setBadge('sidebar-badge-clientes', data.clientes);
      setBadge('sidebar-badge-productos', data.productos);
      setBadge('sidebar-badge-descuentos', data.descuentos);
      setBadge('sidebar-badge-papelera', data.papelera);
    }
  } catch (err) {
    console.error('Error al actualizar contadores de barra lateral:', err);
  }
}

if (typeof window !== 'undefined') {
  window.actualizarContadoresSidebar = actualizarContadoresSidebar;
}


// ============================================================
// GESTOR DE HISTORIAL DE VERSIONES Y REVERSIÓN (ESTILO TIME MACHINE)
// ============================================================
const VersionHistoryManager = {
  tipo: 'factura', // 'factura' | 'presupuesto'
  entidadId: null,
  entidadNumero: '',
  versiones: [],
  versionSeleccionada: null,

  async abrir(tipo, id, numero) {
    this.tipo = tipo;
    this.entidadId = id;
    this.entidadNumero = numero || (tipo === 'factura' ? `FAC-${id}` : `PRE-${id}`);
    this.versiones = [];
    this.versionSeleccionada = null;

    const modal = document.getElementById('modal-historial-versiones');
    const title = document.getElementById('versiones-modal-title');
    if (title) title.textContent = `Historial de Versiones · ${this.entidadNumero}`;
    if (modal) { modal.classList.add('show'); modal.classList.add('active'); }

    const listaCol = document.getElementById('versiones-lista-col');
    const detCol = document.getElementById('versiones-detalle-col');
    const btnRestaurar = document.getElementById('btn-restaurar-version-seleccionada');
    if (btnRestaurar) btnRestaurar.style.display = 'none';

    if (listaCol) listaCol.innerHTML = '<div style="padding: 24px; text-align: center; color: var(--mac-text-tertiary); font-size: 12px;">Cargando versiones…</div>';
    if (detCol) detCol.innerHTML = '<div style="padding: 40px; text-align: center; color: var(--mac-text-tertiary); font-size: 12px;">Selecciona una versión para previsualizar sus datos.</div>';

    try {
      const endpoint = this.tipo === 'factura' 
        ? `/api/facturas/${id}/versiones` 
        : `/api/presupuestos/${id}/versiones`;
      this.versiones = await apiFetch(endpoint);
      this.renderLista();
      if (this.versiones && this.versiones.length > 0) {
        this.seleccionarVersion(this.versiones[0].numero_version);
      }
    } catch (err) {
      if (listaCol) listaCol.innerHTML = `<div style="padding: 20px; color: var(--mac-system-red); font-size: 12px;">Error: ${escapeHtml(err.message)}</div>`;
    }
  },

  renderLista() {
    const listaCol = document.getElementById('versiones-lista-col');
    if (!listaCol) return;

    if (!this.versiones || this.versiones.length === 0) {
      listaCol.innerHTML = '<div style="padding: 24px; text-align: center; color: var(--mac-text-tertiary); font-size: 12px;">No hay versiones registradas aún para este documento.</div>';
      return;
    }

    const maxVer = Math.max(...this.versiones.map(v => v.numero_version));

    listaCol.innerHTML = this.versiones.map(v => {
      const esActual = v.numero_version === maxVer;
      const isSelected = this.versionSeleccionada && this.versionSeleccionada.numero_version === v.numero_version;
      const totalStr = formatCurrency(v.total_factura !== undefined ? v.total_factura : (v.total_estimado || 0));
      const fechaStr = v.created_at ? v.created_at.substring(0, 16).replace('T', ' ') : '—';

      return `
        <div class="version-item ${isSelected ? 'active' : ''}" 
             onclick="VersionHistoryManager.seleccionarVersion(${v.numero_version})"
             style="padding: 10px 12px; margin-bottom: 6px; border-radius: 8px; cursor: pointer; transition: all 0.15s ease; border: 1px solid ${isSelected ? 'var(--mac-accent)' : 'transparent'}; background: ${isSelected ? '#E8F2FF' : '#FFFFFF'};">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
            <span style="font-weight: 700; font-size: 13px; color: ${isSelected ? 'var(--mac-accent)' : 'var(--mac-text-primary)'};">
              v${v.numero_version} ${esActual ? '<span style="font-size: 10px; padding: 1px 5px; border-radius: 4px; background: rgba(10,132,255,0.12); color: var(--mac-accent); font-weight: 600; margin-left: 4px;">Actual</span>' : ''}
            </span>
            <span style="font-size: 12px; font-weight: 600; color: var(--mac-text-primary);">${totalStr}</span>
          </div>
          <div style="font-size: 11px; color: var(--mac-text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(v.motivo || '')}">
            ${escapeHtml(v.motivo || 'Modificación')}
          </div>
          <div style="font-size: 10px; color: var(--mac-text-tertiary); margin-top: 4px;">
            ${fechaStr}
          </div>
        </div>
      `;
    }).join('');
  },

  async seleccionarVersion(numVersion) {
    const detCol = document.getElementById('versiones-detalle-col');
    const btnRestaurar = document.getElementById('btn-restaurar-version-seleccionada');

    try {
      const endpoint = this.tipo === 'factura' 
        ? `/api/facturas/${this.entidadId}/versiones/${numVersion}` 
        : `/api/presupuestos/${this.entidadId}/versiones/${numVersion}`;
      const det = await apiFetch(endpoint);
      this.versionSeleccionada = det;
      this.renderLista();

      const maxVer = Math.max(...this.versiones.map(v => v.numero_version));
      const esActual = numVersion === maxVer;

      if (btnRestaurar) {
        btnRestaurar.style.display = esActual ? 'none' : 'inline-flex';
        btnRestaurar.textContent = `Restaurar versión v${numVersion}`;
      }

      this.renderDetalle(det, esActual);
    } catch (err) {
      if (detCol) detCol.innerHTML = `<div style="color: var(--mac-system-red); font-size: 12px;">Error al cargar detalle: ${escapeHtml(err.message)}</div>`;
    }
  },

  renderDetalle(det, esActual) {
    const detCol = document.getElementById('versiones-detalle-col');
    if (!detCol) return;

    const snap = det.snapshot || {};
    const total = det.total_factura !== undefined ? det.total_factura : (det.total_estimado || 0);

    if (this.tipo === 'factura') {
      const f = snap.factura || {};
      const lineas = snap.lineas || [];
      const cli = snap.cliente || {};

      detCol.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid var(--mac-separator-subtle); padding-bottom: 12px; margin-bottom: 12px;">
          <div>
            <div style="font-size: 16px; font-weight: 700; color: var(--mac-text-primary);">
              Versión v${det.numero_version} ${esActual ? '<span style="font-size: 11px; color: var(--mac-accent); font-weight: 600;">(Versión en vigor)</span>' : ''}
            </div>
            <div style="font-size: 12px; color: var(--mac-text-secondary); margin-top: 2px;">
              ${escapeHtml(det.motivo || '')} · ${det.created_at ? det.created_at.substring(0, 16).replace('T', ' ') : ''}
            </div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--mac-text-tertiary); font-weight: 600;">Importe Total</div>
            <div style="font-size: 18px; font-weight: 700; color: var(--mac-accent);">${formatCurrency(total)}</div>
          </div>
        </div>

        <div style="font-size: 12px; color: var(--mac-text-secondary); margin-bottom: 12px;">
          <strong>Cliente:</strong> ${escapeHtml(cli.razon_social || f.cliente_razon_social || '—')} 
          ${cli.nif_cif ? `(${escapeHtml(cli.nif_cif)})` : ''} · 
          <strong>Fecha emisión:</strong> ${f.fecha_emision || '—'}
        </div>

        <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--mac-text-tertiary); margin-bottom: 6px;">
          Partidas de esta versión (${lineas.length})
        </div>

        <div style="border: 1px solid var(--mac-separator-subtle); border-radius: 6px; overflow: hidden; background: #FFF;">
          <table class="table" style="margin: 0; font-size: 11px;">
            <thead>
              <tr style="background: #F9FAFB;">
                <th>Descripción</th>
                <th style="text-align: center; width: 60px;">Cant.</th>
                <th style="text-align: right; width: 80px;">Precio</th>
                <th style="text-align: right; width: 80px;">Subtotal</th>
              </tr>
            </thead>
            <tbody>
              ${lineas.map(l => `
                <tr>
                  <td>
                    <strong>${escapeHtml(l.descripcion || '—')}</strong>
                    ${l.detalle_material ? `<div style="color: var(--mac-text-tertiary); font-size: 10px;">${escapeHtml(l.detalle_material)}</div>` : ''}
                  </td>
                  <td style="text-align: center;">${l.cantidad}</td>
                  <td style="text-align: right;">${formatCurrency(l.precio_unitario)}</td>
                  <td style="text-align: right; font-weight: 600;">${formatCurrency(l.subtotal_base || (l.cantidad * l.precio_unitario))}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    } else {
      // Presupuesto
      const p = snap.presupuesto || {};
      const opciones = snap.opciones || [];
      const cli = snap.cliente || {};

      detCol.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid var(--mac-separator-subtle); padding-bottom: 12px; margin-bottom: 12px;">
          <div>
            <div style="font-size: 16px; font-weight: 700; color: var(--mac-text-primary);">
              Versión v${det.numero_version} ${esActual ? '<span style="font-size: 11px; color: var(--mac-accent); font-weight: 600;">(Versión en vigor)</span>' : ''}
            </div>
            <div style="font-size: 12px; color: var(--mac-text-secondary); margin-top: 2px;">
              ${escapeHtml(det.motivo || '')} · ${det.created_at ? det.created_at.substring(0, 16).replace('T', ' ') : ''}
            </div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--mac-text-tertiary); font-weight: 600;">Total Estimado</div>
            <div style="font-size: 18px; font-weight: 700; color: var(--mac-accent);">${formatCurrency(total)}</div>
          </div>
        </div>

        <div style="font-size: 12px; color: var(--mac-text-secondary); margin-bottom: 12px;">
          <strong>Cliente:</strong> ${escapeHtml(cli.razon_social || '—')} · 
          <strong>Título:</strong> ${escapeHtml(p.titulo || 'Presupuesto')} (${opciones.length} opciones)
        </div>

        <div style="display: flex; flex-direction: column; gap: 10px;">
          ${opciones.map(op => `
            <div style="border: 1px solid var(--mac-separator-subtle); border-radius: 6px; overflow: hidden; background: #FFF;">
              <div style="background: #F9FAFB; padding: 6px 10px; font-weight: 600; font-size: 11px; display: flex; justify-content: space-between; border-bottom: 1px solid var(--mac-separator-subtle);">
                <span>${escapeHtml(op.nombre_opcion)}</span>
                <span style="color: var(--mac-accent);">${formatCurrency(op.total || 0)}</span>
              </div>
              <table class="table" style="margin: 0; font-size: 11px;">
                <tbody>
                  ${(op.lineas || []).map(l => `
                    <tr>
                      <td style="word-break: break-word; overflow-wrap: break-word;">
                        <strong>${escapeHtml(l.descripcion || '—')}</strong>
                        ${l.detalle_material ? `<div style="color: var(--mac-text-tertiary); font-size: 10px; word-break: break-word;">${escapeHtml(l.detalle_material)}</div>` : ''}
                      </td>
                      <td style="text-align: center; width: 50px;">${l.cantidad}</td>
                      <td style="text-align: right; width: 70px;">${formatCurrency(l.precio_unitario)}</td>
                      <td style="text-align: right; width: 70px; font-weight: 600;">${formatCurrency(l.total || (l.cantidad * l.precio_unitario))}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          `).join('')}
        </div>
      `;
    }
  },

  async ejecutarRestauracion() {
    if (!this.versionSeleccionada) return;
    const numVer = this.versionSeleccionada.numero_version;

    const doRestore = async () => {
      try {
        const endpoint = this.tipo === 'factura'
          ? `/api/facturas/${this.entidadId}/versiones/${numVer}/restaurar`
          : `/api/presupuestos/${this.entidadId}/versiones/${numVer}/restaurar`;
        await apiFetch(endpoint, { method: 'POST' });
        Toast.success('Versión restaurada', `El documento se ha revertido a la versión v${numVer}.`);
        this.cerrar();
        if (this.tipo === 'factura' && typeof cargarFacturasMacOS === 'function') {
          cargarFacturasMacOS();
        } else if (this.tipo === 'presupuesto' && typeof cargarPresupuestos === 'function') {
          cargarPresupuestos();
        } else {
          window.location.reload();
        }
      } catch (err) {
        Toast.error('Error al restaurar versión', err.message);
      }
    };

    const fnConfirm = window.showMacConfirmDialog || window.showMacConfirm;
    let confirmado = false;
    if (typeof fnConfirm === 'function') {
      confirmado = await fnConfirm({
        title: `¿Restaurar a la versión v${numVer}?`,
        detailHtml: `
          <p style="margin: 0 0 8px 0; font-size: 13px; color: var(--mac-text-primary);">
            ¿Deseas revertir este documento a la <strong>versión v${numVer}</strong>?
          </p>
          <p style="margin: 0; font-size: 12px; color: var(--mac-text-secondary); line-height: 1.45;">
            El estado actual se archivará automáticamente como una nueva versión en el historial para preservar la trazabilidad fiscal.
          </p>
        `,
        confirmText: `Restaurar v${numVer}`,
        cancelText: 'Cancelar',
        isDestructive: false
      });
    } else {
      confirmado = window.confirm(`¿Deseas revertir este documento a la versión v${numVer}?`);
    }

    if (confirmado) {
      await doRestore();
    }
  },

  cerrar() {
    const modal = document.getElementById('modal-historial-versiones');
    if (modal) { modal.classList.remove('show'); modal.classList.remove('active'); }
  }
};

if (typeof window !== 'undefined') {
  window.VersionHistoryManager = VersionHistoryManager;
}
