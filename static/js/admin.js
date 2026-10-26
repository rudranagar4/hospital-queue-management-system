/**
 * Admin Operations Command Center Dashboard
 * Real-Time Queue Auto-Refresh & Live DOM Reconciliation
 */

document.addEventListener('DOMContentLoaded', () => {
  const adminDashboard = document.getElementById('admin-dashboard-container');
  if (!adminDashboard) return;

  const deptId = adminDashboard.dataset.deptId;
  if (!deptId) return;

  // Poll queue state every 5000ms
  const pollQueueState = async () => {
    try {
      const response = await fetch(`/api/queue/${deptId}`);
      if (!response.ok) return;
      const data = await response.json();

      if (data.status === 'success') {
        renderNowServing(data.now_serving);
        renderEmergencyQueue(data.emergency_queue);
        renderNormalQueue(data.normal_queue);
        renderCounters(data);
      }
    } catch (e) {
      console.warn("Queue polling failed:", e);
    }
  };

  setInterval(pollQueueState, 5000);

  // Keyboard shortcut to Call Next: Shift + C
  document.addEventListener('keydown', (e) => {
    if (e.shiftKey && (e.key === 'C' || e.key === 'c')) {
      const activeEl = document.activeElement;
      if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.tagName === 'SELECT')) {
        return;
      }
      const callNextBtn = document.getElementById('btn-call-next-submit');
      if (callNextBtn) {
        callNextBtn.click();
      }
    }
  });
});

function renderNowServing(nowServing) {
  const container = document.getElementById('now-serving-content');
  if (!container) return;

  if (!nowServing) {
    container.innerHTML = `
      <div class="text-center py-5 text-muted">
        <i class="bi bi-person-slash display-4 mb-2 d-block opacity-50"></i>
        <h4 class="fw-semibold">No Patient Currently Serving</h4>
        <p class="small text-secondary mb-0">Click "Call Next Patient" to serve the next person in line.</p>
      </div>
    `;
    const box = document.getElementById('now-serving-box');
    if (box) {
      box.classList.remove('is-emergency');
    }
    return;
  }

  const isEmergency = nowServing.case_type === 'emergency';
  const box = document.getElementById('now-serving-box');
  if (box) {
    if (isEmergency) {
      box.classList.add('is-emergency');
    } else {
      box.classList.remove('is-emergency');
    }
  }

  const badgeClass = isEmergency ? 'badge-emergency' : 'badge-normal';
  const caseLabel = isEmergency ? `EMERGENCY (${nowServing.severity_label})` : 'NORMAL';

  container.innerHTML = `
    <div class="row align-items-center">
      <div class="col-md-5 text-center text-md-start mb-3 mb-md-0">
        <div class="d-flex align-items-center justify-content-center justify-content-md-start gap-2 mb-2">
          <span class="badge ${badgeClass} text-uppercase px-3 py-2 fs-6">
            <i class="bi ${isEmergency ? 'bi-exclamation-triangle-fill' : 'bi-person-check-fill'} me-1"></i>
            ${caseLabel}
          </span>
          <span class="badge bg-dark border border-secondary text-light px-3 py-2 fs-6">
            ${nowServing.status.replace('_', ' ').toUpperCase()}
          </span>
        </div>
        <div class="now-serving-token">${nowServing.token_number}</div>
        <h3 class="fw-bold text-white mb-0 mt-2">${nowServing.patient_name}</h3>
        <p class="text-secondary small mb-0">
          Phone: ${nowServing.patient_phone || 'N/A'} | Age: ${nowServing.patient_age || 'N/A'}
        </p>
      </div>
      
      <div class="col-md-7">
        <div class="bg-black bg-opacity-30 rounded-3 p-3 border border-secondary border-opacity-25 mb-3">
          <div class="d-flex justify-content-between text-secondary small mb-1">
            <span>Assigned Doctor:</span>
            <strong class="text-light">${nowServing.doctor_name || 'Attending Physician'}</strong>
          </div>
          <div class="d-flex justify-content-between text-secondary small">
            <span>Chief Symptoms:</span>
            <span class="text-light">${nowServing.description || 'General examination / triage'}</span>
          </div>
        </div>

        <div class="d-flex flex-wrap gap-2 justify-content-md-end">
          ${nowServing.status === 'called' ? `
            <form method="POST" action="/admin/token/${nowServing.id}/status/in_consultation" class="d-inline">
              <input type="hidden" name="csrf_token" value="${getCSRFToken()}">
              <button type="submit" class="btn btn-outline-info btn-sm px-3 rounded-pill">
                <i class="bi bi-play-fill me-1"></i> Start Consultation
              </button>
            </form>
          ` : ''}

          <form method="POST" action="/admin/token/${nowServing.id}/status/completed" class="d-inline">
            <input type="hidden" name="csrf_token" value="${getCSRFToken()}">
            <button type="submit" class="btn btn-success btn-sm px-3 rounded-pill fw-bold">
              <i class="bi bi-check2-circle me-1"></i> Complete
            </button>
          </form>

          <form method="POST" action="/admin/token/${nowServing.id}/status/skipped" class="d-inline">
            <input type="hidden" name="csrf_token" value="${getCSRFToken()}">
            <button type="submit" class="btn btn-outline-warning btn-sm px-3 rounded-pill">
              <i class="bi bi-arrow-right-circle me-1"></i> Skip
            </button>
          </form>

          <form method="POST" action="/admin/token/${nowServing.id}/status/cancelled" class="d-inline">
            <input type="hidden" name="csrf_token" value="${getCSRFToken()}">
            <button type="submit" class="btn btn-outline-danger btn-sm px-3 rounded-pill">
              <i class="bi bi-x-circle me-1"></i> No-Show
            </button>
          </form>
        </div>
      </div>
    </div>
  `;
}

function renderEmergencyQueue(queue) {
  const listEl = document.getElementById('emergency-queue-list');
  if (!listEl) return;

  if (queue.length === 0) {
    listEl.innerHTML = `
      <div class="text-center py-4 text-muted small">
        <i class="bi bi-check2-circle fs-3 text-secondary d-block mb-1"></i>
        No emergency cases waiting in priority heap.
      </div>
    `;
    return;
  }

  let html = '';
  queue.forEach((item, idx) => {
    let sevBadge = 'badge-severity-2';
    if (item.severity === 1) sevBadge = 'badge-severity-1';
    else if (item.severity === 3) sevBadge = 'badge-severity-3';

    html += `
      <div class="queue-row-item emergency-item animate-entrance">
        <div class="d-flex align-items-center gap-3">
          <span class="badge ${sevBadge} rounded-pill px-2 py-1 small fw-bold">
            Sev ${item.severity}: ${item.severity_label}
          </span>
          <span class="fw-bold text-white fs-5 font-monospace">${item.token_number}</span>
          <div>
            <span class="d-block fw-semibold text-light">${item.patient_name}</span>
            <span class="text-secondary small">Age: ${item.patient_age || 'N/A'}</span>
          </div>
        </div>
        <div class="text-end">
          <span class="badge bg-danger bg-opacity-25 text-danger border border-danger border-opacity-25 rounded-pill px-2 py-1 small">
            Wait: ~${item.estimated_wait}m
          </span>
        </div>
      </div>
    `;
  });
  listEl.innerHTML = html;
  // Stagger new items
  if (window.staggerRevealItems) staggerRevealItems(listEl, '.queue-row-item', 60);
}

function renderNormalQueue(queue) {
  const listEl = document.getElementById('normal-queue-list');
  if (!listEl) return;

  if (queue.length === 0) {
    listEl.innerHTML = `
      <div class="text-center py-4 text-muted small">
        <i class="bi bi-inbox fs-3 text-secondary d-block mb-1"></i>
        No normal cases waiting in FIFO queue.
      </div>
    `;
    return;
  }

  let html = '';
  queue.forEach((item, idx) => {
    html += `
      <div class="queue-row-item normal-item animate-entrance">
        <div class="d-flex align-items-center gap-3">
          <span class="badge bg-secondary rounded-circle px-2 py-1 small text-white">#${idx + 1}</span>
          <span class="fw-bold text-white fs-5 font-monospace">${item.token_number}</span>
          <div>
            <span class="d-block fw-semibold text-light">${item.patient_name}</span>
            <span class="text-secondary small">Age: ${item.patient_age || 'N/A'}</span>
          </div>
        </div>
        <div class="text-end">
          <span class="badge bg-primary bg-opacity-25 text-primary border border-primary border-opacity-25 rounded-pill px-2 py-1 small">
            Wait: ~${item.estimated_wait}m
          </span>
        </div>
      </div>
    `;
  });
  listEl.innerHTML = html;
  if (window.staggerRevealItems) staggerRevealItems(listEl, '.queue-row-item', 70);
}

function renderCounters(data) {
  const emergCount = document.getElementById('live-count-emergency');
  const normCount  = document.getElementById('live-count-normal');
  const totalCount = document.getElementById('live-count-total');
  const fairnessProgress = document.getElementById('fairness-progress-bar');
  const fairnessText     = document.getElementById('fairness-counter-text');

  // Flip animation on value change
  function updateWithFlip(el, newVal) {
    if (!el) return;
    const old = parseInt(el.innerText, 10);
    const nv  = parseInt(newVal, 10);
    if (old !== nv) {
      el.style.transition = 'transform 0.2s ease, opacity 0.2s ease';
      el.style.transform  = 'translateY(-8px)';
      el.style.opacity    = '0';
      setTimeout(() => {
        el.innerText = newVal;
        el.style.transform = 'translateY(8px)';
        el.style.opacity   = '0';
        // Force reflow
        void el.offsetWidth;
        el.style.transition = 'transform 0.3s cubic-bezier(0.34,1.56,0.64,1), opacity 0.3s ease';
        el.style.transform  = '';
        el.style.opacity    = '1';
      }, 200);
    }
  }

  updateWithFlip(emergCount, data.emergency_count);
  updateWithFlip(normCount,  data.normal_count);
  updateWithFlip(totalCount, data.total_waiting);

  if (fairnessProgress && fairnessText) {
    const percent = Math.min((data.consecutive_emergencies / data.max_consecutive) * 100, 100);
    fairnessProgress.style.width = `${percent}%`;
    fairnessText.innerText = `${data.consecutive_emergencies} / ${data.max_consecutive}`;
  }
}

function getCSRFToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}

