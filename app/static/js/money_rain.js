/**
 * SIF PyME - Easter Egg "Lluvia de la Fortuna" (Money Rain)
 * Animación fluida en Canvas nativo 60fps con simulación de billetes 3D
 * y sintetizador Web Audio "Cha-Ching" (zero external dependencies).
 */
(function() {
  'use strict';

  // Sintetizador nativo Web Audio: sonido "Cha-Ching" de caja registradora
  function playChaChing() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      if (ctx.state === 'suspended') {
        ctx.resume().catch(() => {});
      }

      const now = ctx.currentTime;

      // Tono 1: Moneda / campanilla inicial (B5 ~987.77 Hz)
      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();
      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(987.77, now);
      gain1.gain.setValueAtTime(0.12, now);
      gain1.gain.exponentialRampToValueAtTime(0.0001, now + 0.28);
      osc1.connect(gain1);
      gain1.connect(ctx.destination);
      osc1.start(now);
      osc1.stop(now + 0.3);

      // Tono 2: Timbre brillante secundario (E6 ~1318.51 Hz) con ligero delay
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(1318.51, now + 0.08);
      gain2.gain.setValueAtTime(0.14, now + 0.08);
      gain2.gain.exponentialRampToValueAtTime(0.0001, now + 0.45);
      osc2.connect(gain2);
      gain2.connect(ctx.destination);
      osc2.start(now + 0.08);
      osc2.stop(now + 0.46);

      // Tono 3: Armónico agudo brillante (B6 ~1975.53 Hz)
      const osc3 = ctx.createOscillator();
      const gain3 = ctx.createGain();
      osc3.type = 'triangle';
      osc3.frequency.setValueAtTime(1975.53, now + 0.12);
      gain3.gain.setValueAtTime(0.08, now + 0.12);
      gain3.gain.exponentialRampToValueAtTime(0.0001, now + 0.35);
      osc3.connect(gain3);
      gain3.connect(ctx.destination);
      osc3.start(now + 0.12);
      osc3.stop(now + 0.36);
    } catch (_) {
      // Si el navegador bloquea audio o el sistema carece de tarjeta de sonido, silenciar limpiamente
    }
  }

  // Dibujar un billete individual estilizado en un canvas temporal precacheado para máximo rendimiento
  function createBillTexture(tipo) {
    const is500 = tipo === '500';
    const w = 110;
    const h = 56;
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');

    // Paleta cromática: 500€ morado / 100€ verde esmeralda
    const bgGradient = ctx.createLinearGradient(0, 0, w, h);
    if (is500) {
      bgGradient.addColorStop(0, '#78489A');
      bgGradient.addColorStop(0.5, '#9A66BD');
      bgGradient.addColorStop(1, '#663985');
    } else {
      bgGradient.addColorStop(0, '#1E6F38');
      bgGradient.addColorStop(0.5, '#2D8E4B');
      bgGradient.addColorStop(1, '#175429');
    }

    // Fondo redondeado del billete
    ctx.fillStyle = bgGradient;
    ctx.beginPath();
    ctx.roundRect(0, 0, w, h, 4);
    ctx.fill();

    // Borde exterior sutil
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = is500 ? 'rgba(235, 205, 255, 0.5)' : 'rgba(185, 245, 200, 0.5)';
    ctx.stroke();

    // Marco interior decorativo
    ctx.lineWidth = 1;
    ctx.strokeStyle = is500 ? 'rgba(255, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.25)';
    ctx.strokeRect(4, 4, w - 8, h - 8);

    // Banda holográfica vertical en el lado derecho
    const holo = ctx.createLinearGradient(w - 22, 0, w - 8, 0);
    holo.addColorStop(0, 'rgba(255, 255, 255, 0.1)');
    holo.addColorStop(0.5, 'rgba(255, 240, 180, 0.45)');
    holo.addColorStop(1, 'rgba(255, 255, 255, 0.15)');
    ctx.fillStyle = holo;
    ctx.fillRect(w - 20, 4, 12, h - 8);

    // Tipografía del valor
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(is500 ? '500 €' : '100 €', 8, 20);

    // Marca de agua central "SIF PyME"
    ctx.font = '600 9px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.55)';
    ctx.textAlign = 'center';
    ctx.fillText('★ SIF PyME ★', (w - 20) / 2, h / 2 + 3);

    // Valor en esquina inferior derecha
    ctx.font = 'bold 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.textAlign = 'right';
    ctx.fillStyle = '#FFFFFF';
    ctx.fillText(is500 ? '500' : '100', w - 24, h - 9);

    return canvas;
  }

  // Pre-renderizar las texturas de 500€ y 100€
  let texture500 = null;
  let texture100 = null;
  function getTextures() {
    if (!texture500) texture500 = createBillTexture('500');
    if (!texture100) texture100 = createBillTexture('100');
    return { texture500, texture100 };
  }

  /**
   * Dispara el efecto de lluvia de billetes sobre la pantalla completa
   * @param {Object} [options]
   * @param {number} [options.count=55] Cantidad de billetes
   * @param {number} [options.duration=4200] Duración en milisegundos
   * @param {boolean} [options.sound=true] Si debe reproducir el sonido sintetizado
   */
  function triggerMoneyRain(options = {}) {
    const count = options.count || 55;
    const duration = options.duration || 4200;
    const enableSound = options.sound !== false;

    if (enableSound) {
      playChaChing();
    }

    const { texture500, texture100 } = getTextures();

    // Crear canvas overlay de pantalla completa
    const canvas = document.createElement('canvas');
    canvas.id = 'sif-money-rain-overlay';
    canvas.style.position = 'fixed';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.width = '100vw';
    canvas.style.height = '100vh';
    canvas.style.pointerEvents = 'none';
    canvas.style.zIndex = '999999';
    document.body.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    // Generar partículas (billetes)
    const particles = [];
    for (let i = 0; i < count; i++) {
      const is500 = Math.random() < 0.7; // 70% billetes morados de 500€, 30% verdes de 100€
      particles.push({
        texture: is500 ? texture500 : texture100,
        x: Math.random() * width,
        y: -120 - Math.random() * (height * 0.9), // escalonados arriba
        vx: (Math.random() - 0.5) * 1.6,
        vy: 2.2 + Math.random() * 3.2,
        scale: 0.65 + Math.random() * 0.55,
        rotation: Math.random() * Math.PI * 2,
        vRot: (Math.random() - 0.5) * 0.04,
        flip: Math.random() * Math.PI * 2,
        vFlip: 0.03 + Math.random() * 0.05,
        windPhase: Math.random() * Math.PI * 2,
        windSpeed: 0.02 + Math.random() * 0.03,
      });
    }

    const startTime = performance.now();
    let animId = null;

    function render(now) {
      const elapsed = now - startTime;
      if (elapsed >= duration) {
        // Limpieza final y destrucción
        window.removeEventListener('resize', handleResize);
        if (canvas.parentNode) {
          canvas.parentNode.removeChild(canvas);
        }
        return;
      }

      // Desvanecimiento suave en los últimos 800ms
      let alpha = 1.0;
      const remaining = duration - elapsed;
      if (remaining < 800) {
        alpha = Math.max(0, remaining / 800);
      }

      ctx.clearRect(0, 0, width, height);
      ctx.globalAlpha = alpha;

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // Física
        p.windPhase += p.windSpeed;
        p.x += p.vx + Math.sin(p.windPhase) * 1.2;
        p.y += p.vy;
        p.rotation += p.vRot;
        p.flip += p.vFlip;

        // Si sobrepasa el fondo, reubicarlo si aún queda más de 1.5s de lluvia
        if (p.y > height + 80 && remaining > 1500) {
          p.y = -80;
          p.x = Math.random() * width;
        }

        const flipScale = Math.cos(p.flip); // Simulación de volteo 3D de cara/cruz
        const bw = p.texture.width * p.scale;
        const bh = p.texture.height * p.scale * Math.abs(flipScale);

        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rotation);

        // Ligera sombra dinámica
        ctx.shadowColor = 'rgba(0, 0, 0, 0.18)';
        ctx.shadowBlur = 8;
        ctx.shadowOffsetY = 4;

        ctx.drawImage(
          p.texture,
          -bw / 2,
          -bh / 2,
          bw,
          Math.max(2, bh)
        );

        ctx.restore();
      }

      animId = requestAnimationFrame(render);
    }

    animId = requestAnimationFrame(render);
  }

  // Exportar al objeto global window
  window.triggerMoneyRain = triggerMoneyRain;
  window.playChaChing = playChaChing;
})();

