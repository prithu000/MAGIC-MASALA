/**
 * Magic Masala — Premium Scroll-Driven Product Assembly
 * v3.0 — Clean, robust, no clipping, works on mobile + desktop
 *
 * Architecture:
 *  - JS places each jar at an absolute pixel position (top/left) derived from
 *    the viewport centre — guaranteeing they stay inside the screen.
 *  - During scroll, JS only drives `transform` (translate + scale + rotate).
 *    No top/left changes after init.
 *  - Uses rAF + lerp for butter-smooth 60 fps / 120 fps motion.
 */
(function () {
  'use strict';

  /* ─────────────────────────────────────────
     0. GUARD: prefers-reduced-motion
  ───────────────────────────────────────── */
  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ─────────────────────────────────────────
     1. DOM REFS
  ───────────────────────────────────────── */
  var section      = document.getElementById('magic-assembly-section');
  if (!section) return;

  var viewport     = section.querySelector('.magic-assembly-viewport');
  var header       = document.getElementById('assembly-header');
  var boxAnchor    = document.getElementById('assembly-box-anchor');
  var finalHero    = document.getElementById('assembly-final-hero');
  var progressFill = document.getElementById('assembly-progress-fill');
  var progressStep = document.getElementById('assembly-progress-step');
  var jarItems     = Array.from(section.querySelectorAll('.assembly-jar-item'));

  if (prefersReduced) {
    section.classList.add('is-reduced-motion');
    return;
  }

  /* ─────────────────────────────────────────
     2. JAR LAYOUT TABLE (11 JARS: 10 Masalas + 1 Hing)
     Positions are (dx, dy) as % of viewport half-width / half-height
     from the viewport centre, plus an initial rotation in degrees.
     Values are chosen so all jars stay well within the visible area.
  ───────────────────────────────────────── */
  var JAR_LAYOUT = [
    // dx%, dy%, rot
    [-42, -26, -13],  // 0  Haldi (top left)
    [-25,  24,  10],  // 1  Dhaniya (bottom mid-left)
    [-45,   4,  -8],  // 2  Lal Mirch (far left)
    [-18, -32,  12],  // 3  Kashmiri Mirch (top left-center)
    [ -5,  28,  -6],  // 4  Jeera (bottom center)
    [  7, -28,   9],  // 5  Kasoori Methi (top right-center)
    [ 23,  25, -10],  // 6  Chana Masala (bottom mid-right)
    [ 24, -18,   8],  // 7  Amchur (top mid-right)
    [ 40,   6,  -6],  // 8  Chaat Masala (far right)
    [ 35, -24,  11],  // 9  Saunf (top far-right)
    [ 42,  22,  14],  // 10 Hing (FREE BONUS, bottom far-right)
  ];

  /* ─────────────────────────────────────────
     3. SIZING — updated on resize
  ───────────────────────────────────────── */
  var vw, vh, jarW, jarH, cx, cy;

  function computeSizes() {
    vw  = viewport.clientWidth;
    vh  = viewport.clientHeight;
    cx  = vw / 2;
    cy  = vh / 2;

    var isMobile = vw < 600;
    var isTablet = vw >= 600 && vw < 1024;
    // Real jar aspect ratio is 1:2.55
    jarW = isMobile ? 38 : (isTablet ? 60 : 82);
    jarH = Math.round(jarW * 2.55);
  }

  /* ─────────────────────────────────────────
     4. INIT — place jars at their spread positions
  ───────────────────────────────────────── */
  function initJars() {
    computeSizes();
    var isMobile = vw < 600;

    jarItems.forEach(function (jar, i) {
      var layout = JAR_LAYOUT[i] || [0, 0, 0];
      var halfW  = vw / 2;
      var halfH  = vh / 2;

      // Scale spread on mobile so jars stay elegantly inside viewport
      var spreadScaleX = isMobile ? 0.88 : 1;
      var spreadScaleY = isMobile ? 0.82 : 1;
      var dx = (layout[0] / 100) * halfW * spreadScaleX;
      var dy = (layout[1] / 100) * halfH * spreadScaleY;
      var rot = layout[2];

      // Store for use in animation
      jar._ox  = dx;          // origin x (px from centre)
      jar._oy  = dy;          // origin y (px from centre)
      jar._rot = rot;         // initial rotation

      // Place absolutely relative to viewport centre
      jar.style.width  = jarW + 'px';
      jar.style.height = jarH + 'px';
      jar.style.top    = (cy - jarH / 2) + 'px';
      jar.style.left   = (cx - jarW / 2) + 'px';

      // Start at spread position
      jar.style.transform = buildJarTransform(dx, dy, 1, rot);
      jar.style.opacity   = '1';
    });
  }

  function buildJarTransform(tx, ty, scale, rotate) {
    return (
      'translate3d(' + tx.toFixed(1) + 'px,' + ty.toFixed(1) + 'px,0)' +
      ' scale(' + scale.toFixed(4) + ')' +
      ' rotate(' + rotate.toFixed(2) + 'deg)'
    );
  }

  /* ─────────────────────────────────────────
     5. EASING UTILS
  ───────────────────────────────────────── */
  function easeOutQuad(t) { return t * (2 - t); }
  function easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1;
  }
  function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function remap(v, inA, inB, outA, outB) {
    return clamp01((v - inA) / (inB - inA)) * (outB - outA) + outA;
  }

  /* ─────────────────────────────────────────
     6. SCROLL PROGRESS CALCULATION
  ───────────────────────────────────────── */
  var currentP = 0;
  var targetP  = 0;
  var rafId    = null;

  function getScrollProgress() {
    var rect = section.getBoundingClientRect();
    var scrollable = section.offsetHeight - vh;
    if (scrollable <= 0) return 0;
    var scrolled = -rect.top;
    return Math.max(0, Math.min(1, scrolled / scrollable));
  }

  function onScroll() {
    targetP = getScrollProgress();
    if (!rafId) rafId = requestAnimationFrame(tick);
  }

  /* ─────────────────────────────────────────
     7. RENDER LOOP
  ───────────────────────────────────────── */
  function tick() {
    rafId = null;

    // Smooth lerp — feels premium
    currentP += (targetP - currentP) * 0.10;
    if (Math.abs(targetP - currentP) < 0.0005) currentP = targetP;

    render(currentP);

    if (Math.abs(targetP - currentP) > 0.0005) {
      rafId = requestAnimationFrame(tick);
    }
  }

  function render(p) {
    var isMobile = vw < 600;

    /* ── Header: fade out between 0 → 0.20 ── */
    if (header) {
      var hFade  = clamp01(1 - p / 0.18);
      var hScale = 1 + p * 0.15;
      var hY     = -p * 70;
      header.style.opacity   = hFade.toFixed(3);
      header.style.transform = 'translate3d(0,' + hY.toFixed(1) + 'px,0) scale(' + hScale.toFixed(3) + ')';
      header.style.pointerEvents = hFade > 0.05 ? '' : 'none';
    }

    /* ── Combo Box: emerges 0.25 → 0.82, fades out 0.82 → 0.92 ── */
    if (boxAnchor) {
      if (p < 0.22) {
        boxAnchor.style.opacity   = '0';
        boxAnchor.style.transform = 'translate(-50%,-50%) scale(0.65) rotate(-4deg)';
        boxAnchor.style.pointerEvents = 'none';
      } else if (p < 0.82) {
        var bp = easeOutQuad(remap(p, 0.22, 0.60, 0, 1));
        var bS = 0.65 + 0.35 * bp;
        var bO = Math.min(1, bp * 1.8);
        var bR = -4 * (1 - bp);
        var bY = 28 * (1 - bp);
        boxAnchor.style.opacity   = bO.toFixed(3);
        boxAnchor.style.transform = 'translate(-50%,calc(-50% + ' + bY.toFixed(1) + 'px)) scale(' + bS.toFixed(3) + ') rotate(' + bR.toFixed(2) + 'deg)';
        boxAnchor.style.pointerEvents = 'auto';
      } else {
        var fade = clamp01(1 - (p - 0.82) / 0.10);
        boxAnchor.style.opacity   = fade.toFixed(3);
        boxAnchor.style.pointerEvents = 'none';
      }
    }

    /* ── Jars: staggered flight 0.12 → 0.80 ── */
    var count = jarItems.length;
    jarItems.forEach(function (jar, i) {
      var ox  = jar._ox;
      var oy  = jar._oy;
      var rot = jar._rot;

      // Stagger timing
      var frac       = i / count;
      var flightStart = 0.12 + frac * 0.14;
      var flightEnd   = 0.56 + frac * 0.10;
      var sinkStart   = 0.58 + frac * 0.09;
      var sinkEnd     = 0.78 + frac * 0.07;

      var label = jar.querySelector('.jar-floating-label');

      if (p <= flightStart) {
        // Floating at origin
        jar.style.opacity   = '1';
        jar.style.transform = buildJarTransform(ox, oy, 1.0, rot);
        if (label) label.style.opacity = '1';

      } else if (p < sinkStart) {
        // Flying toward centre
        var ft    = easeInOutCubic(clamp01((p - flightStart) / (flightEnd - flightStart)));
        var tx    = lerp(ox, 0, ft);
        var ty    = lerp(oy, 0, ft);
        var tr    = rot * (1 - ft);
        var ts    = lerp(1.0, isMobile ? 0.72 : 0.80, ft);
        jar.style.opacity   = '1';
        jar.style.transform = buildJarTransform(tx, ty, ts, tr);
        if (label) label.style.opacity = (1 - ft * 2).toFixed(2);

      } else if (p < sinkEnd) {
        // Sinking into box
        var st    = easeOutQuad(clamp01((p - sinkStart) / (sinkEnd - sinkStart)));
        var ty2   = st * jarH * 0.4;
        var ts2   = lerp(isMobile ? 0.72 : 0.80, 0.52, st);
        var op    = Math.max(0, 1 - st * 1.25);
        jar.style.opacity   = op.toFixed(3);
        jar.style.transform = buildJarTransform(0, ty2, ts2, 0);
        if (label) label.style.opacity = '0';

      } else {
        // Inside box — hidden
        jar.style.opacity   = '0';
        jar.style.transform = buildJarTransform(0, jarH * 0.5, 0.5, 0);
        if (label) label.style.opacity = '0';
      }
    });

    /* ── Final Hero: reveals 0.80 → 1.00 ── */
    if (finalHero) {
      if (p >= 0.76) {
        var hp  = easeOutQuad(clamp01((p - 0.76) / 0.22));
        var hS  = 0.92 + 0.08 * hp;
        var hY2 = 32 * (1 - hp);
        finalHero.style.opacity   = hp.toFixed(3);
        finalHero.style.transform = 'translate(-50%,calc(-50% + ' + hY2.toFixed(1) + 'px)) scale(' + hS.toFixed(3) + ')';
        finalHero.style.pointerEvents = hp > 0.5 ? 'auto' : 'none';
      } else {
        finalHero.style.opacity   = '0';
        finalHero.style.transform = 'translate(-50%,calc(-50% + 32px)) scale(0.92)';
        finalHero.style.pointerEvents = 'none';
      }
    }

    /* ── Progress Bar ── */
    if (progressFill) {
      progressFill.style.width = (p * 100).toFixed(1) + '%';
    }
    if (progressStep) {
      if (p < 0.20)      progressStep.textContent = 'Taaza Stone-Ground Masale';
      else if (p < 0.55) progressStep.textContent = 'Aapki rasoi ke liye taaza...';
      else if (p < 0.78) progressStep.textContent = 'Custom combo packing...';
      else               progressStep.textContent = 'Aapka Masala Box Ready!';
    }
  }

  /* ─────────────────────────────────────────
     8. RESIZE HANDLER
  ───────────────────────────────────────── */
  function onResize() {
    computeSizes();
    var isMobile = vw < 600;
    var halfW = vw / 2;
    var halfH = vh / 2;
    var spreadScaleX = isMobile ? 0.88 : 1;
    var spreadScaleY = isMobile ? 0.82 : 1;

    // Re-place jars at their absolute positions, keeping spread transforms
    jarItems.forEach(function (jar) {
      jar.style.width  = jarW + 'px';
      jar.style.height = jarH + 'px';
      jar.style.top    = (cy - jarH / 2) + 'px';
      jar.style.left   = (cx - jarW / 2) + 'px';
    });
    // Re-calc origin vectors based on new viewport
    jarItems.forEach(function (jar, i) {
      var layout = JAR_LAYOUT[i] || [0, 0, 0];
      jar._ox = (layout[0] / 100) * halfW * spreadScaleX;
      jar._oy = (layout[1] / 100) * halfH * spreadScaleY;
    });
    // Force a re-render at the current progress
    render(currentP);
  }

  /* ─────────────────────────────────────────
     9. BOOTSTRAP
  ───────────────────────────────────────── */
  function init() {
    initJars();
    // Initial render at p=0
    render(0);

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onResize, { passive: true });

    // Interactive button trigger for smooth motion on click/tap
    var scrollBtn = document.getElementById('assembly-scroll-trigger');
    if (scrollBtn) {
      scrollBtn.addEventListener('click', function (e) {
        e.preventDefault();
        var scrollable = section.offsetHeight - vh;
        var targetY = section.offsetTop + scrollable * 0.90;
        window.scrollTo({ top: targetY, behavior: 'smooth' });
      });
    }

    // Handle case where page loads mid-scroll
    onScroll();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
