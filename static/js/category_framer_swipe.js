/**
 * Framer-Motion Category Swipe Engine
 * Smooth inertia dragging, gesture tracking, momentum glide, progress indicator, and button controls.
 */
document.addEventListener('DOMContentLoaded', () => {
  const track = document.getElementById('cat-carousel-track');
  const viewport = document.getElementById('cat-carousel-viewport');
  const prevBtn = document.getElementById('cat-nav-prev');
  const nextBtn = document.getElementById('cat-nav-next');
  const progressBar = document.getElementById('cat-progress-bar');
  const progressTrack = document.getElementById('cat-progress-track');

  if (!track) return;

  const cards = track.querySelectorAll('.category-framer-card');
  if (cards.length === 0) return;

  // State variables
  let isDown = false;
  let startX = 0;
  let scrollLeftStart = 0;
  let isDragging = false;
  let lastX = 0;
  let lastTime = 0;
  let velocity = 0;
  let momentumAnimId = null;

  // ── 1. Progress Bar Update ──
  const updateProgress = () => {
    const maxScroll = track.scrollWidth - track.clientWidth;
    if (maxScroll <= 0) {
      if (prevBtn) prevBtn.disabled = true;
      if (nextBtn) nextBtn.disabled = true;
      if (progressBar) progressBar.style.width = '100%';
      return;
    }

    const scrollRatio = Math.max(0, Math.min(1, track.scrollLeft / maxScroll));

    if (prevBtn) prevBtn.disabled = track.scrollLeft <= 5;
    if (nextBtn) nextBtn.disabled = track.scrollLeft >= maxScroll - 5;

    if (progressBar && progressTrack) {
      const trackWidth = progressTrack.clientWidth;
      const barWidth = Math.max(35, trackWidth * (track.clientWidth / track.scrollWidth));
      const maxTranslate = trackWidth - barWidth;
      const translate = scrollRatio * maxTranslate;

      progressBar.style.width = `${barWidth}px`;
      progressBar.style.transform = `translateX(${translate}px)`;
    }
  };

  track.addEventListener('scroll', () => {
    requestAnimationFrame(updateProgress);
  }, { passive: true });

  window.addEventListener('resize', () => {
    requestAnimationFrame(updateProgress);
  }, { passive: true });

  // Initial call
  setTimeout(updateProgress, 100);

  // ── 2. Card Scroll Helper ──
  const getCardWidth = () => {
    const firstCard = cards[0];
    if (!firstCard) return 320;
    const style = window.getComputedStyle(track);
    const gap = parseFloat(style.columnGap || style.gap || '20') || 20;
    return firstCard.offsetWidth + gap;
  };

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      cancelMomentum();
      const step = getCardWidth();
      track.scrollBy({ left: -step, behavior: 'smooth' });
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      cancelMomentum();
      const step = getCardWidth();
      track.scrollBy({ left: step, behavior: 'smooth' });
    });
  }

  // ── 3. Momentum Decay Animation ──
  const cancelMomentum = () => {
    if (momentumAnimId) {
      cancelAnimationFrame(momentumAnimId);
      momentumAnimId = null;
    }
  };

  const applyMomentum = (initialVelocity) => {
    let currentVel = initialVelocity * 16; // scale to frame delta
    const friction = 0.94; // fluid framer friction

    const step = () => {
      if (Math.abs(currentVel) < 0.5) {
        cancelMomentum();
        return;
      }
      track.scrollLeft -= currentVel;
      currentVel *= friction;
      momentumAnimId = requestAnimationFrame(step);
    };
    momentumAnimId = requestAnimationFrame(step);
  };

  // ── 4. Pointer Drag & Click Reliability (Mouse pad / Touch / Trackpad) ──
  let hasMoved = false;
  let isSwiping = false;

  track.addEventListener('pointerdown', (e) => {
    // Only primary button
    if (e.button !== 0) return;
    
    cancelMomentum();
    isDown = true;
    hasMoved = false;
    isSwiping = false;
    startX = e.pageX;
    scrollLeftStart = track.scrollLeft;
    lastX = e.pageX;
    lastTime = performance.now();
    velocity = 0;
  });

  track.addEventListener('pointermove', (e) => {
    if (!isDown) return;

    const currentX = e.pageX;
    const dx = currentX - startX;

    // Only initiate drag mode if user intentionally moved more than 12 pixels
    if (Math.abs(dx) > 12) {
      if (!isSwiping) {
        isSwiping = true;
        hasMoved = true;
        track.classList.add('is-dragging');
        try {
          track.setPointerCapture(e.pointerId);
        } catch (err) {}
      }

      track.scrollLeft = scrollLeftStart - dx;
      
      const currentTime = performance.now();
      const dt = Math.max(1, currentTime - lastTime);
      const instantDelta = currentX - lastX;
      velocity = instantDelta / dt;

      lastX = currentX;
      lastTime = currentTime;
    }
  });

  const handlePointerEnd = (e) => {
    if (!isDown) return;
    isDown = false;
    track.classList.remove('is-dragging');

    try {
      if (track.hasPointerCapture(e.pointerId)) {
        track.releasePointerCapture(e.pointerId);
      }
    } catch (err) {}

    if (isSwiping) {
      if (Math.abs(velocity) > 0.15) {
        applyMomentum(velocity);
      }
      // Keep isSwiping true for a tiny frame to swallow the immediate synthetic click, then reset
      setTimeout(() => {
        isSwiping = false;
        hasMoved = false;
      }, 50);
    } else {
      isSwiping = false;
      hasMoved = false;
    }
  };

  track.addEventListener('pointerup', handlePointerEnd);
  track.addEventListener('pointercancel', handlePointerEnd);

  // Card click handler: allow normal navigation on click/tap, only suppress if user swiped
  cards.forEach(card => {
    card.addEventListener('click', (e) => {
      if (isSwiping || hasMoved) {
        e.preventDefault();
        e.stopPropagation();
        return false;
      }
      // Clean click on mouse pad / trackpad -> let default browser link navigation proceed!
    });
  });

  // ── 5. Keyboard Navigation ──
  track.setAttribute('tabindex', '0');
  track.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      track.scrollBy({ left: -getCardWidth(), behavior: 'smooth' });
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      track.scrollBy({ left: getCardWidth(), behavior: 'smooth' });
    }
  });
});
