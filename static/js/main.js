/* BCA Main Frontend JS */

// ── Gallery Filter & Lightbox ──────────────────────────────────────────────

const galleryState = { category: 'All', items: [] };

async function loadGallery(category = 'All') {
  galleryState.category = category;
  const url = category === 'All' ? '/api/gallery' : `/api/gallery?category=${encodeURIComponent(category)}`;
  try {
    const res = await fetch(url);
    const items = await res.json();
    galleryState.items = items;
    renderGallery(items);
  } catch (e) {
    console.error('Gallery load error', e);
  }
}

function renderGallery(items) {
  const grid = document.getElementById('gallery-grid');
  if (!grid) return;
  if (items.length === 0) {
    grid.innerHTML = '<p class="col-span-full text-center text-gray-400 py-12">No photos in this category yet.</p>';
    return;
  }
  grid.innerHTML = items.map((item, idx) => `
    <article class="gallery-item rounded-xl shadow-md bg-white" onclick="openLightbox(${idx})">
      <div class="aspect-video overflow-hidden rounded-xl">
        <img src="${escapeHtml(item.image_url)}" alt="${escapeHtml(item.title)}"
             class="w-full h-full object-cover"
             onerror="this.src='https://via.placeholder.com/400x400/FDF2F4/EBB838?text=BCA'">
      </div>
      <div class="p-3">
        <p class="text-xs text-gray-500 mb-1">${formatGalleryDate(item.created_at)}</p>
        <h3 class="font-semibold text-gray-800 text-sm">${escapeHtml(item.title)}</h3>
        <p class="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full inline-block mt-1">${escapeHtml(item.category)}</p>
        ${item.description ? `<p class="text-sm text-gray-700 mt-2 line-clamp-3">${escapeHtml(item.description)}</p>` : ''}
        <button type="button" class="text-sm font-semibold text-gray-800 mt-3 hover:underline"
                onclick="event.stopPropagation(); openLightbox(${idx})">Read More →</button>
      </div>
    </article>
  `).join('');
}

function escapeHtml(value) {
  return String(value || '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[char]);
}

function formatGalleryDate(value) {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
}

function openLightbox(idx) {
  const item = galleryState.items[idx];
  if (!item) return;
  const lb = document.getElementById('lightbox');
  document.getElementById('lb-img').src = item.image_url;
  document.getElementById('lb-img').alt = item.title;
  document.getElementById('lb-date').textContent = formatGalleryDate(item.created_at);
  document.getElementById('lb-title').textContent = item.title;
  document.getElementById('lb-category').textContent = item.category;
  document.getElementById('lb-description').textContent = item.description || '';
  lb.classList.remove('hidden');
  lb.dataset.current = idx;
}

async function openGalleryItem(id) {
  let idx = galleryState.items.findIndex((item) => item.id === id);
  if (idx === -1) {
    await loadGallery('All');
    idx = galleryState.items.findIndex((item) => item.id === id);
  }
  if (idx !== -1) openLightbox(idx);
}

async function openRecentActivityItem(id) {
  try {
    const response = await fetch('/api/recent-activities');
    if (!response.ok) return;
    const activities = await response.json();
    galleryState.items = activities;
    const idx = activities.findIndex((item) => item.id === id);
    if (idx !== -1) openLightbox(idx);
  } catch (error) {
    console.error('Recent activity load error', error);
  }
}

function closeLightbox() {
  document.getElementById('lightbox').classList.add('hidden');
}

function lightboxNav(dir) {
  const lb = document.getElementById('lightbox');
  let idx = parseInt(lb.dataset.current || 0) + dir;
  const len = galleryState.items.length;
  idx = (idx + len) % len;
  openLightbox(idx);
}

// Close lightbox on backdrop click
document.addEventListener('DOMContentLoaded', () => {
  const navLinks = [...document.querySelectorAll('.nav-reference-link')];
  const setActiveNavLink = (targetLink) => {
    navLinks.forEach((item) => {
      const isActive = item === targetLink;
      item.classList.toggle('active', isActive);
      item.style.setProperty('color', isActive ? '#f47783' : '#111', 'important');
    });
  };
  navLinks.forEach((link) => {
    link.addEventListener('click', () => setActiveNavLink(link));
  });
  window.addEventListener('hashchange', () => {
    const targetLink = navLinks.find((link) => link.getAttribute('href') === window.location.hash);
    if (targetLink) setActiveNavLink(targetLink);
  });
  const initialNavLink = navLinks.find((link) => link.getAttribute('href') === window.location.hash);
  if (initialNavLink) setActiveNavLink(initialNavLink);

  document.querySelectorAll('[data-current-year]').forEach((el) => {
    el.textContent = new Date().getFullYear();
  });

  const heroSlides = [...document.querySelectorAll('#hero-slideshow .hero-slide')];
  const heroDots = [...document.querySelectorAll('.hero-dot')];
  if (heroSlides.length > 1) {
    let activeSlide = 0;
    let timer;
    const showSlide = (index) => {
      activeSlide = (index + heroSlides.length) % heroSlides.length;
      heroSlides.forEach((slide, i) => slide.classList.toggle('is-active', i === activeSlide));
      heroDots.forEach((dot, i) => {
        dot.classList.toggle('is-active', i === activeSlide);
        dot.setAttribute('aria-selected', i === activeSlide ? 'true' : 'false');
      });
    };
    const restartTimer = () => {
      clearInterval(timer);
      timer = setInterval(() => showSlide(activeSlide + 1), 6000);
    };
    document.querySelector('.hero-arrow-prev')?.addEventListener('click', () => {
      showSlide(activeSlide - 1);
      restartTimer();
    });
    document.querySelector('.hero-arrow-next')?.addEventListener('click', () => {
      showSlide(activeSlide + 1);
      restartTimer();
    });
    heroDots.forEach((dot, i) => dot.addEventListener('click', () => {
      showSlide(i);
      restartTimer();
    }));
    restartTimer();
  }

  const joinModal = document.getElementById('join-modal');
  const joinForm = document.getElementById('join-form');
  if (joinModal) {
    joinModal.addEventListener('click', (e) => {
      if (e.target === joinModal) closeJoinModal();
    });
  }
  joinForm?.addEventListener('submit', (e) => {
    e.preventDefault();
    joinForm.reset();
    closeJoinModal();
  });

  const lb = document.getElementById('lightbox');
  if (lb) {
    lb.addEventListener('click', (e) => { if (e.target === lb) closeLightbox(); });
  }

  // Keyboard nav
  document.addEventListener('keydown', (e) => {
    if (!lb || lb.classList.contains('hidden')) return;
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowRight') lightboxNav(1);
    if (e.key === 'ArrowLeft') lightboxNav(-1);
  });

  // Gallery filter buttons
  document.querySelectorAll('[data-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-filter]').forEach(b => {
        b.classList.remove('bg-amber-500', 'text-white');
        b.classList.add('bg-white', 'text-gray-700');
      });
      btn.classList.add('bg-amber-500', 'text-white');
      btn.classList.remove('bg-white', 'text-gray-700');
      loadGallery(btn.dataset.filter);
    });
  });

  // Initial gallery load
  if (document.getElementById('gallery-grid')) {
    loadGallery();
  }

  // KHQR Modal
  const donateBtn = document.getElementById('donate-btn');
  const khqrModal = document.getElementById('khqr-modal');
  const closeKhqr = document.getElementById('close-khqr');
  const donationForm = document.getElementById('donation-form');
  const showDonationForm = document.getElementById('show-donation-form');
  if (donateBtn && khqrModal) {
    donateBtn.addEventListener('click', () => openDonateModal());
    closeKhqr?.addEventListener('click', () => closeDonateModal());
    khqrModal.addEventListener('click', (e) => { if (e.target === khqrModal) closeDonateModal(); });
  }
  showDonationForm?.addEventListener('click', () => {
    showDonationForm.classList.add('hidden');
    donationForm?.classList.remove('hidden');
  });
  donationForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = document.getElementById('donation-message');
    const submitButton = donationForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = 'Saving...';
    message.classList.add('hidden');
    try {
      const response = await fetch('/api/donations', {
        method: 'POST',
        body: new FormData(donationForm),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Unable to save donation.');
      message.textContent = '✓ Your name and receipt were sent to admin.';
      message.className = 'text-center text-sm text-green-600';
      donationForm.reset();
      submitButton.classList.add('hidden');
    } catch (error) {
      message.textContent = error.message;
      message.className = 'text-center text-sm text-red-600';
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = 'Save Donation';
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeDonateModal();
      closeLightbox();
    }
  });

  // Mobile nav toggle
  const navToggle = document.getElementById('nav-toggle');
  const mobileMenu = document.getElementById('mobile-menu');
  if (navToggle && mobileMenu) {
    const setMenuOpen = (isOpen) => {
      navToggle.setAttribute('aria-expanded', String(isOpen));
      navToggle.setAttribute('aria-label', isOpen ? 'Close navigation menu' : 'Open navigation menu');
      mobileMenu.classList.toggle('hidden', !isOpen);
    };

    navToggle.addEventListener('click', () => {
      setMenuOpen(navToggle.getAttribute('aria-expanded') !== 'true');
    });
    mobileMenu.querySelectorAll('a, button').forEach((item) => {
      item.addEventListener('click', () => setMenuOpen(false));
    });
  }

  // Animate stats on scroll
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('stat-card');
      }
    });
  }, { threshold: 0.2 });
  document.querySelectorAll('.stat-item').forEach(el => observer.observe(el));

});

// ── KHQR Modal (also callable from nav) ───────────────────────────────────
function openDonateModal() {
  document.getElementById('khqr-modal')?.classList.remove('hidden');
}

function closeDonateModal() {
  document.getElementById('khqr-modal')?.classList.add('hidden');
  document.getElementById('donation-form')?.classList.add('hidden');
  document.getElementById('show-donation-form')?.classList.remove('hidden');
}

function openJoinModal() {
  document.getElementById('join-modal')?.classList.remove('hidden');
}

function closeJoinModal() {
  document.getElementById('join-modal')?.classList.add('hidden');
}
