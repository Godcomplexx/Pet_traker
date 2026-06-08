(function () {
  'use strict';

  const api = window.api;
  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const SLOTS = {
    'floor-left': 'Пол слева',
    'floor-right': 'Пол справа',
    'shelf-left': 'Полка слева',
    'shelf-right': 'Полка справа',
  };

  let pet = null;
  let catalog = {};
  let busy = false;
  let observer = null;
  let syncTimer = null;

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"]/g, (ch) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
    }[ch]));
  }

  function equippedDecor() {
    const equipped = pet?.equipped || {};
    const raw = equipped.decor;
    const ids = Array.isArray(raw) ? raw : raw ? [raw] : [];
    const slots = equipped.decor_slots && typeof equipped.decor_slots === 'object'
      ? equipped.decor_slots
      : {};
    return ids
      .map((id) => {
        const item = catalog[id];
        if (!item || item.type !== 'decor') return null;
        const slot = slots[id] || item.data?.slot || 'floor-right';
        return { id, item, slot };
      })
      .filter(Boolean);
  }

  function decorIcon(item) {
    const data = item.data || {};
    if (data.file) return `assets/decor/${data.file}`;
    return `assets/decor/${data.icon || item.id}.png`;
  }

  function renderRoom() {
    if (!pet) return;
    qsa('.pet-room-screen').forEach((screen) => {
      qsa('.pet-decor', screen).forEach((node) => node.remove());
      const decor = equippedDecor();
      screen.classList.toggle('room-has-light', decor.some(({ item }) => item.data?.kind === 'light'));
      decor.forEach(({ item, slot }) => {
        const node = document.createElement('div');
        node.className = `pet-decor decor-${slot} ${item.data?.kind === 'light' ? 'decor-light' : ''}`;
        node.dataset.roomDecorOverlay = '1';
        node.title = item.name || '';

        const img = document.createElement('img');
        img.className = 'pet-decor-img';
        img.src = decorIcon(item);
        img.alt = item.name || '';
        node.appendChild(img);
        screen.appendChild(node);
      });
    });
  }

  function renderSlotButtons(card, item) {
    const placed = equippedDecor().find(({ id }) => id === item.id);
    const wrap = document.createElement('div');
    wrap.className = 'decor-slot-actions';
    wrap.dataset.roomItem = item.id;
    wrap.innerHTML = Object.entries(SLOTS).map(([slot, label]) => (
      `<button class="${placed?.slot === slot ? 'on' : ''}" type="button" data-room-slot="${slot}">${escapeHtml(label)}</button>`
    )).join('') + (placed
      ? '<button class="danger" type="button" data-room-remove="1">Снять</button>'
      : '');
    card.appendChild(wrap);
  }

  function decorateInventory() {
    qsa('#inventoryGrid [data-inventory]').forEach((card) => {
      const item = catalog[card.dataset.inventory];
      if (!item || item.type !== 'decor') return;
      card.classList.add('room-decor-card');
      card.querySelector('.decor-slot-actions')?.remove();
      renderSlotButtons(card, item);
    });
  }

  function paint() {
    if (busy) return;
    busy = true;
    observer?.disconnect();
    try {
      renderRoom();
      decorateInventory();
    } finally {
      busy = false;
      observe();
    }
  }

  async function sync() {
    if (!api?.isAuthed?.()) return;
    try {
      const [nextPet, shop] = await Promise.all([
        api.get('/pets/me'),
        Object.keys(catalog).length ? Promise.resolve(null) : api.get('/shop/items'),
      ]);
      pet = nextPet;
      if (shop?.items) catalog = Object.fromEntries(shop.items.map((item) => [item.id, item]));
      paint();
    } catch {
      // The app already owns global auth/error handling; this enhancer stays quiet.
    }
  }

  function scheduleSync(delay = 120) {
    clearTimeout(syncTimer);
    syncTimer = setTimeout(sync, delay);
  }

  async function placeDecor(itemId, slot) {
    if (!itemId) return;
    const body = slot ? { item_id: itemId, slot } : { item_id: itemId };
    pet = await api.post('/shop/equip', body);
    paint();
  }

  document.addEventListener('click', async (event) => {
    const action = event.target.closest('[data-room-slot], [data-room-remove]');
    if (!action) return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    const itemId = action.closest('[data-room-item]')?.dataset.roomItem
      || action.closest('[data-inventory]')?.dataset.inventory;
    try {
      await placeDecor(itemId, action.dataset.roomSlot || '');
    } catch (err) {
      const msg = qs('#playMsg');
      if (msg) msg.textContent = err.message || 'Не удалось переставить предмет.';
    }
  }, true);

  document.addEventListener('click', (event) => {
    if (event.target.closest('[data-room-slot], [data-room-remove]')) return;
    if (event.target.closest('[data-inventory]')) scheduleSync(350);
    if (event.target.closest('[data-shop], #openCase')) scheduleSync(500);
  });

  function observe() {
    if (!observer) {
      observer = new MutationObserver(() => {
        if (!busy) scheduleSync();
      });
    }
    qsa('.pet-room-screen, #inventoryGrid').forEach((root) => {
      observer.observe(root, { childList: true, subtree: true });
    });
  }

  window.addEventListener('storage', () => scheduleSync());
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) scheduleSync();
  });
  observe();
  scheduleSync(400);
})();
