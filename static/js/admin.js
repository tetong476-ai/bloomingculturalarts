/* BCA Admin Panel JS */

// Tab switching
function showTab(tabId) {
  document.querySelectorAll('.admin-tab').forEach(t => t.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(b => {
    b.classList.remove('bg-amber-500', 'text-white');
    b.classList.add('text-gray-600', 'hover:bg-gray-100');
  });
  const tab = document.getElementById(tabId);
  if (tab) tab.classList.remove('hidden');
  const btn = document.querySelector(`[data-tab="${tabId}"]`);
  if (btn) {
    btn.classList.add('bg-amber-500', 'text-white');
    btn.classList.remove('text-gray-600', 'hover:bg-gray-100');
  }
  localStorage.setItem('bca_admin_tab', tabId);
}

// Restore last tab
document.addEventListener('DOMContentLoaded', () => {
  const hash = window.location.hash.replace('#', '');
  const saved = hash || localStorage.getItem('bca_admin_tab') || 'tab-settings';
  showTab(saved);

  // Image preview on file input
  document.querySelectorAll('input[type="file"]').forEach(input => {
    input.addEventListener('change', function () {
      const preview = document.getElementById(this.dataset.preview);
      const file = this.files[0];
      if (preview && file) {
        const previewUrl = URL.createObjectURL(file);
        if (this.dataset.previewType === 'campaign-media') {
          setCampaignMediaPreview(
            preview,
            previewUrl,
            file.type.startsWith('video/') || /\.(mp4|webm)$/i.test(file.name)
          );
        } else {
          preview.src = previewUrl;
          preview.classList.remove('hidden');
        }
      }
    });
  });

  // Confirm delete
  document.querySelectorAll('.confirm-delete').forEach(form => {
    form.addEventListener('submit', (e) => {
      if (!confirm('Are you sure you want to delete this item? This cannot be undone.')) {
        e.preventDefault();
      }
    });
  });

  // Toggle campaign active via AJAX
  document.querySelectorAll('.toggle-active').forEach(btn => {
    btn.addEventListener('click', async function () {
      const cid = this.dataset.id;
      const res = await fetch(`/admin/campaigns/${cid}/toggle`, { method: 'POST' });
      const data = await res.json();
      this.textContent = data.is_active ? 'Active' : 'Inactive';
      this.classList.toggle('bg-green-100', data.is_active);
      this.classList.toggle('text-green-700', data.is_active);
      this.classList.toggle('bg-gray-100', !data.is_active);
      this.classList.toggle('text-gray-500', !data.is_active);
    });
  });

  // Flash auto-dismiss
  setTimeout(() => {
    document.querySelectorAll('.flash-msg').forEach(el => {
      el.style.transition = 'opacity 0.5s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 500);
    });
  }, 4000);
});

// Edit modal helpers
function openEditModal(modalId) {
  document.getElementById(modalId)?.classList.remove('hidden');
}
function closeEditModal(modalId) {
  document.getElementById(modalId)?.classList.add('hidden');
}

function setCampaignMediaPreview(preview, mediaUrl, isVideo) {
  const media = document.createElement(isVideo ? 'video' : 'img');
  media.className = 'w-full h-32 object-cover rounded-xl border';
  media.src = mediaUrl;
  if (isVideo) {
    media.controls = true;
    media.playsInline = true;
  } else {
    media.alt = 'Campaign media preview';
  }
  preview.replaceChildren(media);
  preview.classList.remove('hidden');
}

// Populate campaign edit modal
function editCampaign(id, title, description, target, raised, imageUrl, isActive) {
  const form = document.getElementById('edit-campaign-form');
  if (!form) return;
  form.action = `/admin/campaigns/${id}/edit`;
  form.querySelector('[name="title"]').value = title;
  form.querySelector('[name="description"]').value = description;
  form.querySelector('[name="target_amount"]').value = target;
  form.querySelector('[name="raised_amount"]').value = raised;
  form.querySelector('[name="image_url"]').value = imageUrl;
  const activeCheck = form.querySelector('[name="is_active"]');
  if (activeCheck) activeCheck.checked = isActive;
  const preview = document.getElementById('edit-campaign-preview');
  if (preview) {
    preview.replaceChildren();
    if (imageUrl) {
      setCampaignMediaPreview(preview, imageUrl, /\.(mp4|webm)(?:[?#].*)?$/i.test(imageUrl));
    } else {
      preview.classList.add('hidden');
    }
  }
  openEditModal('edit-campaign-modal');
}

// Populate gallery edit modal
function editGallery(button) {
  const { galleryId, galleryTitle, galleryCategory, galleryImageUrl, galleryDescription } = button.dataset;
  const form = document.getElementById('edit-gallery-form');
  if (!form) return;
  form.action = `${button.dataset.collectionPath}/${galleryId}/edit`;
  form.querySelector('[name="title"]').value = galleryTitle;
  form.querySelector('[name="description"]').value = galleryDescription || '';
  const catSelect = form.querySelector('[name="category"]');
  if (catSelect) catSelect.value = galleryCategory;
  form.querySelector('[name="image_url"]').value = galleryImageUrl;
  const preview = document.getElementById('edit-gallery-preview');
  if (preview && galleryImageUrl) { preview.src = galleryImageUrl; preview.classList.remove('hidden'); }
  openEditModal('edit-gallery-modal');
}

// Populate stat edit modal
function editStat(id, label, value, icon) {
  const form = document.getElementById('edit-stat-form');
  if (!form) return;
  form.action = `/admin/stats/${id}/edit`;
  form.querySelector('[name="label"]').value = label;
  form.querySelector('[name="value"]').value = value;
  form.querySelector('[name="icon"]').value = icon;
  openEditModal('edit-stat-modal');
}
