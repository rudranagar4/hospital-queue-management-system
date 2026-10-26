/**
 * Hospital Smart Queue Management System
 * ─────────────────────────────────────────────────────────────────────────────
 * Global Utilities: Scroll Reveal, Particle Canvas, Tilt Cards, Ripple,
 * Navbar Shrink, Magnetic Buttons, Counter Animation, Hospital Chime
 */

/* ============================================================
   WEB AUDIO — HOSPITAL CHIME SYNTHESIZER
   ============================================================ */
class HospitalChime {
  constructor() { this.audioCtx = null; }

  _init() {
    if (!this.audioCtx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) this.audioCtx = new AC();
    }
  }

  _playNote(freq, startOffset, duration, vol = 0.26) {
    try {
      const now = this.audioCtx.currentTime + startOffset;
      const osc  = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, now);
      gain.gain.setValueAtTime(0, now);
      gain.gain.linearRampToValueAtTime(vol, now + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.001, now + duration);
      osc.connect(gain);
      gain.connect(this.audioCtx.destination);
      osc.start(now);
      osc.stop(now + duration + 0.05);
    } catch (e) { /* silent fail */ }
  }

  playCallChime() {
    try {
      this._init();
      if (!this.audioCtx) return;
      if (this.audioCtx.state === 'suspended') this.audioCtx.resume();
      // Ascending chime: E5 → G5 → C6
      this._playNote(659.25, 0.00, 0.80, 0.25);
      this._playNote(784.00, 0.28, 0.80, 0.28);
      this._playNote(1046.5, 0.56, 1.20, 0.22);
    } catch (e) { console.warn('Chime error:', e); }
  }

  playEmergencyAlert() {
    try {
      this._init();
      if (!this.audioCtx) return;
      if (this.audioCtx.state === 'suspended') this.audioCtx.resume();
      // Urgent two-tone beep
      this._playNote(880.0, 0.00, 0.25, 0.35);
      this._playNote(660.0, 0.30, 0.25, 0.35);
      this._playNote(880.0, 0.60, 0.25, 0.35);
    } catch (e) { console.warn('Alert error:', e); }
  }
}

window.hospitalChime = new HospitalChime();


/* ============================================================
   SCROLL-REVEAL — INTERSECTION OBSERVER
   ============================================================ */
function initScrollReveal() {
  const elements = document.querySelectorAll('.reveal');
  if (!elements.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        // Stagger each revealed card by 80ms
        const delay = parseFloat(entry.target.dataset.revealDelay || 0) * 1000;
        setTimeout(() => {
          entry.target.classList.add('revealed');
        }, delay);
        observer.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.12,
    rootMargin: '0px 0px -40px 0px'
  });

  elements.forEach((el, i) => {
    // Auto-assign stagger if not set manually
    if (!el.dataset.revealDelay) {
      el.dataset.revealDelay = (i % 4) * 0.1; // reset each row of 4
    }
    observer.observe(el);
  });
}


/* ============================================================
   ANIMATED PARTICLE CANVAS BACKGROUND
   ============================================================ */
function initParticleCanvas() {
  const canvas = document.getElementById('particles-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let particles = [];
  let animFrameId;

  const isAdmin = document.body.classList.contains('admin-theme');
  const particleColor = isAdmin
    ? 'rgba(16, 185, 129, 0.5)'
    : 'rgba(37, 99, 235, 0.4)';
  const lineColor = isAdmin
    ? 'rgba(16, 185, 129, 0.12)'
    : 'rgba(37, 99, 235, 0.08)';

  function resize() {
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  function createParticle() {
    return {
      x:  Math.random() * canvas.width,
      y:  Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      r:  Math.random() * 2.2 + 0.6,
      alpha: Math.random() * 0.6 + 0.2
    };
  }

  function initParticles(count) {
    const defaultCount = window.innerWidth < 768 ? 24 : 65;
    particles = Array.from({ length: count || defaultCount }, createParticle);
  }

  function drawParticles() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw connecting lines between nearby particles
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx*dx + dy*dy);
        if (dist < 120) {
          ctx.beginPath();
          ctx.strokeStyle = lineColor;
          ctx.globalAlpha = (1 - dist / 120) * 0.5;
          ctx.lineWidth = 0.8;
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.stroke();
        }
      }
    }

    // Draw particles
    particles.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = particleColor;
      ctx.globalAlpha = p.alpha;
      ctx.fill();

      // Move
      p.x += p.vx;
      p.y += p.vy;

      // Bounce edges
      if (p.x < 0 || p.x > canvas.width)  p.vx *= -1;
      if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
    });

    ctx.globalAlpha = 1;
    animFrameId = requestAnimationFrame(drawParticles);
  }

  resize();
  initParticles();
  drawParticles();

  const resizeObserver = new ResizeObserver(() => {
    resize();
    initParticles();
  });
  resizeObserver.observe(document.body);

  // Pause when tab is hidden for performance
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      cancelAnimationFrame(animFrameId);
    } else {
      drawParticles();
    }
  });
}


/* ============================================================
   NAVBAR SCROLL SHRINK
   ============================================================ */
function initNavbarShrink() {
  const navbar = document.querySelector('.navbar');
  if (!navbar) return;

  let lastScroll = 0;
  window.addEventListener('scroll', () => {
    const scrollY = window.scrollY;
    if (scrollY > 40) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
    lastScroll = scrollY;
  }, { passive: true });
}


/* ============================================================
   3D TILT CARD EFFECT (mouse-over)
   ============================================================ */
function initTiltCards() {
  const cards = document.querySelectorAll('.tilt-card');
  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect   = card.getBoundingClientRect();
      const cx     = rect.left + rect.width / 2;
      const cy     = rect.top  + rect.height / 2;
      const dx     = (e.clientX - cx) / (rect.width  / 2);
      const dy     = (e.clientY - cy) / (rect.height / 2);
      const tiltX  = dy * -6;   // max 6 degrees
      const tiltY  = dx *  6;
      card.style.transform = `perspective(800px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) scale(1.02)`;
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
    });
  });
}


/* ============================================================
   RIPPLE CLICK EFFECT
   ============================================================ */
function initRipple() {
  document.querySelectorAll('.ripple-container, .btn-call-next, .btn-patient-primary').forEach(el => {
    el.addEventListener('click', function(e) {
      const ripple = document.createElement('span');
      ripple.classList.add('ripple-wave');
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      ripple.style.cssText = `
        width: ${size}px; height: ${size}px;
        top:  ${e.clientY - rect.top  - size / 2}px;
        left: ${e.clientX - rect.left - size / 2}px;
      `;
      this.appendChild(ripple);
      ripple.addEventListener('animationend', () => ripple.remove());
    });
  });
}


/* ============================================================
   ANIMATED COUNTER (count up from 0)
   ============================================================ */
function animateCounter(el, target, duration = 900) {
  const start     = performance.now();
  const initial   = 0;
  const isFloat   = String(target).includes('.');
  const decimals  = isFloat ? 1 : 0;

  function tick(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    // Ease-out quad
    const eased = 1 - (1 - progress) * (1 - progress);
    const current = initial + (target - initial) * eased;
    el.textContent = isFloat ? current.toFixed(decimals) : Math.floor(current);
    if (progress < 1) requestAnimationFrame(tick);
  }

  requestAnimationFrame(tick);
}

function initCounters() {
  const counters = document.querySelectorAll('[data-counter-target]');
  if (!counters.length) return;

  const obs = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !entry.target.dataset.counted) {
        entry.target.dataset.counted = 'true';
        const target = parseFloat(entry.target.dataset.counterTarget);
        animateCounter(entry.target, target);
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  counters.forEach(el => obs.observe(el));
}


/* ============================================================
   MAGNETIC BUTTON HOVER (subtle position shift)
   ============================================================ */
function initMagneticButtons() {
  document.querySelectorAll('.btn-magnetic').forEach(btn => {
    btn.addEventListener('mousemove', (e) => {
      const rect = btn.getBoundingClientRect();
      const cx   = rect.left + rect.width  / 2;
      const cy   = rect.top  + rect.height / 2;
      const dx   = (e.clientX - cx) * 0.25;
      const dy   = (e.clientY - cy) * 0.25;
      btn.style.transform = `translate(${dx}px, ${dy}px)`;
    });
    btn.addEventListener('mouseleave', () => {
      btn.style.transform = '';
    });
  });
}


/* ============================================================
   AUTO-DISMISS FLASH ALERTS (5 seconds)
   ============================================================ */
function initAlertAutoDismiss() {
  document.querySelectorAll('.alert-dismissible').forEach(alert => {
    setTimeout(() => {
      try {
        bootstrap.Alert.getOrCreateInstance(alert).close();
      } catch (e) { alert.remove(); }
    }, 5000);
  });
}


/* ============================================================
   SMOOTH HOVER LIFT for cards without .glass-card
   ============================================================ */
function initCardHoverLift() {
  document.querySelectorAll('.hover-lift').forEach(card => {
    card.style.transition = 'transform 0.35s cubic-bezier(0.16,1,0.3,1), box-shadow 0.35s ease';
    card.addEventListener('mouseenter', () => {
      card.style.transform  = 'translateY(-6px)';
      card.style.boxShadow  = '0 20px 40px -8px rgba(0,0,0,0.15)';
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform  = '';
      card.style.boxShadow  = '';
    });
  });
}


/* ============================================================
   NUMBER FLIP ANIMATION — call when a displayed number changes
   ============================================================ */
window.flipNumber = function(el, newValue) {
  el.classList.remove('number-flip');
  // Force reflow
  void el.offsetWidth;
  el.textContent = newValue;
  el.classList.add('number-flip');
};


/* ============================================================
   STAGGER REVEAL for dynamically added queue rows
   ============================================================ */
window.staggerRevealItems = function(container, itemSelector, baseDelay = 60) {
  const items = container.querySelectorAll(itemSelector);
  items.forEach((item, i) => {
    item.style.opacity = '0';
    item.style.transform = 'translateX(20px)';
    setTimeout(() => {
      item.style.transition = 'opacity 0.35s ease, transform 0.35s cubic-bezier(0.16,1,0.3,1)';
      item.style.opacity = '1';
      item.style.transform = '';
    }, i * baseDelay);
  });
};


/* ============================================================
   MOBILE NAVBAR AUTO-CLOSE ON LINK CLICK
   ============================================================ */
function initMobileNavbarClose() {
  const navCollapse = document.getElementById('navbarMain');
  if (!navCollapse) return;
  const navLinks = navCollapse.querySelectorAll('.nav-link, .btn');
  navLinks.forEach(link => {
    link.addEventListener('click', () => {
      if (window.innerWidth < 992 && navCollapse.classList.contains('show')) {
        const bsCollapse = bootstrap.Collapse.getInstance(navCollapse) || new bootstrap.Collapse(navCollapse, { toggle: false });
        bsCollapse.hide();
      }
    });
  });
}

/* ============================================================
   MASTER INIT
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  initScrollReveal();
  initParticleCanvas();
  initNavbarShrink();
  initTiltCards();
  initRipple();
  initCounters();
  initMagneticButtons();
  initAlertAutoDismiss();
  initCardHoverLift();
  initMobileNavbarClose();

  // Add .animate-entrance stagger to hero section children
  document.querySelectorAll('.animate-entrance').forEach((el, i) => {
    if (!el.style.animationDelay) {
      el.style.animationDelay = `${i * 0.1}s`;
    }
  });
});
