(function () {
  'use strict';

  const api = window.api;
  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  let pet = null;
  let timer = null;

  function ensureReviveButton() {
    let button = qs('#petRevive');
    if (button) return button;

    const host = qs('#playMsg') || qs('#screen-pet .pet-actions');
    if (!host) return null;

    button = document.createElement('button');
    button.id = 'petRevive';
    button.className = 'btn primary sm pet-revive-btn';
    button.type = 'button';
    button.textContent = 'Оживить питомца';
    host.insertAdjacentElement('afterend', button);
    return button;
  }

  function applyState() {
    const isDead = pet?.is_dead || pet?.state === 'dead';
    document.body.classList.toggle('pet-life-dead', !!isDead);
    qsa('.petscreen').forEach((screen) => screen.classList.toggle('pet-dead-screen', !!isDead));
    qsa('#playPet, #playBall, #playSleep, #playFeed, #petSleep').forEach((button) => {
      button.disabled = !!isDead;
      button.classList.toggle('disabled', !!isDead);
    });

    const button = ensureReviveButton();
    if (button) button.hidden = !isDead;
    const msg = qs('#playMsg');
    if (msg && isDead) msg.textContent = pet?.state_label || 'Питомец умер. Его можно оживить.';
  }

  async function sync() {
    if (!api?.isAuthed?.()) return;
    try {
      pet = await api.get('/pets/me');
      applyState();
    } catch {
      // The main app owns visible auth and network handling.
    }
  }

  function schedule(delay = 1000) {
    clearTimeout(timer);
    timer = setTimeout(sync, delay);
  }

  document.addEventListener('click', async (event) => {
    if (event.target.closest('#petRevive')) {
      event.preventDefault();
      const button = qs('#petRevive');
      if (button) button.disabled = true;
      try {
        await api.post('/pets/me/revive', {});
        window.location.reload();
      } catch (err) {
        const msg = qs('#playMsg');
        if (msg) msg.textContent = err.message || 'Не удалось оживить питомца.';
        if (button) button.disabled = false;
      }
      return;
    }
    if (event.target.closest('#playPet, #playBall, #playSleep, #playFeed, #petSleep')) {
      schedule(500);
    }
  });

  window.addEventListener('storage', () => schedule(200));
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) schedule(200);
  });
  schedule(700);
})();
