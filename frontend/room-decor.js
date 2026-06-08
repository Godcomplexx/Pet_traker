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
  let drag = null;

  function equippedDecor() {
    const equipped = pet?.equipped || {};
    const raw = equipped.decor;
    const ids = Array.isArray(raw) ? raw : raw ? [raw] : [];
    const slots = equipped.decor_slots && typeof equipped.decor_slots === 'object'
      ? equipped.decor_slots
      : {};
    const positions = equipped.decor_positions && typeof equipped.decor_positions === 'object'
      ? equipped.decor_positions
      : {};
    return ids
      .map((id) => {
        const item = catalog[id];
        if (!item || item.type !== 'decor') return null;
        const slot = slots[id] || item.data?.slot || 'floor-right';
        const savedPosition = positions[id];
        const x = Number(savedPosition?.x);
        const y = Number(savedPosition?.y);
        const position = Number.isFinite(x) && Number.isFinite(y) ? { x, y } : null;
        return { id, item, slot, position };
      })
      .filter(Boolean);
  }

  function decorIcon(item) {
    const data = item.data || {};
    if (data.file) return `assets/decor/${data.file}`;
    return `assets/decor/${data.icon || item.id}.png`;
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function pointerPosition(event, screen) {
    const box = screen.getBoundingClientRect();
    return {
      x: clamp(((event.clientX - box.left) / box.width) * 100, 3, 97),
      y: clamp(((event.clientY - box.top) / box.height) * 100, 4, 96),
    };
  }

  function applyFreePosition(node, position) {
    node.classList.add('decor-free');
    node.classList.remove('decor-floor-left', 'decor-floor-right', 'decor-shelf-left', 'decor-shelf-right');
    node.style.setProperty('--decor-x', `${position.x}%`);
    node.style.setProperty('--decor-y', `${position.y}%`);
  }

  function renderRoom() {
    if (!pet) return;
    qsa('.pet-room-screen').forEach((screen) => {
      qsa('.pet-decor', screen).forEach((node) => node.remove());
      const decor = equippedDecor();
      screen.classList.toggle('room-has-light', decor.some(({ item }) => item.data?.kind === 'light'));
      decor.forEach(({ id, item, slot, position }) => {
        const node = document.createElement('div');
        node.className = `pet-decor ${item.data?.kind === 'light' ? 'decor-light' : ''}`;
        node.dataset.roomDecorOverlay = '1';
        node.dataset.roomDecorId = id;
        node.title = item.name || '';
        if (position) {
          applyFreePosition(node, position);
        } else {
          node.classList.add(`decor-${slot}`);
        }

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
    Object.entries(SLOTS).forEach(([slot, label]) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.roomSlot = slot;
      button.textContent = label;
      button.classList.toggle('on', placed?.slot === slot);
      wrap.appendChild(button);
    });
    if (placed) {
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'danger';
      remove.dataset.roomRemove = '1';
      remove.textContent = 'Снять';
      wrap.appendChild(remove);
    }
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
      if (!drag) renderRoom();
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

  async function saveDecorPosition(itemId, position) {
    pet = await api.post('/shop/decor-position', {
      item_id: itemId,
      x: position.x,
      y: position.y,
    });
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

  document.addEventListener('pointerdown', (event) => {
    const node = event.target.closest('.pet-room-screen .pet-decor[data-room-decor-id]');
    if (!node || !api?.isAuthed?.()) return;
    const screen = node.closest('.pet-room-screen');
    if (!screen) return;
    event.preventDefault();
    event.stopPropagation();
    drag = {
      itemId: node.dataset.roomDecorId,
      node,
      screen,
      pointerId: event.pointerId,
      position: pointerPosition(event, screen),
    };
    node.classList.add('is-dragging');
    node.setPointerCapture?.(event.pointerId);
    applyFreePosition(node, drag.position);
  }, true);

  document.addEventListener('pointermove', (event) => {
    if (!drag || event.pointerId !== drag.pointerId) return;
    event.preventDefault();
    drag.position = pointerPosition(event, drag.screen);
    applyFreePosition(drag.node, drag.position);
  }, true);

  document.addEventListener('pointerup', async (event) => {
    if (!drag || event.pointerId !== drag.pointerId) return;
    event.preventDefault();
    const finished = drag;
    drag = null;
    finished.node.classList.remove('is-dragging');
    try {
      await saveDecorPosition(finished.itemId, finished.position);
    } catch (err) {
      const msg = qs('#playMsg');
      if (msg) msg.textContent = err.message || 'Не удалось сохранить положение предмета.';
      scheduleSync();
    }
  }, true);

  document.addEventListener('pointercancel', (event) => {
    if (!drag || event.pointerId !== drag.pointerId) return;
    drag.node.classList.remove('is-dragging');
    drag = null;
    scheduleSync();
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
