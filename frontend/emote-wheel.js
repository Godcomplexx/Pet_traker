(function () {
  'use strict';

  const api = window.api;
  const menuUi = window.petproEmoteWheelMenu;
  if (!menuUi) return;

  const qs = (sel, root = document) => root.querySelector(sel);
  const WALL_EMOTE_KEY = 'petpro.wallEmotes';
  const { RPS, buildMenu, buildRpsChoiceMenu, emoteImg, emotePath, rpsEmoteImg } = menuUi;

  let menu = null;
  let workspaceId = null;
  let rpsPanel = null;
  let rpsTimer = null;
  let teamDecorTimer = null;

  function readWallEmotes() {
    try {
      const parsed = JSON.parse(localStorage.getItem(WALL_EMOTE_KEY) || '{}');
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch {
      return {};
    }
  }

  function writeWallEmotes(value) {
    try {
      localStorage.setItem(WALL_EMOTE_KEY, JSON.stringify(value));
    } catch {
      // Local visual preference only.
    }
  }

  function saveWallEmote(target, index) {
    const key = target?.dataset?.userId || target?.dataset?.petId || '';
    if (!key) return;
    const emotes = readWallEmotes();
    emotes[key] = Number(index);
    writeWallEmotes(emotes);
    target.dataset.wallEmote = String(index);
  }

  function storedWallEmote(pet) {
    const emotes = readWallEmotes();
    return emotes[pet.user_id] ?? emotes[pet.id];
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
    const existing = screen.querySelector('.pipoya-selected-emote');
    if (existing?.dataset.emoteIndex === String(index)) return;
    const removable = teamPet ? '.pet-emote' : '.pipoya-selected-emote, .pipoya-burst, .rps-burst';
    screen.querySelectorAll(removable).forEach((node) => node.remove());
    const emote = document.createElement('div');
    emote.className = 'pet-emote state-emote pipoya-selected-emote';
    emote.dataset.emoteIndex = String(index);
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
      const emote = storedWallEmote(pet);
      if (emote !== undefined) setPetEmote(node, Number(emote));
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
    const body = document.createElement('div');
    body.className = 't';
    const name = document.createElement('b');
    name.textContent = 'Вы';
    const meta = document.createElement('div');
    meta.className = 'mono';
    meta.textContent = 'сейчас';
    body.append(name, document.createTextNode(` - ${text}`), meta);
    const img = document.createElement('img');
    img.className = 'wall-image pipoya-wall-image';
    img.src = imageData;
    img.alt = '';
    node.append(body, img);
    feed.prepend(node);
  }

  async function postToWall(text, index) {
    const wsId = await getWorkspaceId();
    if (!wsId || !api?.post) return;
    const imageData = await emoteDataUrl(index);
    await api.post(`/workspaces/${wsId}/wall`, { text, image_data: imageData });
    prependLocalWallPost(text, imageData);
  }

  function chooseEmote(target, index, mode) {
    closeMenu();
    if (mode === 'wall') saveWallEmote(target, index);
    setPetEmote(target, index);
  }

  async function inviteRps(target, key) {
    if (!RPS[key]) return;
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
      await api.post(`/workspaces/${wsId}/rps`, { opponent_id: opponentId, choice: key });
      showRpsBurst(target, key);
      showRpsNotice(`Вызов отправлен: ${teamPetName(target)}`);
      refreshRpsPanel();
    } catch (err) {
      showRpsNotice(err?.message || 'Не удалось отправить вызов');
    }
  }

  async function playRpsBot(target, key) {
    const wsId = await getWorkspaceId();
    if (!RPS[key] || !wsId || !api?.post) return;
    try {
      await api.post(`/workspaces/${wsId}/rps/bot`, { choice: key });
      showRpsBurst(target, key);
      refreshPetState();
      showRpsNotice('КНБ с ботом сыграно. Результат на стене.');
      setTimeout(() => {
        if (document.querySelector('#screen-team.on')) document.querySelector('[data-go="team"]')?.click();
      }, 450);
    } catch (err) {
      showRpsNotice(err?.message || 'Не удалось сыграть с ботом');
    }
  }

  async function chooseRpsResponse(challenge, key) {
    if (!RPS[key] || !challenge?.id) return;
    closeMenu();
    await api.post(`/rps/challenges/${challenge.id}/choice`, { choice: key });
    refreshPetState();
    showRpsNotice(`Вы выбрали: ${RPS[key].label}`);
    refreshRpsPanel();
    setTimeout(() => {
      if (document.querySelector('#screen-team.on')) document.querySelector('[data-go="team"]')?.click();
    }, 500);
  }

  function teamPetName(target) {
    return qs('.team-name', target)?.textContent?.trim() || 'питомец';
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

  function openRpsChoice(challenge) {
    closeMenu();
    menu = buildRpsChoiceMenu(challenge, {
      closeMenu,
      chooseRpsResponse: (item, key) => chooseRpsResponse(item, key).catch(() => showRpsNotice('Ошибка')),
    });
    document.body.appendChild(menu);
    placeMenu(window.innerWidth / 2, window.innerHeight / 2);
  }

  function openMenu(target, x, y, mode) {
    closeMenu();
    menu = buildMenu(target, mode, {
      chooseEmote,
      closeMenu,
      inviteRps: (item, key) => inviteRps(item, key).catch((err) => showRpsNotice(err?.message || 'Не удалось отправить вызов')),
    });
    document.body.appendChild(menu);
    placeMenu(x, y);
  }

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
    if (accept) openRpsChoice(next);
    else showRpsNotice('Вызов отклонён');
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
    const awaitingChoice = items.find((item) => item.opponent_id === meId && item.status === 'accepted' && !item.opponent_choice);
    if (!incoming.length && !awaitingChoice) {
      panel.hidden = true;
      panel.replaceChildren();
      return;
    }
    panel.hidden = false;
    panel.replaceChildren();
    if (awaitingChoice) panel.appendChild(rpsPrimaryButton(awaitingChoice));
    incoming.forEach((challenge) => panel.appendChild(rpsChallengeCard(challenge)));
  }

  function rpsPrimaryButton(challenge) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'rps-card primary';
    button.textContent = 'Выбрать ход в КНБ';
    button.addEventListener('click', () => openRpsChoice(challenge));
    return button;
  }

  function rpsChallengeCard(challenge) {
    const card = document.createElement('div');
    card.className = 'rps-card';
    const title = document.createElement('b');
    title.textContent = 'Камень-ножницы-бумага';
    const text = document.createElement('span');
    text.textContent = 'Вас вызывают на стене';
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
    card.append(title, text, actions);
    return card;
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
  if (playground) new MutationObserver(scheduleTeamDecor).observe(playground, { childList: true, subtree: true });
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
