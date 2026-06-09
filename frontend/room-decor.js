(function () {
  'use strict';

  const api = window.api;
  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const TABLE_DEFAULT_POSITION = { x: 50, y: 72 };
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

  function tableStorageKey() {
    return `petpro_room_table_position:${pet?.id || 'default'}`;
  }

  function readTablePosition() {
    try {
      const raw = localStorage.getItem(tableStorageKey());
      const saved = raw ? JSON.parse(raw) : null;
      const x = Number(saved?.x);
      const y = Number(saved?.y);
      if (Number.isFinite(x) && Number.isFinite(y)) {
        return { x: clamp(x, 18, 82), y: clamp(y, 62, 86) };
      }
    } catch {
      // Invalid saved room furniture state should not break the pet screen.
    }
    return { ...TABLE_DEFAULT_POSITION };
  }

  function saveTablePosition(position) {
    try {
      localStorage.setItem(tableStorageKey(), JSON.stringify(position));
    } catch {
      // Dragging still works for the current session if storage is unavailable.
    }
  }

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

  function tablePointerPosition(event, screen) {
    const position = pointerPosition(event, screen);
    return {
      x: clamp(position.x, 18, 82),
      y: clamp(position.y, 62, 86),
    };
  }

  function isPlantDecor(item) {
    const data = item?.data || {};
    const file = String(data.file || data.icon || item?.id || '').toLowerCase();
    const name = String(item?.name || '').toLowerCase();
    return /(^|[/_-])(plant|flower)|flower|plant/.test(`${file} ${name}`);
  }

  function tableSurfacePosition() {
    const table = readTablePosition();
    return { x: table.x, y: table.y - 11 };
  }

  function isOnTableSurface(item, position) {
    if (!isPlantDecor(item) || !position) return false;
    const table = readTablePosition();
    const surface = tableSurfacePosition();
    return (
      Math.abs(position.x - table.x) <= 25
      && position.y >= surface.y - 8
      && position.y <= table.y + 8
    );
  }

  function snapToTableSurface(item, position) {
    if (!isOnTableSurface(item, position)) return position;
    const table = readTablePosition();
    const surface = tableSurfacePosition();
    return {
      x: clamp(position.x, table.x - 20, table.x + 20),
      y: surface.y,
    };
  }

  function applyTablePosition(screen, position) {
    screen.style.setProperty('--room-table-x', `${position.x}%`);
    screen.style.setProperty('--room-table-y', `${position.y}%`);
    const table = screen.querySelector('.pet-room-table');
    if (table) {
      table.style.setProperty('--room-table-x', `${position.x}%`);
      table.style.setProperty('--room-table-y', `${position.y}%`);
    }
  }

  function ensureRoomTable(screen) {
    let table = screen.querySelector('.pet-room-table');
    if (table) return table;
    table = document.createElement('div');
    table.className = 'pet-room-table';
    table.dataset.roomTable = '1';
    table.title = 'Table';
    const img = document.createElement('img');
    img.src = 'assets/decor/wooden_table.png';
    img.alt = 'Table';
    table.appendChild(img);
    screen.appendChild(table);
    return table;
  }

  function applyFreePosition(node, position, item) {
    node.classList.add('decor-free');
    node.classList.remove('decor-floor-left', 'decor-floor-right', 'decor-shelf-left', 'decor-shelf-right');
    node.classList.toggle('decor-on-table', isOnTableSurface(item, position));
    node.style.setProperty('--decor-x', `${position.x}%`);
    node.style.setProperty('--decor-y', `${position.y}%`);
  }

  function renderRoom() {
    if (!pet) return;
    qsa('.pet-room-screen').forEach((screen) => {
      qsa('.pet-decor', screen).forEach((node) => node.remove());
      ensureRoomTable(screen);
      applyTablePosition(screen, readTablePosition());
      const decor = equippedDecor();
      screen.classList.toggle('room-has-light', decor.some(({ item }) => item.data?.kind === 'light'));
      decor.forEach(({ id, item, slot, position }) => {
        const node = document.createElement('div');
        node.className = `pet-decor ${item.data?.kind === 'light' ? 'decor-light' : ''}`;
        node.dataset.roomDecorOverlay = '1';
        node.dataset.roomDecorId = id;
        node.title = item.name || '';
        if (position) {
          applyFreePosition(node, position, item);
        } else {
          node.classList.add(`decor-${slot}`);
          node.classList.toggle('decor-on-table', slot.startsWith('shelf-') && isPlantDecor(item));
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
    const table = event.target.closest('.pet-room-screen .pet-room-table');
    if (table) {
      const screen = table.closest('.pet-room-screen');
      if (!screen) return;
      event.preventDefault();
      event.stopPropagation();
      drag = {
        type: 'table',
        node: table,
        screen,
        pointerId: event.pointerId,
        position: tablePointerPosition(event, screen),
      };
      table.classList.add('is-dragging');
      table.setPointerCapture?.(event.pointerId);
      applyTablePosition(screen, drag.position);
      return;
    }

    const node = event.target.closest('.pet-room-screen .pet-decor[data-room-decor-id]');
    if (!node || !api?.isAuthed?.()) return;
    const screen = node.closest('.pet-room-screen');
    if (!screen) return;
    event.preventDefault();
    event.stopPropagation();
    drag = {
      type: 'decor',
      itemId: node.dataset.roomDecorId,
      item: catalog[node.dataset.roomDecorId],
      node,
      screen,
      pointerId: event.pointerId,
      position: pointerPosition(event, screen),
    };
    node.classList.add('is-dragging');
    node.setPointerCapture?.(event.pointerId);
    applyFreePosition(node, drag.position, drag.item);
  }, true);

  document.addEventListener('pointermove', (event) => {
    if (!drag || event.pointerId !== drag.pointerId) return;
    event.preventDefault();
    if (drag.type === 'table') {
      drag.position = tablePointerPosition(event, drag.screen);
      qsa('.pet-room-screen').forEach((screen) => applyTablePosition(screen, drag.position));
      return;
    }
    drag.position = pointerPosition(event, drag.screen);
    applyFreePosition(drag.node, drag.position, drag.item);
  }, true);

  document.addEventListener('pointerup', async (event) => {
    if (!drag || event.pointerId !== drag.pointerId) return;
    event.preventDefault();
    const finished = drag;
    drag = null;
    finished.node.classList.remove('is-dragging');
    if (finished.type === 'table') {
      saveTablePosition(finished.position);
      paint();
      return;
    }
    try {
      finished.position = snapToTableSurface(finished.item, finished.position);
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
    if (drag.type === 'table') {
      qsa('.pet-room-screen').forEach((screen) => applyTablePosition(screen, readTablePosition()));
    }
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
