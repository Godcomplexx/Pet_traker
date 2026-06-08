(function () {
  'use strict';

  const api = window.api;
  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  let pet = null;
  let catalog = {};
  let busy = false;
  let observer = null;
  let syncTimer = null;
  let tracking = false;

  function accessoryIcon(item) {
    const file = item?.data?.file || item?.data;
    return typeof file === 'string' && file ? `assets/accessories/${file}` : '';
  }

  function equippedAccessory() {
    const itemId = pet?.equipped?.accessory;
    const item = itemId ? catalog[itemId] : null;
    return item?.type === 'accessory' ? item : null;
  }

  function decorateCard(card, item) {
    const preview = qs('.swatch-prev', card);
    const src = accessoryIcon(item);
    if (!preview || !src || preview.dataset.accessoryPreview === item.id) return;

    const img = document.createElement('img');
    img.className = 'accessory-icon';
    img.src = src;
    img.alt = item.name || '';

    preview.className = 'swatch-prev accessory-prev';
    preview.dataset.accessoryPreview = item.id;
    preview.replaceChildren(img);
  }

  function decorateCards() {
    qsa('[data-shop], [data-inventory]').forEach((card) => {
      const itemId = card.dataset.shop || card.dataset.inventory;
      const item = itemId ? catalog[itemId] : null;
      if (item?.type === 'accessory') decorateCard(card, item);
    });
  }

  function positionAccessory(screen, node, item) {
    const petNode = qs('.pixelpet', screen);
    if (!petNode) return;

    const screenBox = screen.getBoundingClientRect();
    const petBox = petNode.getBoundingClientRect();
    if (!screenBox.width || !petBox.width) return;

    const data = item.data || {};
    const scale = Number(data.scale || 0.5);
    const anchorX = Number(data.anchor_x || 0.5);
    const anchorY = Number(data.anchor_y || 0.46);
    const offsetX = Number(data.offset_x || 0);
    const offsetY = Number(data.offset_y || 0);
    const width = Math.max(20, petBox.width * scale);
    const left = petBox.left - screenBox.left + petBox.width * anchorX + offsetX;
    const top = petBox.top - screenBox.top + petBox.height * anchorY + offsetY;

    node.style.width = `${Math.round(width)}px`;
    node.style.height = `${Math.round(width)}px`;
    node.style.left = `${Math.round(left)}px`;
    node.style.top = `${Math.round(top)}px`;
  }

  function renderAccessories() {
    const item = equippedAccessory();
    qsa('.petscreen').forEach((screen) => {
      qsa('.pet-accessory', screen).forEach((node) => node.remove());
      if (!item || !qs('.pixelpet', screen)) return;

      const node = document.createElement('div');
      node.className = 'pet-accessory';
      node.dataset.petAccessory = item.id;
      node.title = item.name || '';

      const img = document.createElement('img');
      img.className = 'pet-accessory-img';
      img.src = accessoryIcon(item);
      img.alt = item.name || '';
      node.appendChild(img);
      screen.appendChild(node);
      positionAccessory(screen, node, item);
    });
    trackAccessoryPosition();
  }

  function trackAccessoryPosition() {
    if (tracking) return;
    tracking = true;
    requestAnimationFrame(function tick() {
      const item = equippedAccessory();
      let active = false;
      qsa('.pet-accessory').forEach((node) => {
        const screen = node.closest('.petscreen');
        if (!screen || !item || !document.body.contains(node)) return;
        active = true;
        positionAccessory(screen, node, item);
      });
      if (active) {
        requestAnimationFrame(tick);
      } else {
        tracking = false;
      }
    });
  }

  function render() {
    if (busy) return;
    busy = true;
    observer?.disconnect();
    try {
      decorateCards();
      renderAccessories();
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
      render();
    } catch {
      // The base app owns visible auth and network errors.
    }
  }

  function scheduleSync(delay = 120) {
    clearTimeout(syncTimer);
    syncTimer = setTimeout(sync, delay);
  }

  function observe() {
    if (!observer) {
      observer = new MutationObserver(() => {
        if (!busy) scheduleSync();
      });
    }
    qsa('.petscreen, #shopGrid, #inventoryGrid, #dockBackpack').forEach((root) => {
      observer.observe(root, { childList: true, subtree: true });
    });
  }

  document.addEventListener('click', (event) => {
    if (event.target.closest('[data-shop], [data-inventory], [data-dock-bag-page]')) {
      scheduleSync(450);
    }
  });
  window.addEventListener('resize', () => render());
  window.addEventListener('storage', () => scheduleSync());
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) scheduleSync();
  });
  observe();
  scheduleSync(450);
})();
