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
    <div class="gallery-item rounded-xl shadow-md bg-white" onclick="openLightbox(${idx})">
      <div class="aspect-square overflow-hidden rounded-xl">
        <img src="${item.image_url}" alt="${item.title}"
             class="w-full h-full object-cover"
             onerror="this.src='https://via.placeholder.com/400x400/FDF2F4/EBB838?text=BCA'">
      </div>
      <div class="p-3">
        <p class="font-semibold text-gray-800 text-sm truncate">${item.title}</p>
        <span class="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">${item.category}</span>
      </div>
    </div>
  `).join('');
}

function openLightbox(idx) {
  const item = galleryState.items[idx];
  if (!item) return;
  const lb = document.getElementById('lightbox');
  document.getElementById('lb-img').src = item.image_url;
  document.getElementById('lb-title').textContent = item.title;
  document.getElementById('lb-category').textContent = item.category;
  lb.classList.remove('hidden');
  lb.dataset.current = idx;
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
  if (donateBtn && khqrModal) {
    donateBtn.addEventListener('click', () => khqrModal.classList.remove('hidden'));
    closeKhqr?.addEventListener('click', () => khqrModal.classList.add('hidden'));
    khqrModal.addEventListener('click', (e) => { if (e.target === khqrModal) khqrModal.classList.add('hidden'); });
  }

  // Mobile nav toggle
  const navToggle = document.getElementById('nav-toggle');
  const mobileMenu = document.getElementById('mobile-menu');
  if (navToggle && mobileMenu) {
    navToggle.addEventListener('click', () => mobileMenu.classList.toggle('hidden'));
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

  // Smooth progress bars
  document.querySelectorAll('.progress-fill').forEach(bar => {
    const target = bar.dataset.width || '0';
    setTimeout(() => { bar.style.width = target + '%'; }, 300);
  });
});

// ── KHQR Modal (also callable from nav) ───────────────────────────────────
function openDonateModal() {
  document.getElementById('khqr-modal')?.classList.remove('hidden');
}
