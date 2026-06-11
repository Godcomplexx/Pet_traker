(function () {
  'use strict';

  const api = window.api;
  const qs = (sel, root = document) => root.querySelector(sel);
  const EMOTE_DIR = 'assets/emotes/pipoya';

  const RPS = {
    rock: { label: 'Камень', short: 'К', index: 86 },
    scissors: { label: 'Ножницы', short: 'Н', index: 87 },
    paper: { label: 'Бумага', short: 'Б', index: 88 },
  };

  const PET_GROUPS = [
    group('notice', 'Внимание', 0, [0, 1, 2, 3, 4]),
    group('joy', 'Радость', 5, [5, 6, 7, 8, 14]),
    group('love', 'Симпатия', 9, [9, 10, 11, 12, 18]),
    group('state', 'Состояние', 20, [20, 25, 26, 27, 28]),
    group('face', 'Лицо', 30, [30, 31, 32, 33, 34]),
    group('power', 'Эффект', 37, [37, 38, 39, 40, 49]),
  ];

  const WALL_GROUPS = [
    group('hello', 'Реакции', 0, [0, 1, 2, 3, 4, 5]),
    group('warm', 'Добро', 8, [8, 9, 10, 11, 12, 14]),
    group('fun', 'Весело', 15, [15, 16, 17, 18, 19, 21]),
    group('mood', 'Настроение', 22, [22, 23, 24, 25, 26, 27]),
    group('faces', 'Мимика', 30, [30, 31, 32, 33, 34, 35]),
    group('energy', 'Эффекты', 37, [37, 38, 39, 40, 41, 42]),
    group('game', 'Игры', 85, [
      action('rock'),
      action('scissors'),
      action('paper'),
    ]),
  ];

  let menu = null;
  let workspaceId = null;
  let rpsPanel = null;
  let rpsTimer = null;
  let teamDecorTimer = null;

  function group(id, label, icon, entries) {
    return { id, label, icon, entries };
  }

  function action(id) {
    return { action: id };
  }

  function emotePath(index) {
    return `${EMOTE_DIR}/pipo-popupemotes${String(index).padStart(3, '0')}.png`;
  }

  function emoteImg(index, className = '') {
    const emote = document.createElement('span');
    emote.setAttribute('role', 'img');
    emote.setAttribute('aria-label', `emote ${index}`);
    emote.className = `pipoya-emote-img ${className}`.trim();
    emote.style.setProperty('--pipoya-url', `url('${emotePath(index)}')`);
    return emote;
  }

  function rpsEmoteImg(key, className = '') {
    const selected = RPS[key];
    const emote = emoteImg(selected.index, className);
    emote.setAttribute('aria-label', selected.label);
    return emote;
  }

  function closeMenu() {
    menu?.remove();
    menu = null;
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function placeMenu(x, y) {
    if (!menu) return;
    const margin = 10;
    const box = menu.getBoundingClientRect();
    menu.style.left = `${clamp(x - box.width / 2, margin, window.innerWidth - box.width - margin)}px`;
    menu.style.top = `${clamp(y - box.height / 2, margin, window.innerHeight - box.height - margin)}px`;
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"]/g, (char) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
    }[char]));
  }

  function showBurst(host, index) {
    const screen = host.closest('.petscreen, .team-pet, .team-playground') || host;
    const burst = document.createElement('div');
    burst.className = 'pet-emote burst pipoya-burst';
    burst.appendChild(emoteImg(index, 'pet-emote-img is-animated'));
    screen.appendChild(burst);
    setTimeout(() => burst.remove(), 1400);
  }

  function setPetEmote(host, index) {
    const teamPet = host.closest('.team-pet');
    const screen = teamPet || host.closest('.petscreen, .team-playground') || host;
    const removable = teamPet ? '.pet-emote' : '.pipoya-selected-emote, .pipoya-burst, .rps-burst';
    screen.querySelectorAll(removable).forEach((node) => node.remove());
    const emote = document.createElement('div');
    emote.className = 'pet-emote state-emote pipoya-selected-emote';
    emote.appendChild(emoteImg(index, 'pet-emote-img'));
    screen.appendChild(emote);
  }

  function showRpsBurst(host, key) {
    const screen = host.closest('.petscreen, .team-pet, .team-playground') || host;
    const burst = document.createElement('div');
    burst.className = 'pet-emote burst rps-burst';
    burst.appendChild(rpsEmoteImg(key, 'pet-emote-img is-animated'));
    screen.appendChild(burst);
    setTimeout(() => burst.remove(), 1400);
  }

  async function getWorkspaceId() {
    if (workspaceId) return workspaceId;
    if (!api?.isAuthed?.()) return null;
    const workspaces = await api.get('/workspaces');
    workspaceId = workspaces?.[0]?.id || null;
    return workspaceId;
  }

  async function decorateTeamPets() {
    const wsId = await getWorkspaceId();
    if (!wsId || !api?.get) return [];
    const room = await api.get(`/workspaces/${wsId}/team-room`).catch(() => ({ pets: [] }));
    const pets = room.pets || [];
    document.querySelectorAll('.team-playground .team-pet').forEach((node, index) => {
      const pet = pets[index];
      if (!pet) return;
      node.dataset.userId = pet.user_id || '';
      node.dataset.petId = pet.id || '';
      node.title = 'Правый клик: эмоции и игры';
    });
    return pets;
  }

  function scheduleTeamDecor() {
    clearTimeout(teamDecorTimer);
    teamDecorTimer = setTimeout(() => decorateTeamPets().catch(() => {}), 160);
  }

  function blobToImage(blob) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      const url = URL.createObjectURL(blob);
      img.onload = () => {
        URL.revokeObjectURL(url);
        resolve(img);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error('emote image decode failed'));
      };
      img.src = url;
    });
  }

  async function emoteDataUrl(index) {
    const response = await fetch(emotePath(index));
    if (!response.ok) throw new Error('emote asset not found');
    const img = await blobToImage(await response.blob());
    const canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 32;
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(img, 0, 0, 32, 32, 0, 0, 32, 32);
    return canvas.toDataURL('image/png');
  }

  function prependLocalWallPost(text, imageData) {
    const feed = qs('#wallFeed');
    if (!feed) return;
    const node = document.createElement('div');
    node.className = 'task wall-local-emote';
    node.innerHTML = `
      <div class="t"><b>Вы</b> - ${escapeHtml(text)}
        <div class="mono">сейчас</div>
      </div>
      <img class="wall-image pipoya-wall-image" src="${imageData}" alt="">
    `;
    feed.prepend(node);
  }

  async function postToWall(text, index) {
    const wsId = await getWorkspaceId();
    if (!wsId || !api?.post) return;
    const imageData = await emoteDataUrl(index);
    await api.post(`/workspaces/${wsId}/wall`, { text, image_data: imageData });
    prependLocalWallPost(text, imageData);
  }

  function teamPetName(target) {
    return qs('.team-name', target)?.textContent?.trim() || 'питомец';
  }

  function chooseEmote(target, index) {
    closeMenu();
    setPetEmote(target, index);
  }

  async function inviteRps(target, key) {
    const selected = RPS[key];
    if (!selected) return;
    closeMenu();
    const wsId = await getWorkspaceId();
    let opponentId = target.dataset.userId;
    if (!opponentId) {
      await decorateTeamPets();
      opponentId = target.dataset.userId;
    }
    const meId = await currentUserId();
    if (!wsId || !api?.post) {
      showRpsNotice('Стена еще не готова для игры');
      return;
    }
    if (!opponentId || (meId && String(opponentId) === String(meId))) {
      await playRpsBot(target, key);
      return;
    }
    try {
      await api.post(`/workspaces/${wsId}/rps`, {
        opponent_id: opponentId,
        choice: key,
      });
      showRpsBurst(target, key);
      showRpsNotice(`Вызов отправлен: ${teamPetName(target)}`);
      refreshRpsPanel();
    } catch (err) {
      showRpsNotice(err?.message || 'Не удалось отправить вызов');
    }
  }

  async function playRpsBot(target, key) {
    const selected = RPS[key];
    const wsId = await getWorkspaceId();
    if (!selected || !wsId || !api?.post) return;
    try {
      await api.post(`/workspaces/${wsId}/rps/bot`, { choice: key });
      showRpsBurst(target, key);
      refreshPetState();
      showRpsNotice('КНБ с ботом сыграно. Результат на стене.');
      setTimeout(() => {
        const wallIsOpen = document.querySelector('#screen-team.on');
        if (wallIsOpen) document.querySelector('[data-go="team"]')?.click();
      }, 450);
    } catch (err) {
      showRpsNotice(err?.message || 'Не удалось сыграть с ботом');
    }
  }

  async function chooseRpsResponse(challenge, key) {
    const selected = RPS[key];
    if (!selected || !challenge?.id) return;
    closeMenu();
    await api.post(`/rps/challenges/${challenge.id}/choice`, { choice: key });
    refreshPetState();
    showRpsNotice(`Вы выбрали: ${selected.label}`);
    refreshRpsPanel();
    setTimeout(() => {
      const wallIsOpen = document.querySelector('#screen-team.on');
      if (wallIsOpen) document.querySelector('[data-go="team"]')?.click();
    }, 500);
  }

  function showRpsNotice(text) {
    const toasts = qs('#toasts');
    if (!toasts) return;
    const toast = document.createElement('div');
    toast.className = 'toast sk xp';
    toast.textContent = text;
    toasts.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('fade');
      setTimeout(() => toast.remove(), 400);
    }, 2400);
  }

  function refreshPetState() {
    document.dispatchEvent(new CustomEvent('petpro:refresh-pet'));
  }

  function setRadialPosition(node, index, total, radius) {
    const angle = -90 + (360 / total) * index;
    const radians = angle * Math.PI / 180;
    node.style.setProperty('--angle', `${angle}deg`);
    node.style.setProperty('--inverse-angle', `${-angle}deg`);
    node.style.setProperty('--radius', `${radius}px`);
    node.style.setProperty('--radial-x', `${Math.cos(radians) * radius}px`);
    node.style.setProperty('--radial-y', `${Math.sin(radians) * radius}px`);
  }

  function makeCategoryButton(category, index, total, selectCategory) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'emote-node emote-category';
    button.title = category.label;
    button.dataset.category = category.id;
    button.appendChild(emoteImg(category.icon));
    const label = document.createElement('span');
    label.className = 'emote-label';
    label.textContent = category.label;
    button.appendChild(label);
    setRadialPosition(button, index, total, 114);
    button.addEventListener('click', () => selectCategory(category.id));
    return button;
  }

  function makeItemButton(target, entry, index, total, mode) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'emote-node emote-choice';
    setRadialPosition(button, index, total, 66);

    if (typeof entry === 'object' && entry.action) {
      const selected = RPS[entry.action];
      button.classList.add('emote-rps');
      button.title = selected.label;
      button.appendChild(rpsEmoteImg(entry.action));
      button.addEventListener('click', () => inviteRps(target, entry.action).catch((err) => {
        showRpsNotice(err?.message || 'Не удалось отправить вызов');
      }));
      return button;
    }

    button.title = `Emote ${entry + 1}`;
    button.appendChild(emoteImg(entry));
    button.addEventListener('click', () => chooseEmote(target, entry, mode));
    return button;
  }

  function buildMenu(target, mode) {
    const categories = mode === 'pet' ? PET_GROUPS : WALL_GROUPS;
    let active = mode === 'wall' ? 'game' : categories[0].id;

    const root = document.createElement('div');
    root.className = `emote-wheel ${mode === 'pet' ? 'pet-mode' : 'wall-mode'}`;
    root.setAttribute('role', 'menu');

    const center = document.createElement('button');
    center.type = 'button';
    center.className = 'emote-wheel-center';
    center.addEventListener('click', closeMenu);
    root.appendChild(center);

    const categoryRing = document.createElement('div');
    categoryRing.className = 'emote-category-ring';
    root.appendChild(categoryRing);

    const itemRing = document.createElement('div');
    itemRing.className = 'emote-item-ring';
    root.appendChild(itemRing);

    function selectCategoryAtPoint(event) {
      if (event.target.closest('.emote-choice, .emote-wheel-center')) return;
      const box = root.getBoundingClientRect();
      const cx = box.left + box.width / 2;
      const cy = box.top + box.height / 2;
      const dx = event.clientX - cx;
      const dy = event.clientY - cy;
      const distance = Math.hypot(dx, dy);
      if (distance < box.width * 0.30 || distance > box.width * 0.50) return;
      const degrees = (Math.atan2(dy, dx) * 180 / Math.PI + 450) % 360;
      const index = Math.round(degrees / (360 / categories.length)) % categories.length;
      active = categories[index].id;
      event.preventDefault();
      event.stopPropagation();
      render();
    }

    root.addEventListener('click', selectCategoryAtPoint, true);

    function render() {
      const selected = categories.find((category) => category.id === active) || categories[0];
      center.innerHTML = `<b>${escapeHtml(selected.label)}</b><span>Esc</span>`;
      categoryRing.replaceChildren(...categories.map((category, index) => {
        const button = makeCategoryButton(category, index, categories.length, (id) => {
          active = id;
          render();
        });
        button.classList.toggle('on', category.id === selected.id);
        return button;
      }));
      itemRing.replaceChildren(...selected.entries.map((entry, index) => (
        makeItemButton(target, entry, index, selected.entries.length, mode)
      )));
    }

    render();
    return root;
  }

  function buildRpsChoiceMenu(challenge) {
    const root = document.createElement('div');
    root.className = 'emote-wheel rps-choice-mode';
    root.setAttribute('role', 'menu');

    const center = document.createElement('button');
    center.type = 'button';
    center.className = 'emote-wheel-center';
    center.innerHTML = '<b>Ваш ход</b><span>Esc</span>';
    center.addEventListener('click', closeMenu);
    root.appendChild(center);

    const itemRing = document.createElement('div');
    itemRing.className = 'emote-item-ring';
    ['rock', 'scissors', 'paper'].forEach((key, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'emote-node emote-rps';
      button.title = RPS[key].label;
      button.appendChild(rpsEmoteImg(key));
      setRadialPosition(button, index, 3, 86);
      button.addEventListener('click', () => chooseRpsResponse(challenge, key).catch((err) => {
        showRpsNotice(err?.message || 'Не удалось сделать ход');
      }));
      itemRing.appendChild(button);
    });
    root.appendChild(itemRing);
    return root;
  }

  function openRpsChoice(challenge) {
    closeMenu();
    menu = buildRpsChoiceMenu(challenge);
    document.body.appendChild(menu);
    placeMenu(window.innerWidth / 2, window.innerHeight / 2);
  }

  function openMenu(target, x, y, mode) {
    closeMenu();
    menu = buildMenu(target, mode);
    document.body.appendChild(menu);
    placeMenu(x, y);
  }

  document.addEventListener('click', (event) => {
    const pet = event.target.closest('#screen-pet .petscreen .pixelpet, #dockPetScreen .pixelpet');
    if (!pet || event.target.closest('.emote-wheel')) {
      if (!event.target.closest('.emote-wheel')) closeMenu();
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const box = pet.getBoundingClientRect();
    openMenu(pet, box.left + box.width / 2, box.top + box.height / 2, 'pet');
  }, true);

  document.addEventListener('contextmenu', (event) => {
    const target = event.target.closest('.team-playground .team-pet');
    if (!target) return;
    event.preventDefault();
    event.stopPropagation();
    decorateTeamPets().finally(() => openMenu(target, event.clientX, event.clientY, 'wall'));
  }, true);

  async function rpsChallenges() {
    if (!api?.isAuthed?.()) return [];
    return api.get('/rps/challenges').catch(() => []);
  }

  async function currentUserId() {
    if (!api?.isAuthed?.()) return null;
    const me = await api.get('/auth/me').catch(() => null);
    return me?.id || null;
  }

  async function respondRps(challenge, accept) {
    const next = await api.post(`/rps/challenges/${challenge.id}/respond`, { accept });
    if (accept) {
      openRpsChoice(next);
    } else {
      showRpsNotice('Вызов отклонён');
    }
    refreshRpsPanel();
  }

  function ensureRpsPanel() {
    if (rpsPanel) return rpsPanel;
    rpsPanel = document.createElement('div');
    rpsPanel.className = 'rps-panel';
    rpsPanel.hidden = true;
    document.body.appendChild(rpsPanel);
    return rpsPanel;
  }

  async function refreshRpsPanel() {
    const panel = ensureRpsPanel();
    const [items, meId] = await Promise.all([rpsChallenges(), currentUserId()]);
    const incoming = items.filter((item) => item.opponent_id === meId && item.status === 'pending');
    const awaitingChoice = items.find(
      (item) => item.opponent_id === meId && item.status === 'accepted' && !item.opponent_choice
    );
    if (!incoming.length && !awaitingChoice) {
      panel.hidden = true;
      panel.replaceChildren();
      return;
    }

    panel.hidden = false;
    panel.replaceChildren();
    if (awaitingChoice) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'rps-card primary';
      button.textContent = 'Выбрать ход в КНБ';
      button.addEventListener('click', () => openRpsChoice(awaitingChoice));
      panel.appendChild(button);
    }
    incoming.forEach((challenge) => {
      const card = document.createElement('div');
      card.className = 'rps-card';
      card.innerHTML = '<b>Камень-ножницы-бумага</b><span>Вас вызывают на стене</span>';
      const actions = document.createElement('div');
      actions.className = 'rps-card-actions';
      const accept = document.createElement('button');
      accept.type = 'button';
      accept.textContent = 'Принять';
      accept.addEventListener('click', () => respondRps(challenge, true).catch(() => showRpsNotice('Ошибка')));
      const decline = document.createElement('button');
      decline.type = 'button';
      decline.className = 'danger';
      decline.textContent = 'Отказаться';
      decline.addEventListener('click', () => respondRps(challenge, false).catch(() => showRpsNotice('Ошибка')));
      actions.append(accept, decline);
      card.appendChild(actions);
      panel.appendChild(card);
    });
  }

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeMenu();
  });

  window.addEventListener('resize', closeMenu);
  document.addEventListener('scroll', closeMenu, true);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      scheduleTeamDecor();
      refreshRpsPanel();
    }
  });
  const playground = document.getElementById('teamPlayground');
  if (playground) {
    new MutationObserver(scheduleTeamDecor).observe(playground, { childList: true, subtree: true });
  }
  setTimeout(() => {
    decorateTeamPets().catch(() => {});
    refreshRpsPanel();
    rpsTimer = setInterval(refreshRpsPanel, 12000);
  }, 1200);
  window.addEventListener('beforeunload', () => {
    clearInterval(rpsTimer);
    clearTimeout(teamDecorTimer);
  });
})();
