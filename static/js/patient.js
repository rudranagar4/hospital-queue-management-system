/**
 * Patient Dashboard Live Updates & Interactions
 */

document.addEventListener('DOMContentLoaded', () => {
  // Case Type Selector Logic (in Booking Modal / Form)
  const caseTypeRadios = document.querySelectorAll('input[name="case_type"]');
  const emergencyDetails = document.getElementById('emergency-details-section');
  const caseCardNormal = document.getElementById('card-case-normal');
  const caseCardEmergency = document.getElementById('card-case-emergency');

  if (caseTypeRadios.length > 0) {
    function updateCaseSelection(value) {
      if (value === 'emergency') {
        if (emergencyDetails) {
          emergencyDetails.classList.remove('d-none');
          emergencyDetails.classList.add('animate-entrance');
        }
        if (caseCardEmergency) caseCardEmergency.classList.add('selected-emergency');
        if (caseCardNormal) caseCardNormal.classList.remove('selected-normal');
      } else {
        if (emergencyDetails) emergencyDetails.classList.add('d-none');
        if (caseCardNormal) caseCardNormal.classList.add('selected-normal');
        if (caseCardEmergency) caseCardEmergency.classList.remove('selected-emergency');
      }
    }

    caseTypeRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        if (radio.checked) {
          updateCaseSelection(radio.value);
        }
      });
    });

    if (caseCardNormal) {
      caseCardNormal.addEventListener('click', () => {
        const radio = caseCardNormal.querySelector('input[type="radio"]');
        if (radio) {
          radio.checked = true;
          updateCaseSelection('normal');
        }
      });
    }

    if (caseCardEmergency) {
      caseCardEmergency.addEventListener('click', () => {
        const radio = caseCardEmergency.querySelector('input[type="radio"]');
        if (radio) {
          radio.checked = true;
          updateCaseSelection('emergency');
        }
      });
    }
  }

  // Active Token Polling (Every 5 seconds)
  const tokenElement = document.getElementById('active-token-data');
  if (tokenElement) {
    const tokenId = tokenElement.dataset.tokenId;
    let previousStatus = tokenElement.dataset.status;

    const pollTokenStatus = async () => {
      try {
        const response = await fetch(`/api/patient/token-status/${tokenId}`);
        if (!response.ok) return;
        const data = await response.json();

        if (data.status === 'success' && data.token) {
          const currentStatus = data.token.status;

          // 1. Detect transition to 'called'
          if (previousStatus === 'waiting' && currentStatus === 'called') {
            window.hospitalChime.playCallChime();
            if ('vibrate' in navigator) {
              navigator.vibrate([300, 150, 300, 150, 400]);
            }
            showCalledAlert(data.token.token_number, data.token.department_name);
          }
          previousStatus = currentStatus;

          // 2. Update position and wait time in DOM
          const posEl = document.getElementById('live-position-val');
          const waitEl = document.getElementById('live-wait-val');
          const statusBadge = document.getElementById('live-status-badge');

          if (posEl) {
            if (data.queue_position !== null) {
              if (data.queue_position === 0) {
                posEl.innerHTML = '<span class="text-success"><i class="bi bi-bell-fill"></i> Your Turn</span>';
              } else if (data.queue_position === 1) {
                posEl.innerHTML = '<span class="text-primary font-weight-bold">Next in Line!</span>';
              } else {
                posEl.innerText = `#${data.queue_position} in line`;
              }
            } else {
              posEl.innerText = currentStatus.toUpperCase();
            }
          }

          if (waitEl) {
            if (data.estimated_wait !== null) {
              waitEl.innerText = `~${data.estimated_wait} mins`;
            } else {
              waitEl.innerText = 'Now';
            }
          }

          // 3. Update Stepper visuals
          updateStepper(currentStatus);

          // 4. If completed or cancelled, prompt reload after a short delay
          if (currentStatus === 'completed' || currentStatus === 'cancelled') {
            setTimeout(() => {
              window.location.reload();
            }, 3000);
          }
        }
      } catch (err) {
        console.warn("Status polling error:", err);
      }
    };

    // Run poll every 5000ms
    setInterval(pollTokenStatus, 5000);
  }
});

function updateStepper(status) {
  const stepWaiting = document.getElementById('step-waiting');
  const stepCalled = document.getElementById('step-called');
  const stepConsulting = document.getElementById('step-consulting');
  const stepCompleted = document.getElementById('step-completed');

  if (!stepWaiting) return;

  // Reset classes
  [stepWaiting, stepCalled, stepConsulting, stepCompleted].forEach(s => {
    if (s) {
      s.classList.remove('active', 'completed', 'called-step');
    }
  });

  if (status === 'waiting') {
    stepWaiting.classList.add('active');
  } else if (status === 'called') {
    stepWaiting.classList.add('completed');
    stepCalled.classList.add('active', 'called-step');
  } else if (status === 'in_consultation') {
    stepWaiting.classList.add('completed');
    stepCalled.classList.add('completed');
    stepConsulting.classList.add('active');
  } else if (status === 'completed') {
    stepWaiting.classList.add('completed');
    stepCalled.classList.add('completed');
    stepConsulting.classList.add('completed');
    stepCompleted.classList.add('completed');
  }
}

function showCalledAlert(tokenNum, deptName) {
  // Remove any existing call modal
  document.querySelectorAll('.call-modal-overlay').forEach(m => m.remove());

  const overlay = document.createElement('div');
  overlay.className = 'call-modal-overlay';
  overlay.style.cssText = `
    position: fixed; inset: 0; z-index: 9999;
    background: rgba(0,0,0,0.72);
    display: flex; align-items: center; justify-content: center;
    animation: fadeInScale 0.4s cubic-bezier(0.34,1.56,0.64,1) both;
  `;

  overlay.innerHTML = `
    <div class="call-modal-content text-center" style="
      background: linear-gradient(145deg,#fff,#fff5f5);
      border-radius: 28px;
      padding: clamp(1.8rem, 5vw, 3rem) clamp(1.2rem, 4vw, 2.5rem);
      max-width: 440px;
      width: 92%;
      box-shadow: 0 40px 80px rgba(239,68,68,0.3), 0 0 0 2px rgba(239,68,68,0.25);
      border-top: 6px solid #ef4444;
      position: relative;
      overflow: hidden;
    ">
      <!-- Pulse ring behind bell -->
      <div class="mb-4" style="position:relative;display:inline-block;">
        <div style="
          position:absolute;inset:-12px;border-radius:50%;
          background:rgba(239,68,68,0.1);
          animation: pulseGlowRed 1.5s ease-in-out infinite;
        "></div>
        <div style="
          width:70px;height:70px;border-radius:50%;
          background:linear-gradient(135deg,#ef4444,#dc2626);
          display:flex;align-items:center;justify-content:center;
          box-shadow:0 8px 24px rgba(239,68,68,0.5);
          animation: heartbeat 1.8s ease-in-out infinite;
        ">
          <i class="bi bi-bell-fill text-white" style="font-size:1.8rem;"></i>
        </div>
      </div>

      <h2 class="fw-bolder text-danger mb-1" style="font-family:'Outfit',sans-serif;font-size:clamp(1.5rem, 4.5vw, 2rem);">
        It's Your Turn!
      </h2>
      <p class="text-muted mb-2 small">Please proceed immediately to</p>

      <div style="
        font-family:'Outfit',sans-serif;
        font-size:clamp(2.3rem, 9vw, 3.8rem);font-weight:900;line-height:1.05;
        background:linear-gradient(135deg,#dc2626,#ea580c);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
        letter-spacing:-0.04em;margin-bottom:0.75rem;
        animation: heartbeat 1.8s ease-in-out infinite;
      ">${tokenNum}</div>

      <div class="mb-4">
        <span style="
          display:inline-block;
          background:linear-gradient(135deg,#fef2f2,#fff);
          border:1.5px solid #fca5a5;
          border-radius:12px;
          padding:0.45rem 1rem;
          font-weight:700;color:#dc2626;
          font-size:1rem;
        ">
          <i class="bi bi-geo-alt-fill me-1"></i> ${deptName}
        </span>
      </div>

      <button
        onclick="this.closest('.call-modal-overlay').style.animation='none';this.closest('.call-modal-overlay').style.opacity='0';this.closest('.call-modal-overlay').style.transition='opacity 0.3s ease';setTimeout(()=>this.closest('.call-modal-overlay').remove(),300);"
        style="
          background:linear-gradient(135deg,#ef4444,#dc2626);
          color:#fff;border:none;border-radius:50px;
          padding:0.8rem 2rem;font-size:1rem;font-weight:700;
          box-shadow:0 8px 24px rgba(239,68,68,0.4);
          cursor:pointer;transition:all 0.2s ease;
          font-family:'Plus Jakarta Sans',sans-serif;
          width:100%;max-width:280px;
        "
        onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 12px 30px rgba(239,68,68,0.5)'"
        onmouseout="this.style.transform='';this.style.boxShadow='0 8px 24px rgba(239,68,68,0.4)'"
      >
        <i class="bi bi-arrow-right-circle-fill me-2"></i> I'm on My Way!
      </button>
    </div>
  `;

  document.body.appendChild(overlay);

  // Auto-dismiss after 30 seconds
  setTimeout(() => {
    if (overlay.parentNode) {
      overlay.style.opacity = '0';
      overlay.style.transition = 'opacity 0.5s ease';
      setTimeout(() => overlay.remove(), 500);
    }
  }, 30000);
}

