/* PetPro — real frontend wired to the FastAPI backend. Reuses wireframes.css. */
(function () {
  'use strict';

  const api = window.api;
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const PROJECT_STATUSES = ['IDEA', 'PLANNING', 'ACTIVE', 'PAUSED', 'IN_REVIEW', 'DONE', 'ARCHIVED'];
  const ARTICLE_STATUSES = [
    'IDEA', 'PLANNING', 'WRITING', 'INTERNAL_REVIEW', 'REVISION',
    'SUBMITTED', 'UNDER_REVIEW', 'ACCEPTED', 'PUBLISHED', 'ARCHIVED',
  ];
  const PROJECT_ROLES = ['PROJECT_OWNER', 'LEAD', 'CONTRIBUTOR', 'REVIEWER', 'OBSERVER'];
  const ARTICLE_ROLES = ['AUTHOR', 'CO_AUTHOR', 'REVIEWER', 'EDITOR', 'OBSERVER'];
  const TASK_TYPES = [
    'RESEARCH', 'WRITING', 'REVIEW', 'FORMATTING', 'DEVELOPMENT', 'DESIGN', 'TESTING',
    'DEPLOYMENT', 'EXPERIMENT', 'SUBMISSION', 'RESPONSE_TO_REVIEWER', 'ADMIN', 'PERSONAL', 'OTHER',
  ];
  const TASK_PRIORITIES = ['LOW', 'MEDIUM', 'HIGH', 'URGENT'];
  const CHARACTER_CATALOG = [
    { id: 'char_agent_mike', name: 'Agent Mike', file: 'agent_mike.png', frameWidth: 32, frameHeight: 32, frames: 2, opaqueTop: 17, opaqueCenter: 19, hatScale: 0.88, hatFlip: true },
    { id: 'char_angie', name: 'Angie', file: 'angie.png', frameWidth: 32, frameHeight: 32, frames: 6, opaqueTop: 10, opaqueCenter: 15.5, hatScale: 0.89 },
    { id: 'char_armand', name: 'Armand', file: 'armand.png', frameWidth: 32, frameHeight: 32, frames: 5, opaqueTop: 1, opaqueCenter: 15, hatScale: 1.25 },
    { id: 'char_ballooney', name: 'Ballooney', file: 'ballooney.png', frameWidth: 32, frameHeight: 32, frames: 2, opaqueTop: 3, opaqueCenter: 15.5, hatScale: 0.78 },
    { id: 'char_barry_cherry', name: 'Barry Cherry', file: 'barry_cherry.png', frameWidth: 32, frameHeight: 32, frames: 4, opaqueTop: 16, opaqueCenter: 16, hatScale: 0.94 },
    { id: 'char_big_red', name: 'Big Red', file: 'big_red.png', frameWidth: 32, frameHeight: 32, frames: 6, opaqueTop: 12, opaqueCenter: 15, hatScale: 1.06, hatFlip: true },
    { id: 'char_blankey', name: 'Blankey', file: 'blankey.png', frameWidth: 32, frameHeight: 32, frames: 4, opaqueTop: 9, opaqueCenter: 15.5, hatScale: 1 },
    { id: 'char_blocky_bub', name: 'Blocky Bub', file: 'blocky_bub.png', frameWidth: 16, frameHeight: 16, frames: 2, opaqueTop: 4, opaqueCenter: 7.5, hatScale: 0.68 },
    { id: 'char_bub', name: 'Bub', file: 'bub.png', frameWidth: 16, frameHeight: 16, frames: 2, opaqueTop: 5, opaqueCenter: 7.5, hatScale: 0.68 },
    { id: 'char_bumpy_the_robot', name: 'Bumpy the Robot', file: 'bumpy_the_robot.png', frameWidth: 16, frameHeight: 16, frames: 4, opaqueTop: 3, opaqueCenter: 7.5, hatScale: 0.78 },
    { id: 'char_bushly', name: 'Bushly', file: 'bushly.png', frameWidth: 16, frameHeight: 16, frames: 3, opaqueTop: 3, opaqueCenter: 7.5, hatScale: 0.68 },
    { id: 'char_chi_chi_the_bird', name: 'Chi Chi the Bird', file: 'chi_chi_the_bird.png', frameWidth: 16, frameHeight: 16, frames: 1, opaqueTop: 2, opaqueCenter: 7.5, hatScale: 0.89 },
    { id: 'char_daikon', name: 'Daikon', file: 'daikon.png', frameWidth: 16, frameHeight: 32, frames: 2, opaqueTop: 14, opaqueCenter: 7.5, hatScale: 0.68 },
    { id: 'char_devo_the_devil', name: 'Devo the Devil', file: 'devo_the_devil.png', frameWidth: 16, frameHeight: 16, frames: 1, opaqueTop: 2, opaqueCenter: 7.5, hatScale: 0.89 },
    { id: 'char_diver_the_fish', name: 'Diver the Fish', file: 'diver_the_fish.png', frameWidth: 16, frameHeight: 16, frames: 4, opaqueTop: 1, opaqueCenter: 7, hatScale: 0.83 },
    { id: 'char_fairy', name: 'Fairy', file: 'fairy.png', frameWidth: 32, frameHeight: 32, frames: 4, opaqueTop: 8, opaqueCenter: 15.5, hatScale: 0.76 },
    { id: 'char_geralt', name: 'Geralt', file: 'geralt.png', frameWidth: 32, frameHeight: 32, frames: 2, opaqueTop: 16, opaqueCenter: 16, hatScale: 0.72 },
    { id: 'char_gloppy_slime', name: 'Gloppy Slime', file: 'gloppy_slime.png', frameWidth: 16, frameHeight: 16, frames: 2, opaqueTop: 2, opaqueCenter: 7.5, hatScale: 0.7 },
    { id: 'char_grizzly', name: 'Grizzly', file: 'grizzly.png', frameWidth: 48, frameHeight: 32, frames: 1, opaqueTop: 10, opaqueCenter: 23, hatScale: 1.25 },
    { id: 'char_gum_bot', name: 'Gum Bot', file: 'gum_bot.png', frameWidth: 32, frameHeight: 32, frames: 4, opaqueTop: 14, opaqueCenter: 15.5, hatScale: 0.89 },
    { id: 'char_hermie', name: 'Hermie', file: 'hermie.png', frameWidth: 32, frameHeight: 32, frames: 2, opaqueTop: 19, opaqueCenter: 16, hatScale: 1.06, hatFlip: true },
    { id: 'char_jumpy_lumpy', name: 'Jumpy Lumpy', file: 'jumpy_lumpy.png', frameWidth: 32, frameHeight: 32, frames: 2, opaqueTop: 21, opaqueCenter: 15.5, hatScale: 0.78 },
    { id: 'char_lil_wiz', name: 'Lil Wiz', file: 'lil_wiz.png', frameWidth: 32, frameHeight: 32, frames: 5, opaqueTop: 6, opaqueCenter: 15.5, hatScale: 1.11 },
    { id: 'char_martian_red', name: 'Martian Red', file: 'martian_red.png', frameWidth: 32, frameHeight: 32, frames: 2, opaqueTop: 12, opaqueCenter: 15.5, hatScale: 0.92, hatFlip: true },
    { id: 'char_moe_scotty', name: 'Moe Scotty', file: 'moe_scotty.png', frameWidth: 32, frameHeight: 32, frames: 4, opaqueTop: 4, opaqueCenter: 16, hatScale: 1.25 },
    { id: 'char_mr_chomps', name: 'Mr. Chomps', file: 'mr_chomps.png', frameWidth: 32, frameHeight: 32, frames: 12, opaqueTop: 18, opaqueCenter: 15, hatScale: 1.25 },
    { id: 'char_mr_circuit', name: 'Mr. Circuit', file: 'mr_circuit.png', frameWidth: 32, frameHeight: 32, frames: 2, opaqueTop: 10, opaqueCenter: 15, hatScale: 0.9 },
    { id: 'char_mr_man', name: 'Mr. Man', file: 'mr_man.png', frameWidth: 16, frameHeight: 16, frames: 4, opaqueTop: 1, opaqueCenter: 7.5, hatScale: 0.68 },
    { id: 'char_mr_mochi', name: 'Mr. Mochi', file: 'mr_mochi.png', frameWidth: 32, frameHeight: 32, frames: 2, opaqueTop: 14, opaqueCenter: 15.5, hatScale: 0.88 },
    { id: 'char_octi', name: 'Octi', file: 'octi.png', frameWidth: 16, frameHeight: 16, frames: 2, opaqueTop: 4, opaqueCenter: 7.5, hatScale: 0.78 },
    { id: 'char_onion_lad', name: 'Onion Lad', file: 'onion_lad.png', frameWidth: 16, frameHeight: 16, frames: 2, opaqueTop: 3, opaqueCenter: 6.5, hatScale: 0.78 },
    { id: 'char_orange', name: 'Orange', file: 'orange.png', frameWidth: 32, frameHeight: 32, frames: 4, opaqueTop: 14, opaqueCenter: 15.5, hatScale: 0.9 },
    { id: 'char_orc', name: 'Orc', file: 'orc.png', frameWidth: 64, frameHeight: 32, frames: 7, opaqueTop: 3, opaqueCenter: 27.5, hatScale: 1.25, hatFlip: true },
    { id: 'char_orchid_owl', name: 'Orchid Owl', file: 'orchid_owl.png', frameWidth: 32, frameHeight: 32, frames: 2, opaqueTop: 14, opaqueCenter: 15.5, hatScale: 0.82 },
    { id: 'char_penguin', name: 'Penguin', file: 'penguin.png', frameWidth: 16, frameHeight: 16, frames: 5, opaqueTop: 1, opaqueCenter: 7.5, hatScale: 0.76 },
    { id: 'char_percy', name: 'Percy', file: 'percy.png', frameWidth: 32, frameHeight: 32, frames: 9, opaqueTop: 10, opaqueCenter: 15, hatScale: 1.25, hatFlip: true },
    { id: 'char_pokey_bub', name: 'Pokey Bub', file: 'pokey_bub.png', frameWidth: 16, frameHeight: 16, frames: 2, opaqueTop: 3, opaqueCenter: 7.5, hatScale: 0.89 },
    { id: 'char_roach', name: 'Roach', file: 'roach.png', frameWidth: 32, frameHeight: 32, frames: 2, opaqueTop: 13, opaqueCenter: 17, hatScale: 0.94, hatFlip: true },
    { id: 'char_robo_pumpkin', name: 'Robo Pumpkin', file: 'robo_pumpkin.png', frameWidth: 16, frameHeight: 16, frames: 1, opaqueTop: 0, opaqueCenter: 7.5, hatScale: 0.78 },
    { id: 'char_robo_retro', name: 'Robo Retro', file: 'robo_retro.png', frameWidth: 32, frameHeight: 32, frames: 9, opaqueTop: 14, opaqueCenter: 15.5, hatScale: 1.22 },
    { id: 'char_robo_totem', name: 'Robo Totem', file: 'robo_totem.png', frameWidth: 16, frameHeight: 32, frames: 1, opaqueTop: 10, opaqueCenter: 7.5, hatScale: 0.78 },
    { id: 'char_robot_j5', name: 'Robot J5', file: 'robot_j5.png', frameWidth: 32, frameHeight: 32, frames: 5, opaqueTop: 16, opaqueCenter: 15.5, hatScale: 1 },
    { id: 'char_robot_walky', name: 'Robot Walky', file: 'robot_walky.png', frameWidth: 32, frameHeight: 32, frames: 2, opaqueTop: 15, opaqueCenter: 15.5, hatScale: 0.88 },
    { id: 'char_rocket_cherry', name: 'Rocket Cherry', file: 'rocket_cherry.png', frameWidth: 16, frameHeight: 32, frames: 2, opaqueTop: 10, opaqueCenter: 8.5, hatScale: 0.78, hatFlip: true },
    { id: 'char_rolling_nero', name: 'Rolling Nero', file: 'rolling_nero.png', frameWidth: 16, frameHeight: 16, frames: 6, opaqueTop: 0, opaqueCenter: 7.5, hatScale: 0.89 },
    { id: 'char_skeleton', name: 'Skeleton', file: 'skeleton.png', frameWidth: 32, frameHeight: 32, frames: 9, opaqueTop: 5, opaqueCenter: 16, hatScale: 0.92, hatFlip: true },
    { id: 'char_snip_snap_crab', name: 'Snip Snap Crab', file: 'snip_snap_crab.png', frameWidth: 32, frameHeight: 32, frames: 1, opaqueTop: 15, opaqueCenter: 15.5, hatScale: 1.25 },
    { id: 'char_spikey_bub', name: 'Spikey Bub', file: 'spikey_bub.png', frameWidth: 16, frameHeight: 16, frames: 2, opaqueTop: 2, opaqueCenter: 7.5, hatScale: 0.68, hatFlip: true },
    { id: 'char_squirmy_wormy', name: 'Squirmy Wormy', file: 'squirmy_wormy.png', frameWidth: 32, frameHeight: 32, frames: 3, opaqueTop: 21, opaqueCenter: 15, hatScale: 1.25, hatFlip: true },
    { id: 'char_toggle', name: 'Toggle', file: 'toggle.png', frameWidth: 32, frameHeight: 32, frames: 5, opaqueTop: 11, opaqueCenter: 15.5, hatScale: 0.78, hatFlip: true },
    { id: 'char_twiggy', name: 'Twiggy', file: 'twiggy.png', frameWidth: 32, frameHeight: 32, frames: 5, opaqueTop: 7, opaqueCenter: 15, hatScale: 0.92 },
    { id: 'char_vessa', name: 'Vessa', file: 'vessa.png', frameWidth: 32, frameHeight: 32, frames: 10, opaqueTop: 8, opaqueCenter: 15, hatScale: 0.83, hatFlip: true },
    { id: 'char_wispy_fire', name: 'Wispy Fire', file: 'wispy_fire.png', frameWidth: 32, frameHeight: 32, frames: 21, opaqueTop: 4, opaqueCenter: 15.5, hatScale: 0.89 },
  ];
  const CHARACTER_INDEX = Object.fromEntries(CHARACTER_CATALOG.map((c) => [c.id, c]));
  const LEGACY_SPECIES = new Set(['capybara', 'cat', 'dog', 'frog', 'axolotl']);
  const ACTIVE_PROJECT_STATUSES = new Set(['IDEA', 'PLANNING', 'ACTIVE', 'PAUSED', 'IN_REVIEW']);
  const ACTIVE_ARTICLE_STATUSES = new Set([
    'IDEA', 'PLANNING', 'WRITING', 'INTERNAL_REVIEW', 'REVISION', 'SUBMITTED', 'UNDER_REVIEW',
  ]);

  const state = {
    me: null,
    workspaces: [],
    wsId: null,
    pet: null,
    prevXp: null,
    projects: [],
    articles: [],
    members: [],
    pollTimer: null,
    shopTab: 'all',
    shopOpen: false,
    dockBagPage: 0,
    foodBagPage: 0,
    wallImageData: null,
    wallUnread: 0,
    currentScreen: null,
  };

  const esc = (s) =>
    String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const initials = (name) =>
    (name || '?').split(/\s+/).map((w) => w[0]).join('').slice(0, 2).toUpperCase();

  const cdnIcon = (code) => `https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/${code}.svg`;
  const ICON_FALLBACKS = {
    dashboard: cdnIcon('1f4ca'),
    lab: cdnIcon('1f9ea'),
    projects: cdnIcon('1f4c1'),
    articles: cdnIcon('1f4c4'),
    tasks: cdnIcon('2705'),
    pet: cdnIcon('1f43e'),
    game: cdnIcon('1f3ae'),
    wall: cdnIcon('1f4ac'),
    notifications: cdnIcon('1f514'),
    logout: cdnIcon('1f6aa'),
    copy: cdnIcon('1f4cb'),
    coin: cdnIcon('1fa99'),
    apple: cdnIcon('1f34e'),
    food_banana: cdnIcon('1f34c'),
    food_berry: cdnIcon('1fad0'),
    food_carrot: cdnIcon('1f955'),
    food_cupcake: cdnIcon('1f9c1'),
    food_fish: cdnIcon('1f41f'),
    food_milk: cdnIcon('1f95b'),
    food_ramen: cdnIcon('1f35c'),
    food_rice: cdnIcon('1f35a'),
    heart: cdnIcon('1f49a'),
    ball: cdnIcon('1f3be'),
    party: cdnIcon('1f389'),
    crown: cdnIcon('1f451'),
    grad: cdnIcon('1f393'),
    flower: cdnIcon('1f338'),
    star: cdnIcon('2b50'),
    sunglasses: cdnIcon('1f60e'),
    microscope: cdnIcon('1f52c'),
    moon: cdnIcon('1f319'),
    ribbon: cdnIcon('1f380'),
    fire: cdnIcon('1f525'),
    gem: cdnIcon('1f48e'),
    happy: cdnIcon('1f60a'),
    ok: cdnIcon('1f642'),
    sad: cdnIcon('1f61f'),
    hungry: cdnIcon('1f37d'),
    sleepy: cdnIcon('1f634'),
    cat: cdnIcon('1f431'),
    dog: cdnIcon('1f436'),
    frog: cdnIcon('1f438'),
    axolotl: cdnIcon('1f98e'),
    capybara: cdnIcon('1f9ab'),
  };
  const PICKUP_SPRITES = {
    coin: { file: 'coin.png', frames: 4, w: 16, h: 16, label: 'монеты' },
    small_coin: { file: 'small_coin.png', frames: 4, w: 16, h: 16, label: 'монеты' },
    heart: { file: 'heart_spin.png', frames: 4, w: 16, h: 16, label: 'сердце' },
    pickup_heart: { file: 'heart_spin.png', frames: 4, w: 16, h: 16, label: 'сердце' },
    chest: { file: 'chest.png', frames: 3, w: 32, h: 16, label: 'кейс' },
    present: { file: 'present.png', frames: 3, w: 16, h: 16, label: 'подарок' },
    health_kit: { file: 'health_kit.png', frames: 1, w: 16, h: 16, label: 'аптечка' },
  };

  window.petproIconFallback = (img) => {
    const step = Number(img.dataset.fallbackStep || 0);
    const name = img.dataset.iconName;
    if (step === 0 && name) {
      img.dataset.fallbackStep = '1';
      img.src = `assets/custom-icons/${name}.png`;
      return;
    }
    const fallback = img.dataset.fallback;
    if (step <= 1 && fallback) {
      img.dataset.fallbackStep = '2';
      img.src = fallback;
      return;
    }
    img.style.display = 'none';
  };

  function iconImg(name, alt = '', size = '') {
    if (PICKUP_SPRITES[name]) return pickupSprite(name, alt, size);
    return `<img class="ui-icon ${size}" src="assets/custom-icons/${name}.svg" data-icon-name="${esc(name)}" data-fallback="${esc(ICON_FALLBACKS[name] || '')}" alt="${esc(alt)}" onerror="window.petproIconFallback&&window.petproIconFallback(this)">`;
  }

  function pickupSprite(name, alt = '', size = '') {
    const s = PICKUP_SPRITES[name];
    const framesClass = s.frames === 4 ? 'pickup-4' : (s.frames === 3 ? 'pickup-3' : 'pickup-static');
    const label = alt || s.label || name;
    const scale = size.includes('case-xl') ? 3.05 : (size.includes('xl') ? 2.15 : (size.includes('lg') ? 1.55 : 1.25));
    const w = Math.round(s.w * scale);
    const h = Math.round(s.h * scale);
    const sheet = Math.round(s.w * s.frames * scale);
    return `<span class="ui-icon pickup-sprite ${framesClass} ${size}" role="img" aria-label="${esc(label)}" style="--pickup-url:url('assets/pickups/${s.file}');--pickup-w:${w}px;--pickup-h:${h}px;--pickup-sheet:${sheet}px;"></span>`;
  }

  function iconLabel(name, text, size = '') {
    return `<span class="icon-label">${iconImg(name, '', size)}<span>${esc(text)}</span></span>`;
  }

  function iconNode(name, size = '') {
    const holder = document.createElement('span');
    holder.innerHTML = iconImg(name, '', size);
    return holder.firstElementChild;
  }

  function hydrateAssetIcons(root = document) {
    $$('.asset-icon[data-icon]', root).forEach((el) => {
      if (el.dataset.hydrated === '1') return;
      el.dataset.hydrated = '1';
      el.innerHTML = iconImg(el.dataset.icon, el.dataset.label || '', el.dataset.size || '');
    });
  }

  /* ---------------- toasts ---------------- */
  function toast(text, kind = '') {
    const el = document.createElement('div');
    el.className = 'toast sk ' + kind;
    el.textContent = text;
    $('#toasts').appendChild(el);
    setTimeout(() => {
      el.classList.add('fade');
      setTimeout(() => el.remove(), 400);
    }, 2600);
  }

  /* ---------------- navigation ---------------- */
  // Какой пункт меню подсветить для детальных экранов.
  const NAV_PARENT = { projdetail: 'projects', artdetail: 'articles', taskdetail: 'mytasks' };

  function go(name) {
    const prev = state.currentScreen;
    if (prev === 'team' && name !== 'team' && state.wsId) {
      api.del(`/workspaces/${state.wsId}/wall/presence`).catch(() => {});
    }
    state.currentScreen = name;
    $$('.screen').forEach((s) => s.classList.toggle('on', s.id === 'screen-' + name));
    const navKey = NAV_PARENT[name] || name;
    $$('#nav a').forEach((a) => a.classList.toggle('active', a.dataset.go === navKey));
    const main = $('.main');
    if (main) main.scrollTop = 0;
    const loaders = {
      lab: renderLab,
      dashboard: renderDashboard,
      projects: renderProjects,
      articles: renderArticles,
      mytasks: renderMyTasks,
      pet: renderPet,
      team: renderWall,
      gameroom: renderGameRoom,
      notif: renderNotifications,
    };
    if (loaders[name]) return loaders[name]();
    return undefined;
  }

  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-go]');
    if (t) {
      e.preventDefault();
      go(t.dataset.go);
    }
  });

  /* ---------------- auth ---------------- */
  let authMode = 'login';
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function setFieldError(field, msg) {
    const box = $(`.field-err[data-err="${field}"]`);
    if (box) box.textContent = msg || '';
    const input = { display_name: '#displayName', email: '#email', password: '#password', password2: '#password2' }[field];
    const el = input && $(input);
    if (el) {
      el.classList.toggle('invalid', !!msg);
      if (!msg && el.value) el.classList.add('valid');
      else el.classList.remove('valid');
    }
  }

  function clearAuthErrors() {
    $('#authError').textContent = '';
    ['display_name', 'email', 'password', 'password2'].forEach((f) => setFieldError(f, ''));
  }

  // Клиентская проверка перед отправкой. Возвращает true, если всё валидно.
  function validateAuth() {
    clearAuthErrors();
    const email = $('#email').value.trim();
    const password = $('#password').value;
    let ok = true;

    if (!email) {
      setFieldError('email', 'Введите email');
      ok = false;
    } else if (!EMAIL_RE.test(email)) {
      setFieldError('email', 'Введите корректный email (например, you@lab.ru)');
      ok = false;
    }

    if (!password) {
      setFieldError('password', 'Введите пароль');
      ok = false;
    } else if (authMode === 'reg') {
      if (password.length < 8) {
        setFieldError('password', 'Минимум 8 символов');
        ok = false;
      } else if (!/[A-Za-zА-Яа-я]/.test(password) || !/\d/.test(password)) {
        setFieldError('password', 'Нужны хотя бы одна буква и одна цифра');
        ok = false;
      }
    }

    if (authMode === 'reg') {
      const name = $('#displayName').value.trim();
      if (name.length < 2) {
        setFieldError('display_name', 'Имя должно содержать минимум 2 символа');
        ok = false;
      }
      if ($('#password2').value !== password) {
        setFieldError('password2', 'Пароли не совпадают');
        ok = false;
      }
    }
    return ok;
  }

  function switchMode(mode) {
    authMode = mode;
    $$('#authTabs button').forEach((x) => x.classList.toggle('on', x.dataset.tab === mode));
    const reg = mode === 'reg';
    $('#nameField').style.display = reg ? 'block' : 'none';
    $('#confirmField').style.display = reg ? 'block' : 'none';
    $('#pwHint').style.display = reg ? 'block' : 'none';
    $('#password').setAttribute('autocomplete', reg ? 'new-password' : 'current-password');
    $('#authGo').textContent = reg ? 'Создать →' : 'Войти →';
    clearAuthErrors();
  }

  $$('#authTabs button').forEach((b) => b.addEventListener('click', () => switchMode(b.dataset.tab)));

  // Снимаем ошибку с поля, как только пользователь его правит.
  ['displayName', 'email', 'password', 'password2'].forEach((id) => {
    const el = $('#' + id);
    if (el) el.addEventListener('input', () => {
      const field = id === 'displayName' ? 'display_name' : id;
      setFieldError(field, '');
      $('#authError').textContent = '';
    });
  });

  async function submitAuth() {
    if (!validateAuth()) return;
    const btn = $('#authGo');
    btn.disabled = true;
    const email = $('#email').value.trim();
    const password = $('#password').value;
    const display_name = $('#displayName').value.trim();
    try {
      if (authMode === 'reg') {
        const res = await api.register({ email, password, display_name });
        if (res.status === 'verification_required') {
          // Аккаунт создан — нужен код из письма.
          showVerifyPane(email);
          return;
        }
        // Подтверждение отключено на сервере — логинимся сразу.
        const tokens = await api.login({ email, password });
        api.setTokens(tokens);
        await enterApp();
      } else {
        const tokens = await api.login({ email, password });
        api.setTokens(tokens);
        await enterApp();
      }
    } catch (err) {
      if (err.fields) {
        Object.entries(err.fields).forEach(([f, m]) => setFieldError(f, m));
      }
      if (err.status === 409) {
        setFieldError('email', 'Этот email уже зарегистрирован');
      } else if (err.status === 401) {
        $('#authError').textContent = 'Неверный email или пароль';
      } else if (err.status === 403) {
        // Email не подтверждён — отправим на шаг ввода кода.
        $('#authError').textContent = '';
        try {
          await api.post('/auth/resend-code', { email });
          showVerifyPane(email);
        } catch {
          showVerifyPane(email);
        }
      } else if (!err.fields) {
        $('#authError').textContent = err.message || 'Ошибка авторизации';
      }
    } finally {
      btn.disabled = false;
    }
  }

  $('#authForm').addEventListener('submit', (e) => {
    e.preventDefault();
    submitAuth();
  });

  /* ---------------- email verification ---------------- */
  let pendingEmail = null;
  let pendingPassword = null;

  function showVerifyPane(email) {
    pendingEmail = email;
    pendingPassword = $('#password').value;
    $('#authPane').style.display = 'none';
    $('#verifyPane').style.display = 'block';
    $('#verifyEmail').textContent = email;
    $('#verifyCode').value = '';
    setFieldError('verify_code', '');
    $('#resendStatus').textContent = '';
    $('#devCodeHint').style.display = 'none';
    $('#verifyCode').focus();
  }

  function hideVerifyPane() {
    $('#verifyPane').style.display = 'none';
    $('#authPane').style.display = 'block';
  }

  $('#verifyCode').addEventListener('input', () => setFieldError('verify_code', ''));

  $('#verifyBtn').addEventListener('click', async () => {
    const code = $('#verifyCode').value.trim();
    if (code.length !== 6) return setFieldError('verify_code', 'Введите 6-значный код');
    const btn = $('#verifyBtn');
    btn.disabled = true;
    try {
      const tokens = await api.post('/auth/verify', { email: pendingEmail, code });
      api.setTokens(tokens);
      await enterApp();
    } catch (err) {
      setFieldError('verify_code', err.message || 'Неверный код');
    } finally {
      btn.disabled = false;
    }
  });

  $('#resendBtn').addEventListener('click', async () => {
    const btn = $('#resendBtn');
    const status = $('#resendStatus');
    btn.disabled = true;
    status.textContent = '';
    btn.textContent = 'Отправляем...';
    try {
      const r = await api.post('/auth/resend-code', { email: pendingEmail });
      toast('Код отправлен повторно', 'xp');
      status.textContent = 'Код отправлен повторно';
    } catch (err) {
      status.textContent = err.message || 'Не удалось отправить код';
    } finally {
      btn.disabled = false;
      btn.textContent = 'Отправить код ещё раз';
    }
  });

  $('#backToAuth').addEventListener('click', hideVerifyPane);

  $('#logoutBtn').addEventListener('click', () => {
    api.clearTokens();
    location.reload();
  });

  /* ---------------- bootstrap ---------------- */
  async function enterApp() {
    state.me = await api.get('/auth/me');
    state.workspaces = await api.get('/workspaces');

    $('#auth').classList.remove('on');

    // Нет ни одной лаборатории → показываем онбординг (создать / войти по коду).
    if (state.workspaces.length === 0) {
      showOnboarding();
      return;
    }
    state.wsId = state.workspaces[0].id;
    await afterWorkspace();
  }

  // После того как у пользователя есть лаборатория — проверяем питомца.
  async function afterWorkspace() {
    const pet = await api.get('/pets/me');
    state.pet = pet;
    state.prevXp = pet.xp;
    if (!pet.customized || LEGACY_SPECIES.has(pet.species) || !CHARACTER_INDEX[pet.species]) {
      showPetCreator(pet);
      return;
    }
    launchApp();
  }

  function launchApp() {
    $('#onboard').classList.remove('on');
    $('#petcreate').classList.remove('on');
    $('#app').style.display = 'grid';
    hydrateAssetIcons();
    initSidebarControls();
    $('#meName').innerHTML = `${esc(state.me.display_name)}<div class="mono">${esc(state.me.email)}</div>`;
    $('#meAvatar').textContent = initials(state.me.display_name);

    renderWorkspacePicker();
    // заранее грузим каталог магазина — чтобы шапки/фоны рисовались и в доке
    api.get('/shop/items').then((cat) => {
      state.shopCatalog = cat.items;
      cat.items.forEach((it) => (SHOP_INDEX[it.id] = it));
      const cp = $('#casePrice'); if (cp) cp.textContent = cat.case_price;
      if (state.pet) paintPet(state.pet);
    }).catch(() => {});
    refreshPet();
    refreshNotifBadge();
    refreshWallBadge();
    initPetDock();
    startPolling();
    go('dashboard');
  }

  // закреплённый питомец справа: сворачивание с запоминанием
  function initPetDock() {
    const dock = $('#petDock');
    const toggle = $('#petDockToggle');
    const app = $('#app');
    if (!dock || !toggle) return;
    try {
      if (localStorage.getItem('petpro_dock_collapsed') === '1') {
        dock.classList.add('collapsed');
        app && app.classList.add('dock-hidden');
      }
    } catch (e) {}
    toggle.addEventListener('click', () => {
      const collapsed = dock.classList.toggle('collapsed');
      app && app.classList.toggle('dock-hidden', collapsed);
      try { localStorage.setItem('petpro_dock_collapsed', collapsed ? '1' : '0'); } catch (e) {}
    });
  }

  function startPolling() {
    if (state.pollTimer) clearInterval(state.pollTimer);
    state.pollTimer = setInterval(async () => {
      if (!api.isAuthed() || !state.wsId) return;
      try {
        await refreshNotifBadge();
        await refreshWallBadge();
        const active = $('.screen.on');
        const name = active ? active.id.replace('screen-', '') : '';
        if (name === 'dashboard') await refreshDashboardLive();
        if (name === 'team') await renderWall();
        if (name === 'notif') await renderNotifications();
      } catch {
        // Polling is best-effort; explicit actions still surface errors via toasts.
      }
    }, 30000);
  }

  /* ---------------- onboarding ---------------- */
  function showOnboarding() {
    $('#app').style.display = 'none';
    $('#onboard').classList.add('on');
    $('#onboardHi').textContent = `привет, ${state.me.display_name.split(' ')[0]}!`;
  }

  function setObError(field, msg) {
    const box = $(`.field-err[data-err="${field}"]`);
    if (box) box.textContent = msg || '';
  }

  $$('#onboardTabs button').forEach((b) =>
    b.addEventListener('click', () => {
      const tab = b.dataset.otab;
      $$('#onboardTabs button').forEach((x) => x.classList.toggle('on', x === b));
      $('#onboardCreate').style.display = tab === 'create' ? 'block' : 'none';
      $('#onboardJoin').style.display = tab === 'join' ? 'block' : 'none';
      setObError('ob_name', ''); setObError('ob_code', '');
    }),
  );

  $('#obCreateBtn').addEventListener('click', async () => {
    setObError('ob_name', '');
    const name = $('#obName').value.trim();
    if (name.length < 2) return setObError('ob_name', 'Название минимум 2 символа');
    const btn = $('#obCreateBtn');
    btn.disabled = true;
    try {
      const ws = await api.post('/workspaces', { name, description: $('#obDesc').value.trim() || null });
      state.workspaces = [ws];
      state.wsId = ws.id;
      toast('Лаборатория создана', 'xp');
      $('#onboard').classList.remove('on');
      await afterWorkspace();
    } catch (err) {
      setObError('ob_name', err.message || 'Не удалось создать');
    } finally {
      btn.disabled = false;
    }
  });

  $('#obJoinBtn').addEventListener('click', async () => {
    setObError('ob_code', '');
    const code = $('#obCode').value.trim().toUpperCase();
    if (code.length < 4) return setObError('ob_code', 'Введите код приглашения');
    const btn = $('#obJoinBtn');
    btn.disabled = true;
    try {
      const ws = await api.post('/workspaces/join', { join_code: code });
      state.workspaces = await api.get('/workspaces');
      state.wsId = ws.id;
      toast(`Вы присоединились к «${ws.name}»`, 'xp');
      $('#onboard').classList.remove('on');
      await afterWorkspace();
    } catch (err) {
      if (err.status === 404) setObError('ob_code', 'Лаборатория с таким кодом не найдена');
      else if (err.status === 409) setObError('ob_code', 'Вы уже участник этой лаборатории');
      else setObError('ob_code', err.message || 'Не удалось присоединиться');
    } finally {
      btn.disabled = false;
    }
  });

  $('#obLogout').addEventListener('click', () => {
    api.clearTokens();
    location.reload();
  });

  /* ---------------- pet creator ---------------- */
  const pcDraft = { name: 'Кодзи', species: 'char_agent_mike', body_color: '#9dbf9b', accent_color: '#b08a9e' };

  function characterSrc(id) {
    const c = CHARACTER_INDEX[id];
    return c ? `assets/characters/${c.file}` : '';
  }

  function characterImage(id, alt = '') {
    const c = CHARACTER_INDEX[id];
    const src = characterSrc(id);
    if (!c || !src) return '';
    const label = esc(alt || c.name || id);
    const frameWidth = Number(c.frameWidth || 32);
    const frameHeight = Number(c.frameHeight || 32);
    const frames = Math.max(1, Number(c.frames || 1));
    const baseScale = 32 / frameHeight;
    const staticFrame = frames <= 1 ? ' data-static="1"' : '';
    return `<span class="asset-pet-sprite" role="img" aria-label="${label}"${staticFrame} style="--sprite-url:url('${src}');--sprite-frames:${frames};--sprite-frame-w:${frameWidth};--sprite-frame-h:${frameHeight};--sprite-base-scale:${baseScale};"></span>`;
  }

  function randomStarterCharacters(currentId = '') {
    const pool = CHARACTER_CATALOG.slice().sort(() => Math.random() - 0.5);
    const selected = [];
    if (CHARACTER_INDEX[currentId]) selected.push(CHARACTER_INDEX[currentId]);
    for (const c of pool) {
      if (selected.length >= 5) break;
      if (!selected.some((x) => x.id === c.id)) selected.push(c);
    }
    return selected;
  }

  function pcPreview() {
    const screen = $('#petcreate .petscreen');
    const old = screen.querySelector('.pixelpet, .asset-pet');
    if (old) old.remove();
    screen.appendChild(buildPixelPet(pcDraft));
  }

  function showPetCreator(pet) {
    // Префилл из существующего питомца (на случай повторной настройки).
    pcDraft.name = pet.name && pet.name !== 'Питомец' ? pet.name : 'Кодзи';
    const choices = randomStarterCharacters(pet.species);
    pcDraft.species = CHARACTER_INDEX[pet.species] ? pet.species : choices[0].id;
    pcDraft.body_color = pet.body_color || '#9dbf9b';
    pcDraft.accent_color = pet.accent_color || '#b08a9e';
    $('#pcName').value = pcDraft.name;

    $('#pcSpecies').innerHTML = choices.map(
      (c) => `<div class="species-opt character-choice ${c.id === pcDraft.species ? 'on' : ''}" data-species="${c.id}">
        <div class="character-choice-preview">${characterImage(c.id, c.name)}</div>
        <div>${esc(c.name)}</div>
      </div>`,
    ).join('');

    $('#app').style.display = 'none';
    $('#onboard').classList.remove('on');
    $('#petcreate').classList.add('on');
    pcPreview();
  }

  $('#pcName').addEventListener('input', () => {
    pcDraft.name = $('#pcName').value;
  });

  // Выбор вида/цветов (делегирование внутри pet-creator).
  $('#petcreate').addEventListener('click', (e) => {
    const sp = e.target.closest('[data-species]');
    if (sp) {
      pcDraft.species = sp.dataset.species;
      $$('#pcSpecies .species-opt').forEach((x) => x.classList.toggle('on', x === sp));
      pcPreview();
      return;
    }
  });

  $('#pcSaveBtn').addEventListener('click', async () => {
    const name = $('#pcName').value.trim();
    if (name.length < 1) return setObError('pc_name', 'Введите имя питомца');
    setObError('pc_name', '');
    const btn = $('#pcSaveBtn');
    btn.disabled = true;
    try {
      const pet = await api.put('/pets/me', { ...pcDraft, name });
      state.pet = pet;
      state.prevXp = pet.xp;
      toast(`${pet.name} готов!`, 'xp');
      launchApp();
    } catch (err) {
      setObError('pc_name', err.message || 'Не удалось сохранить');
    } finally {
      btn.disabled = false;
    }
  });

  function renderWorkspacePicker() {
    const sel = $('#wsPick');
    sel.innerHTML = state.workspaces
      .map((w) => `<option value="${w.id}">${esc(w.name)}</option>`)
      .join('');
    sel.value = state.wsId;
    sel.onchange = () => {
      state.wsId = sel.value;
      go('dashboard');
    };
  }

  $('#newWsBtn').addEventListener('click', async () => {
    const name = prompt('Название новой лаборатории:');
    if (!name || name.trim().length < 2) return;
    const ws = await api.post('/workspaces', { name: name.trim() });
    state.workspaces.push(ws);
    state.wsId = ws.id;
    renderWorkspacePicker();
    toast('Лаборатория создана', 'xp');
    go('lab');
  });

  /* ---------------- laboratory (members + invite code + roles) ---------------- */
  const ROLE_OPTIONS = ['OWNER', 'ADMIN', 'PROJECT_LEAD', 'EDITOR', 'MEMBER', 'VIEWER'];
  const ADMIN_ROLES = new Set(['OWNER', 'ADMIN']);
  const ELEVATED_ROLES = new Set(['OWNER', 'ADMIN', 'PROJECT_LEAD', 'EDITOR']);

  async function renderLab() {
    const ws = state.workspaces.find((w) => w.id === state.wsId);
    if (!ws) return;
    $('#labName').textContent = ws.name;

    const members = await api.get(`/workspaces/${state.wsId}/members`);
    const meId = state.me.id;
    const my = members.find((m) => m.user_id === meId);
    const myRole = my ? my.role : 'MEMBER';
    state.myRole = myRole;
    const canManage = ADMIN_ROLES.has(myRole);

    $('#labRole').textContent = `ваша роль: ${myRole} · ${members.length} участник(ов)`;
    $('#memberCount').textContent = `${members.length}`;

    // Код приглашения видят только OWNER/ADMIN.
    const inviteCard = $('#inviteCard');
    if (canManage && ws.join_code) {
      inviteCard.style.display = '';
      $('#joinCode').textContent = ws.join_code;
    } else {
      inviteCard.style.display = 'none';
    }

    $('#memberBody').innerHTML = members
      .map((m) => {
        const isSelf = m.user_id === meId;
        const isOwner = m.role === 'OWNER';
        const name = esc(m.display_name || m.user_id.slice(0, 8));
        const email = esc(m.email || '');
        // OWNER/ADMIN могут менять роли всем, кроме владельца и себя.
        const editable = canManage && !isOwner && !isSelf;
        const roleCell = editable
          ? `<select class="rolepick" data-role-of="${m.user_id}">${ROLE_OPTIONS.map(
              (r) => `<option ${r === m.role ? 'selected' : ''}>${r}</option>`,
            ).join('')}</select>`
          : `<span class="tag ptype">${m.role}</span>`;
        const action =
          editable
            ? `<span class="chip danger btn-like" data-remove-member="${m.user_id}">удалить</span>`
            : '';
        return `<tr>
          <td><div class="row"><div class="avatar hatch">${initials(m.display_name || '?')}</div>
            <div><b>${name}</b>${isSelf ? ' <span class="mono">(вы)</span>' : ''}<div class="mono">${email}</div></div></div></td>
          <td>${roleCell}</td>
          <td>${action}</td>
        </tr>`;
      })
      .join('');

    $('#roleHint').style.display = canManage ? '' : 'none';
  }

  $('#copyCodeBtn').addEventListener('click', async () => {
    const code = $('#joinCode').textContent.trim();
    try {
      await navigator.clipboard.writeText(code);
      toast('Код скопирован', 'xp');
    } catch {
      toast('Код: ' + code, '');
    }
  });

  // Добавление участника по email.
  $('#inviteBtn').addEventListener('click', async () => {
    const email = $('#inviteEmail').value.trim();
    const role = $('#inviteRole').value;
    $('#inviteErr').textContent = '';
    if (!email) return;
    try {
      await api.post(`/workspaces/${state.wsId}/invite`, { email, role });
      $('#inviteEmail').value = '';
      toast('Участник добавлен', 'xp');
      renderLab();
    } catch (err) {
      $('#inviteErr').textContent =
        err.status === 404 ? 'Нет пользователя с таким email (он должен зарегистрироваться)' : (err.message || 'Не удалось добавить');
    }
  });

  // Смена роли участника.
  document.addEventListener('change', async (e) => {
    const sel = e.target.closest('[data-role-of]');
    if (!sel) return;
    const uid = sel.dataset.roleOf;
    try {
      await api.patch(`/workspaces/${state.wsId}/members/${uid}`, { role: sel.value });
      toast('Роль обновлена', 'xp');
    } catch (err) {
      toast(err.message || 'Не удалось изменить роль', '');
      renderLab();
    }
  });

  // Удаление участника.
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-remove-member]');
    if (!btn) return;
    if (!confirm('Удалить участника из лаборатории?')) return;
    try {
      await api.del(`/workspaces/${state.wsId}/members/${btn.dataset.removeMember}`);
      toast('Участник удалён', '');
      renderLab();
    } catch (err) {
      toast(err.message || 'Не удалось удалить', '');
    }
  });

  /* ---------------- pixel pet sprites ---------------- */
  // Каждый вид — сетка 10×9: b=тело, s=тень, e=глаз, m=рот/акцент, .=пусто.
  const PET_SHAPES = {
    capybara: ['...bbbb...', '.bbbbbbbb.', 'bbbbbbbbbb', 'bbebbbbebb', 'bbebbbbebb', 'bbbbbbbbbb', 'bbbbmmbbbb', '.bbbbbbbb.', '..bb..bb..'],
    cat:      ['b........b', 'bb......bb', 'bbbbbbbbbb', 'bebbbbbbeb', 'bbbbbbbbbb', 'bbbmmmmbbb', 'bbbbbbbbbb', '.bbbbbbbb.', '..b.bb.b..'],
    dog:      ['bb......bb', 'bb......bb', 'bbbbbbbbbb', 'bebbbbbbeb', 'bbbbbbbbbb', 'bbbbmmbbbb', 'bbbmmmmbbb', '.bbbbbbbb.', '..bb..bb..'],
    frog:     ['.e.....e..', 'beb...beb.', 'bbbbbbbbbb', 'bbbbbbbbbb', 'bbbbbbbbbb', 'bmmmmmmmmb', 'bbbbbbbbbb', '.bbbbbbbb.', 'b.b....b.b'],
    axolotl:  ['s..bbbb..s', 'sbbbbbbbbs', 'bbbbbbbbbb', 'bebbbbbbeb', 'bbbbbbbbbb', 'bbbmmmmbbb', 'bbbbbbbbbb', '.bbbbbbbb.', '..b....b..'],
  };

  function buildPixelPet(pet) {
    if (CHARACTER_INDEX[pet.species]) {
      const el = document.createElement('div');
      el.className = 'pixelpet asset-pet idle';
      el.innerHTML = characterImage(pet.species, CHARACTER_INDEX[pet.species].name);
      return el;
    }
    const rows = PET_SHAPES[pet.species] || PET_SHAPES.capybara;
    const el = document.createElement('div');
    el.className = 'pixelpet idle';
    el.style.setProperty('--pp-body', pet.body_color || '#9dbf9b');
    el.style.setProperty('--pp-mouth', pet.accent_color || '#b08a9e');
    // Тень — затемнённое тело.
    el.style.setProperty('--pp-shade', shade(pet.body_color || '#d99a52', -0.25));
    const frag = document.createDocumentFragment();
    rows.join('').split('').forEach((ch) => {
      const i = document.createElement('i');
      if (ch === 'b') i.className = 'b';
      else if (ch === 'e') i.className = 'e';
      else if (ch === 'm') i.className = 'm';
      else if (ch === 's') i.className = 's';
      frag.appendChild(i);
    });
    el.appendChild(frag);
    return el;
  }

  // Затемнить/осветлить hex-цвет.
  function shade(hex, amt) {
    const n = parseInt(hex.slice(1), 16);
    const clamp = (v) => Math.max(0, Math.min(255, Math.round(v)));
    const r = clamp(((n >> 16) & 255) * (1 + amt));
    const g = clamp(((n >> 8) & 255) * (1 + amt));
    const b = clamp((n & 255) * (1 + amt));
    return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
  }

  // id предмета -> объект из каталога (заполняется при загрузке магазина).
  const SHOP_INDEX = {};
  const STATE_ICON = { happy: 'happy', ok: 'ok', sad: 'sad', hungry: 'hungry', sleepy: 'sleepy' };
  const PET_EMOTES = {
    alert: 'alert',
    angry: 'angry',
    annoyed: 'annoyed',
    dizzy: 'dizzy',
    happy: 'happy',
    heart: 'heart',
    heart2: 'heart2',
    idea: 'idea',
    music: 'music',
    ok: 'smile2',
    sad: 'tear',
    skull: 'skull',
    sleepy: 'sleep',
    sleep: 'sleep',
    sleepy_face: 'sleepy_face',
    smile2: 'smile2',
    sparkle: 'sparkle',
    star: 'star',
    tear: 'tear',
  };

  function itemIcon(it) {
    if (it?.type === 'food' && it.data?.icon) return it.data.icon;
    return it?.id || '';
  }

  function hatAssetSrc(it) {
    if (it?.type !== 'hat' || typeof it.data !== 'string' || !/\.png$/i.test(it.data)) return '';
    return `assets/hats/${it.data}`;
  }

  function hatImg(it, className = 'hat-icon') {
    const src = hatAssetSrc(it);
    return src
      ? `<img class="${className}" src="${esc(src)}" alt="${esc(it.name || '')}">`
      : iconImg(itemIcon(it), it.name, 'lg');
  }

  function emoteImg(name, alt = '') {
    const file = PET_EMOTES[name];
    return file ? `<img class="pet-emote-img" src="assets/emotes/${file}.png" alt="${esc(alt || name)}">` : '';
  }

  function stateEmote(pet) {
    if (!pet) return 'ok';
    if (pet.state === 'hungry') return 'alert';
    if (pet.state === 'sleepy') return 'sleep';
    if (pet.state === 'sad') return 'tear';
    if (pet.state === 'happy') return 'happy';
    return 'smile2';
  }

  function showPetEmote(container, name, mode = 'state') {
    if (!container || !PET_EMOTES[name]) return;
    const bubble = document.createElement('div');
    bubble.className = `pet-emote ${mode === 'burst' ? 'burst' : 'state-emote'}`;
    bubble.innerHTML = emoteImg(name, name);
    container.appendChild(bubble);
    if (mode === 'burst') setTimeout(() => bubble.remove(), 1300);
  }

  function fitHatToPet(screen, pet, hat) {
    const c = CHARACTER_INDEX[pet.species];
    if (!screen || !hat || !c) return;
    const isDock = screen.id === 'dockPetScreen';
    const isBig = !isDock && !!screen.closest('.petbig');
    const uiScale = isDock ? 1.8 : (isBig ? 2.8 : 2.35);
    const hatSize = isDock ? 52 : (isBig ? 78 : 64);
    const scale = Number(c.hatScale || 1);
    const frameWidth = Number(c.frameWidth || 32);
    const frameHeight = Number(c.frameHeight || 32);
    const spriteScale = (32 / frameHeight) * uiScale;
    const spriteHeight = frameHeight * spriteScale;
    const spriteTop = screen.clientHeight / 2 - spriteHeight / 2;
    const headTop = spriteTop + Number(c.opaqueTop || 0) * spriteScale;
    const headX = screen.clientWidth / 2
      + (Number(c.opaqueCenter || frameWidth / 2) - frameWidth / 2) * spriteScale;
    const hatOpaqueBottom = hatSize * 0.68 * scale;
    const top = headTop - hatOpaqueBottom + 5 * spriteScale;

    hat.style.setProperty('--pet-hat-left', `${Math.round(headX)}px`);
    hat.style.setProperty('--pet-hat-top', `${Math.round(top)}px`);
    hat.style.setProperty('--pet-hat-scale', String(scale));
    // hatFlip:true зеркалит шапку для персонажей, смотрящих в другую сторону.
    hat.style.setProperty('--pet-hat-flip', c.hatFlip ? '-1' : '1');
  }

  // Перерисовать спрайт во всех экранах-«дисплеях» с учётом состояния + экипировки.
  function paintSprites(pet) {
    const eq = pet.equipped || {};
    const hatItem = eq.hat && SHOP_INDEX[eq.hat];
    const bgItem = eq.bg && SHOP_INDEX[eq.bg];
    $$('.petscreen').forEach((screen) => {
      screen.querySelector('.pixelpet')?.remove();
      screen.querySelector('.pet-hat')?.remove();
      screen.querySelectorAll('.pet-emote.state-emote').forEach((el) => el.remove());
      // фон из экипировки (если есть) — иначе сбрасываем к стилю по умолчанию
      screen.style.background = bgItem ? bgItem.data : '';
      const sprite = buildPixelPet(pet);
      if (pet.state) sprite.classList.add('state-' + pet.state);
      screen.appendChild(sprite);
      showPetEmote(screen, stateEmote(pet), 'state');
      // PNG-шапка поверх питомца
      if (hatItem) {
        const hat = document.createElement('div');
        hat.className = 'pet-hat';
        const src = hatAssetSrc(hatItem);
        if (src) {
          const img = document.createElement('img');
          img.className = 'pet-hat-img';
          img.src = src;
          img.alt = hatItem.name || '';
          hat.appendChild(img);
        } else {
          hat.appendChild(iconNode(itemIcon(hatItem), 'lg'));
        }
        fitHatToPet(screen, pet, hat);
        screen.appendChild(hat);
      }
    });
  }

  function initSidebarControls() {
    const app = $('#app');
    const toggle = $('#menuToggle');
    const sidebar = $('#sidebar');
    const overlay = $('#sideOverlay');
    const collapseBtn = $('#sideCollapse');
    if (app && app.dataset.sidebarReady === '1') return;
    if (app) app.dataset.sidebarReady = '1';

    const isMobile = () => window.matchMedia('(max-width: 900px)').matches;
    const closeSide = () => {
      sidebar && sidebar.classList.remove('open');
      overlay && overlay.classList.remove('on');
      document.body.style.overflow = '';
    };
    const openSide = () => {
      if (!sidebar || !overlay) return;
      sidebar.classList.add('open');
      overlay.classList.add('on');
      document.body.style.overflow = 'hidden';
    };

    if (toggle && sidebar && overlay) {
      toggle.addEventListener('click', (e) => {
        e.preventDefault();
        sidebar.classList.contains('open') ? closeSide() : openSide();
      });
      overlay.addEventListener('click', closeSide);
      $$('#nav a').forEach((a) => a.addEventListener('click', () => {
        if (isMobile()) closeSide();
      }));
    }

    if (collapseBtn && app) {
      try {
        app.classList.toggle(
          'side-collapsed',
          localStorage.getItem('petpro_side_collapsed') === '1' && !isMobile(),
        );
      } catch (e) {}
      collapseBtn.addEventListener('click', (e) => {
        e.preventDefault();
        if (isMobile()) {
          closeSide();
          return;
        }
        const collapsed = app.classList.toggle('side-collapsed');
        try { localStorage.setItem('petpro_side_collapsed', collapsed ? '1' : '0'); } catch (e) {}
      });
    }

    window.addEventListener('resize', () => {
      const repaintPet = () => state.pet && requestAnimationFrame(() => paintSprites(state.pet));
      if (isMobile()) {
        app && app.classList.remove('side-collapsed');
        repaintPet();
        return;
      }
      closeSide();
      try {
        app && app.classList.toggle('side-collapsed', localStorage.getItem('petpro_side_collapsed') === '1');
      } catch (e) {}
      repaintPet();
    });
  }

  /* ---------------- pet ---------------- */
  function levelOf(xp) {
    return Math.floor(xp / 100) + 1;
  }
  function paintPet(pet) {
    const lvl = levelOf(pet.xp);
    const into = pet.xp - (lvl - 1) * 100;
    $$('[data-petname]').forEach((e) => (e.textContent = pet.name));
    $$('[data-petlevel]').forEach((e) => (e.textContent = lvl));
    $$('[data-petlevelnext]').forEach((e) => (e.textContent = lvl + 1));
    $$('[data-petfill]').forEach((e) => (e.style.width = into + '%'));
    $$('[data-petnum]').forEach((e) => (e.textContent = `${into}/100`));
    const set = (sel, v) => $$(sel).forEach((e) => (e.style.width = v + '%'));
    const num = (sel, v) => $$(sel).forEach((e) => (e.textContent = v));
    set('[data-petmood]', pet.mood); num('[data-petmoodnum]', pet.mood);
    set('[data-pethunger]', pet.hunger); num('[data-pethungernum]', pet.hunger);
    set('[data-petenergy]', pet.energy); num('[data-petenergynum]', pet.energy);
    $$('[data-petenergyhint]').forEach((e) => {
      const energy = Number(pet.energy || 0);
      e.textContent = energy < 80
        ? 'Энергия от времени не растёт сама: работа даёт +6, а сон быстро восстановит её до 100.'
        : 'Энергия тратится на игры и падает примерно на 3 в час. Сон станет доступен, когда питомец устанет ниже 80.';
    });
    // Подпись состояния (тамагочи).
    const stateIcon = STATE_ICON[pet.state];
    $$('[data-petstate]').forEach((e) => {
      e.innerHTML = stateIcon ? iconLabel(stateIcon, pet.state_label || '') : esc(pet.state_label || '');
    });
    $$('[data-petstate-mini]').forEach((e) => {
      e.innerHTML = stateIcon ? iconImg(stateIcon, pet.state || '') : '';
    });
    // Монеты (для дока и комнаты игр).
    $$('[data-petcoins]').forEach((e) => (e.innerHTML = iconLabel('coin', String(pet.coins || 0))));
    $('#coinBalance') && ($('#coinBalance').innerHTML = iconLabel('coin', String(pet.coins || 0)));
    paintSprites(pet);
    renderBackpack();
    renderFoodBags();
    updatePlayControls();
  }
  async function refreshPet() {
    const pet = await api.get('/pets/me');
    if (state.prevXp !== null && pet.xp > state.prevXp) {
      const diff = pet.xp - state.prevXp;
      const leveled = levelOf(pet.xp) > levelOf(state.prevXp);
      toast(leveled ? `Уровень ${levelOf(pet.xp)}! +${diff} XP` : `+${diff} XP`, leveled ? 'lvl' : 'xp');
    }
    // Подсказки-«тамагочи»: если питомцу плохо — мягко напоминаем поработать.
    if (state.prevState && pet.state !== state.prevState) {
      if (pet.state === 'hungry') toast('Питомец проголодался - закрой задачу', '');
      else if (pet.state === 'sad') toast('Питомец загрустил без работы', '');
      else if (pet.state === 'sleepy') toast('Питомцу нужен отдых', '');
      else if (pet.state === 'happy') toast('Питомец доволен!', 'xp');
    }
    state.prevState = pet.state;
    state.prevXp = pet.xp;
    state.pet = pet;
    paintPet(pet);
  }

  // inline-переименование питомца (без prompt-окна)
  function openPetNameEdit() {
    $('#petNameInput').value = state.pet ? state.pet.name : '';
    $('#petNameDisplay').style.display = 'none';
    $('#renamePetBtn').style.display = 'none';
    $('#petNameEdit').style.display = 'flex';
    $('#petNameInput').focus();
  }
  function closePetNameEdit() {
    $('#petNameEdit').style.display = 'none';
    $('#petNameDisplay').style.display = '';
    $('#renamePetBtn').style.display = '';
  }
  async function savePetName() {
    const name = $('#petNameInput').value.trim();
    if (!name) return;
    await api.patch('/pets/me', { name });
    await refreshPet();
    closePetNameEdit();
    toast('Имя обновлено', 'xp');
  }

  $('#renamePetBtn').addEventListener('click', openPetNameEdit);
  $('#petNameSave').addEventListener('click', savePetName);
  $('#petNameCancel').addEventListener('click', closePetNameEdit);
  $('#petNameInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') savePetName();
    if (e.key === 'Escape') closePetNameEdit();
  });

  /* ---------------- task rendering ---------------- */
  function taskRow(t) {
    const personal = t.scope === 'PERSONAL';
    const done = t.status === 'DONE';
    return `<div class="task ${personal ? 'priv' : ''} ${done ? 'done' : ''}" data-task="${t.id}">
      <div class="prio ${t.priority}"></div>
      <div class="chk ${done ? 'done' : ''}" data-toggle="${t.id}"></div>
      <div class="t" data-open-task="${t.id}" style="cursor:pointer;">${esc(t.title)} <span class="tag">${t.type}</span></div>
      ${done ? `<span class="chip ${personal ? 'priv' : 'xp'}">+${personal ? 5 : 10} XP</span>` : (t.due_date ? `<span class="chip">${t.due_date}</span>` : '')}
    </div>`;
  }

  async function toggleTask(id, currentlyDone) {
    try {
      await api.patch(`/tasks/${id}/${currentlyDone ? 'reopen' : 'complete'}`, {});
      await refreshPet();
    } catch (err) {
      toast(err.message, '');
    }
  }

  // delegated checkbox toggle
  document.addEventListener('click', async (e) => {
    const chk = e.target.closest('[data-toggle]');
    if (!chk) return;
    const row = chk.closest('.task');
    await toggleTask(chk.dataset.toggle, row.classList.contains('done'));
    // re-render whichever screen is active
    const active = $('.screen.on');
    if (active) go(active.id.replace('screen-', ''));
  });

  /* ---------------- dashboard ---------------- */
  async function renderDashboard() {
    $('#dashHi').textContent = `Привет, ${state.me.display_name.split(' ')[0]}`;
    const ws = state.workspaces.find((w) => w.id === state.wsId);
    $('#dashSub').textContent = ws ? ws.name : '';
    await refreshPet();
    await refreshDashboardLive();
  }

  async function refreshDashboardLive() {
    const [tasks, feed, projects, articles] = await Promise.all([
      api.get('/me/tasks'),
      api.get(`/workspaces/${state.wsId}/activity?limit=15`),
      api.get(`/workspaces/${state.wsId}/projects`),
      api.get(`/workspaces/${state.wsId}/articles`),
    ]);
    state.projects = projects;
    state.articles = articles;
    const open = tasks.filter((t) => t.status !== 'DONE');
    $('#dashTaskCount').textContent = `${open.length} открыто`;
    // на дашборде — только незавершённые; выполненные живут в архиве «Мои задачи»
    $('#dashTasks').innerHTML = open.length
      ? open.slice(0, 8).map(taskRow).join('')
      : '<div class="muted sm">Открытых задач нет — создайте на «Мои задачи».</div>';

    $('#dashFeed').innerHTML = feed.length
      ? feed.map(feedRow).join('')
      : '<div class="muted sm">Пока тихо.</div>';
    renderDashboardWidgets(tasks, projects, articles);
  }

  function renderDashboardWidgets(tasks, projects, articles) {
    const dated = tasks
      .filter((t) => t.due_date && t.status !== 'DONE')
      .sort((a, b) => a.due_date.localeCompare(b.due_date))
      .slice(0, 5);
    $('#dashDeadlines').innerHTML = dated.length
      ? dated.map((t) => `<div class="task" data-open-task="${t.id}" style="cursor:pointer;">
          <div class="prio ${t.priority}"></div>
          <div class="t">${esc(t.title)} <span class="tag">${t.scope}</span></div>
          <span class="chip">${t.due_date}</span>
        </div>`).join('')
      : '<div class="muted sm">Ближайших дедлайнов нет.</div>';

    const activeProjects = projects.filter((p) => ACTIVE_PROJECT_STATUSES.has(p.status)).slice(0, 5);
    $('#dashProjects').innerHTML = activeProjects.length
      ? activeProjects.map((p) => `<div class="task" data-open-project="${p.id}" style="cursor:pointer;">
          <div class="t">${esc(p.name)}</div><span class="tag ptype">${p.status}</span>
        </div>`).join('')
      : '<div class="muted sm">Активных проектов нет.</div>';

    const activeArticles = articles.filter((a) => ACTIVE_ARTICLE_STATUSES.has(a.status)).slice(0, 5);
    $('#dashArticles').innerHTML = activeArticles.length
      ? activeArticles.map((a) => `<div class="task" data-open-article="${a.id}" style="cursor:pointer;">
          <div class="t">${esc(a.title)}</div><span class="tag ptype">${a.status}</span>
        </div>`).join('')
      : '<div class="muted sm">Статей в работе нет.</div>';
  }

  function feedRow(a) {
    return `<div class="it"><div class="av">${initials(a.actor_id.slice(0, 2))}</div>
      <div><span>${esc(a.text)}</span><div class="when">${new Date(a.created_at).toLocaleString('ru')}</div></div></div>`;
  }

  /* ---------------- projects ---------------- */
  function statusSelect(kind, id, current, statuses) {
    const opts = statuses.map((s) => `<option ${s === current ? 'selected' : ''}>${s}</option>`).join('');
    return `<select class="rolepick" data-status="${kind}:${id}">${opts}</select>`;
  }

  async function renderProjects() {
    const projects = await api.get(`/workspaces/${state.wsId}/projects`);
    state.projects = projects;
    const board = $('#projectBoard');
    board.innerHTML = PROJECT_STATUSES.map((st) => {
      const inCol = projects.filter((p) => p.status === st);
      const cards = inCol
        .map(
          (p) => `<div class="acard soft">
            <div class="row"><span class="tag ptype">${p.type}</span></div>
            <div class="ttl" data-open-project="${p.id}" style="cursor:pointer;">${esc(p.name)}</div>
            ${statusSelect('project', p.id, p.status, PROJECT_STATUSES)}
          </div>`,
        )
        .join('');
      return `<div class="colm"><div class="colhead soft"><b>${st}</b><span class="cnt">${inCol.length}</span></div>${cards}</div>`;
    }).join('');
  }

  $('#newProjectBtn').addEventListener('click', async () => {
    const name = $('#projName').value.trim();
    if (!name) return;
    const desc = $('#projDescNew').value.trim();
    const body = {
      name,
      type: $('#projType').value,
      status: $('#projStatusNew').value,
      ...(desc && { description: desc }),
    };
    await api.post(`/workspaces/${state.wsId}/projects`, body);
    $('#projName').value = '';
    $('#projDescNew').value = '';
    toast('Проект создан', 'xp');
    renderProjects();
  });

  /* ---------------- articles ---------------- */
  async function renderArticles() {
    const articles = await api.get(`/workspaces/${state.wsId}/articles`);
    $('#articleList').innerHTML = articles.length
      ? articles
          .map(
            (a) => `<div class="card sk2" style="cursor:pointer;" data-open-article="${a.id}"><div class="between">
              <div><b>${esc(a.title)}</b>${a.target_journal ? ` <span class="mono">· ${esc(a.target_journal)}</span>` : ''}</div>
              <span class="tag ptype">${a.status}</span>
            </div></div>`,
          )
          .join('')
      : '<div class="muted sm">Статей пока нет.</div>';
  }

  $('#newArticleBtn').addEventListener('click', async () => {
    const title = $('#artTitle').value.trim();
    if (!title) return;
    const desc = $('#artDescNew').value.trim();
    const journal = $('#artJournalNew').value.trim();
    const body = {
      title,
      ...(desc && { description: desc }),
      ...(journal && { target_journal: journal }),
    };
    await api.post(`/workspaces/${state.wsId}/articles`, body);
    $('#artTitle').value = '';
    $('#artDescNew').value = '';
    $('#artJournalNew').value = '';
    toast('Статья создана', 'xp');
    renderArticles();
  });

  /* ---------------- detail: project ---------------- */
  function statusOptions(current, statuses) {
    return statuses.map((s) => `<option ${s === current ? 'selected' : ''}>${s}</option>`).join('');
  }

  async function openProject(id) {
    state.openProject = id;
    go('projdetail');
    const p = await api.get(`/projects/${id}`);
    $('#pdName').textContent = p.name;
    $('#pdMeta').textContent = `${p.type}${p.deadline ? ' · дедлайн ' + p.deadline : ''}`;
    $('#pdDesc').textContent = p.description || 'Без описания';
    const sel = $('#pdStatus');
    sel.innerHTML = statusOptions(p.status, PROJECT_STATUSES);
    sel.dataset.status = `project:${id}`;

    const [tasks, articles] = await Promise.all([
      api.get(`/projects/${id}/tasks`),
      api.get(`/projects/${id}/articles`),
    ]);
    $('#pdTaskCount').textContent = `${tasks.filter((t) => t.status !== 'DONE').length} открыто`;
    $('#pdTasks').innerHTML = tasks.length ? tasks.map(taskRowLinked).join('') : '<div class="muted sm">Нет задач.</div>';
    $('#pdArticles').innerHTML = articles.length
      ? articles.map((a) => `<div class="task" data-open-article="${a.id}" style="cursor:pointer;"><div class="t">${esc(a.title)}</div><span class="tag ptype">${a.status}</span></div>`).join('')
      : '<div class="muted sm">Нет статей.</div>';

    renderMemberManager('project', id, p.workspace_id);
    mountComments('project', id);
  }

  $('#pdAddTask').addEventListener('click', async () => {
    const title = $('#pdNewTask').value.trim();
    if (!title) return;
    const due = $('#pdNewTaskDue').value;
    const body = { scope: 'PROJECT', project_id: state.openProject, title, ...(due && { due_date: due }) };
    try {
      await api.post('/tasks', body);
      $('#pdNewTask').value = '';
      $('#pdNewTaskDue').value = '';
      toast('Задача добавлена', 'xp');
      openProject(state.openProject);
    } catch (err) {
      toast(err.message, '');
    }
  });

  /* ---------------- detail: article ---------------- */
  async function openArticle(id) {
    state.openArticle = id;
    go('artdetail');
    const a = await api.get(`/articles/${id}`);
    $('#adTitle').textContent = a.title;
    $('#adMeta').textContent = a.status;
    $('#adDesc').textContent = a.description || 'Без описания';
    const fields = [];
    if (a.target_journal) fields.push(`журнал: ${esc(a.target_journal)}`);
    if (a.document_url) fields.push(`<a href="${esc(a.document_url)}" target="_blank" style="color:var(--accent)">документ ↗</a>`);
    if (a.deadline) fields.push(`дедлайн: ${a.deadline}`);
    $('#adFields').innerHTML = fields.join(' · ');
    const sel = $('#adStatus');
    sel.innerHTML = statusOptions(a.status, ARTICLE_STATUSES);
    sel.dataset.status = `article:${id}`;

    const own = await api.get(`/articles/${id}/tasks`).catch(() => []);
    $('#adTaskCount').textContent = `${own.length}`;
    $('#adTasks').innerHTML = own.length ? own.map(taskRowLinked).join('') : '<div class="muted sm">Нет задач статьи.</div>';

    renderMemberManager('article', id, a.workspace_id);
    mountComments('article', id);
  }

  $('#adAddTask').addEventListener('click', async () => {
    const title = $('#adNewTask').value.trim();
    if (!title) return;
    const due = $('#adNewTaskDue').value;
    const body = { scope: 'ARTICLE', article_id: state.openArticle, title, ...(due && { due_date: due }) };
    try {
      await api.post('/tasks', body);
      $('#adNewTask').value = '';
      $('#adNewTaskDue').value = '';
      toast('Задача добавлена', 'xp');
      openArticle(state.openArticle);
    } catch (err) {
      toast(err.message, '');
    }
  });

  /* ---------------- project/article members ---------------- */
  const MEMBER_CONFIG = {
    project: {
      roles: PROJECT_ROLES,
      path: (id) => `/projects/${id}/members`,
    },
    article: {
      roles: ARTICLE_ROLES,
      path: (id) => `/articles/${id}/members`,
    },
  };

  async function renderMemberManager(kind, entityId, workspaceId) {
    const cfg = MEMBER_CONFIG[kind];
    const box = $(`.memberbox[data-members="${kind}"]`);
    if (!cfg || !box) return;
    box.dataset.id = entityId;
    const list = box.querySelector('[data-member-list]');
    const userSel = box.querySelector('[data-member-user]');
    const roleSel = box.querySelector('[data-member-role]');
    const addBtn = box.querySelector('[data-member-add]');
    list.innerHTML = '<div class="ph" style="height:44px;">загрузка…</div>';

    try {
      const [workspaceMembers, entityMembers] = await Promise.all([
        api.get(`/workspaces/${workspaceId}/members`),
        api.get(cfg.path(entityId)),
      ]);
      state.members = workspaceMembers;
      const my = workspaceMembers.find((m) => m.user_id === state.me.id);
      const canManage = !!my && ELEVATED_ROLES.has(my.role);

      userSel.innerHTML = workspaceMembers
        .map((m) => `<option value="${m.user_id}">${esc(m.display_name || m.email || m.user_id.slice(0, 8))}</option>`)
        .join('');
      roleSel.innerHTML = cfg.roles.map((r) => `<option>${r}</option>`).join('');
      userSel.disabled = !canManage;
      roleSel.disabled = !canManage;
      addBtn.disabled = !canManage;
      addBtn.style.display = canManage ? '' : 'none';

      list.innerHTML = entityMembers.length
        ? `<table class="tbl"><tbody>${entityMembers.map((m) => {
            const roleCell = canManage
              ? `<select class="rolepick" data-member-role-of="${m.user_id}" data-kind="${kind}" data-entity-id="${entityId}">
                  ${cfg.roles.map((r) => `<option ${r === m.role ? 'selected' : ''}>${r}</option>`).join('')}
                </select>`
              : `<span class="tag ptype">${m.role}</span>`;
            const remove = canManage
              ? `<span class="chip danger btn-like" data-remove-entity-member="${m.user_id}" data-kind="${kind}" data-entity-id="${entityId}">удалить</span>`
              : '';
            return `<tr>
              <td><div class="row"><div class="avatar hatch">${initials(m.display_name || '?')}</div>
                <div><b>${esc(m.display_name || m.user_id.slice(0, 8))}</b><div class="mono">${esc(m.email || '')}</div></div></div></td>
              <td>${roleCell}</td>
              <td>${remove}</td>
            </tr>`;
          }).join('')}</tbody></table>`
        : '<div class="muted sm">Участников пока нет.</div>';
    } catch {
      list.innerHTML = '<div class="muted sm">Не удалось загрузить участников.</div>';
    }
  }

  document.addEventListener('click', async (e) => {
    const add = e.target.closest('[data-member-add]');
    if (!add) return;
    const box = add.closest('.memberbox');
    const kind = box.dataset.members;
    const id = box.dataset.id;
    const cfg = MEMBER_CONFIG[kind];
    const user_id = box.querySelector('[data-member-user]').value;
    const role = box.querySelector('[data-member-role]').value;
    if (!user_id || !role) return;
    add.disabled = true;
    try {
      await api.post(cfg.path(id), { user_id, role });
      toast('Участник обновлён', 'xp');
      const entity = kind === 'project' ? await api.get(`/projects/${id}`) : await api.get(`/articles/${id}`);
      renderMemberManager(kind, id, entity.workspace_id);
    } catch (err) {
      toast(err.message || 'Не удалось обновить участника', '');
    } finally {
      add.disabled = false;
    }
  });

  document.addEventListener('change', async (e) => {
    const sel = e.target.closest('[data-member-role-of]');
    if (!sel) return;
    const kind = sel.dataset.kind;
    const id = sel.dataset.entityId;
    const cfg = MEMBER_CONFIG[kind];
    try {
      await api.post(cfg.path(id), { user_id: sel.dataset.memberRoleOf, role: sel.value });
      toast('Роль обновлена', 'xp');
    } catch (err) {
      toast(err.message || 'Не удалось изменить роль', '');
      const entity = kind === 'project' ? await api.get(`/projects/${id}`) : await api.get(`/articles/${id}`);
      renderMemberManager(kind, id, entity.workspace_id);
    }
  });

  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-remove-entity-member]');
    if (!btn) return;
    if (!confirm('Удалить участника?')) return;
    const kind = btn.dataset.kind;
    const id = btn.dataset.entityId;
    const cfg = MEMBER_CONFIG[kind];
    try {
      await api.del(`${cfg.path(id)}/${btn.dataset.removeEntityMember}`);
      toast('Участник удалён', '');
      const entity = kind === 'project' ? await api.get(`/projects/${id}`) : await api.get(`/articles/${id}`);
      renderMemberManager(kind, id, entity.workspace_id);
    } catch (err) {
      toast(err.message || 'Не удалось удалить', '');
    }
  });

  /* ---------------- detail: task ---------------- */
  async function openTask(id) {
    state.openTask = id;
    go('taskdetail');
    const t = await api.get(`/tasks/${id}`);
    state.openTaskObj = t;
    // участники нужны, чтобы показать имена исполнителей и кто выполнил
    if (t.scope !== 'PERSONAL' && (!state.members || !state.members.length)) {
      state.members = await api.get(`/workspaces/${state.wsId}/members`).catch(() => []);
    }
    $('#tdTitle').textContent = t.title;
    const parts = [t.scope, t.type, t.status];
    if (t.due_date) parts.push('до ' + t.due_date);
    const who = (t.assignees && t.assignees.length ? t.assignees : (t.assignee_id ? [t.assignee_id] : []));
    if (who.length) parts.push('исполнители: ' + who.map(memberName).join(', '));
    if (t.status === 'DONE' && t.completed_by) parts.push('✓ выполнил: ' + memberName(t.completed_by));
    $('#tdMeta').textContent = parts.join(' · ');
    $('#tdDesc').textContent = t.description || 'Без описания';
    $('#tdToggle').textContent = t.status === 'DONE' ? 'Переоткрыть' : 'Закрыть задачу';
    $('#tdEditCard').hidden = true;
    renderTaskEditForm(t);
    mountComments('task', id);
  }

  function optionList(values, current) {
    return values
      .map((v) => `<option value="${v}" ${v === current ? 'selected' : ''}>${v}</option>`)
      .join('');
  }

  function renderTaskEditForm(t) {
    $('#tdEditTitle').value = t.title || '';
    $('#tdEditDesc').value = t.description || '';
    $('#tdEditDue').value = t.due_date || '';
    $('#tdEditType').innerHTML = optionList(TASK_TYPES, t.type || 'OTHER');
    $('#tdEditPriority').innerHTML = optionList(TASK_PRIORITIES, t.priority || 'MEDIUM');

    const wrap = $('#tdEditAssigneesWrap');
    const list = $('#tdEditAssignees');
    if (t.scope === 'PERSONAL') {
      wrap.hidden = true;
      list.innerHTML = '';
      return;
    }

    wrap.hidden = false;
    const selected = new Set(t.assignees && t.assignees.length ? t.assignees : (t.assignee_id ? [t.assignee_id] : []));
    list.innerHTML = (state.members || [])
      .map((m) => {
        const label = esc(m.display_name || m.email || m.user_id.slice(0, 6));
        return `<label class="task-edit-assignee">
          <input type="checkbox" value="${m.user_id}" ${selected.has(m.user_id) ? 'checked' : ''}>
          <span>${label}</span>
        </label>`;
      })
      .join('') || '<div class="muted sm">Нет участников для назначения.</div>';
  }

  $('#tdBack').addEventListener('click', () => go(NAV_PARENT.taskdetail));

  $('#tdEdit').addEventListener('click', () => {
    const card = $('#tdEditCard');
    card.hidden = !card.hidden;
    if (!card.hidden) card.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  $('#tdCancel').addEventListener('click', () => {
    $('#tdEditCard').hidden = true;
    if (state.openTaskObj) renderTaskEditForm(state.openTaskObj);
  });

  $('#tdSave').addEventListener('click', async () => {
    const t = state.openTaskObj;
    if (!t) return;
    const title = $('#tdEditTitle').value.trim();
    if (!title) return toast('Название задачи не может быть пустым', '');

    const desc = $('#tdEditDesc').value.trim();
    const body = {
      title,
      description: desc || null,
      due_date: $('#tdEditDue').value || null,
      type: $('#tdEditType').value,
      priority: $('#tdEditPriority').value,
    };
    if (t.scope !== 'PERSONAL') {
      body.assignee_ids = $$('#tdEditAssignees input[type="checkbox"]:checked').map((x) => x.value);
    }

    const btn = $('#tdSave');
    btn.disabled = true;
    try {
      const updated = await api.patch(`/tasks/${t.id}`, body);
      state.openTaskObj = updated;
      toast('Задача обновлена', 'xp');
      await openTask(t.id);
    } catch (err) {
      toast(err.message || 'Не удалось сохранить', '');
    } finally {
      btn.disabled = false;
    }
  });

  $('#tdToggle').addEventListener('click', async () => {
    const t = state.openTaskObj;
    if (!t) return;
    await toggleTask(t.id, t.status === 'DONE');
    openTask(t.id);
  });

  // Клик по строке задачи → деталь (используется в детальных списках).
  function taskRowLinked(t) {
    const personal = t.scope === 'PERSONAL';
    const done = t.status === 'DONE';
    return `<div class="task ${personal ? 'priv' : ''} ${done ? 'done' : ''}">
      <div class="chk ${done ? 'done' : ''}" data-toggle="${t.id}"></div>
      <div class="t" data-open-task="${t.id}" style="cursor:pointer;">${esc(t.title)} <span class="tag">${t.type}</span></div>
    </div>`;
  }

  /* ---------------- comments (project/article/task) ---------------- */
  // Базовый путь для команды комментариев данной сущности.
  function cmtBase(kind, id) {
    return { project: `/projects/${id}`, article: `/articles/${id}`, task: `/tasks/${id}` }[kind];
  }

  async function mountComments(kind, id) {
    const box = $(`.cmtbox[data-cmt="${kind}"]`);
    if (!box) return;
    const list = box.querySelector('.cmt-list');
    const form = box.querySelector('.cmt-form');
    box.dataset.id = id;

    // подгрузим участников лаборатории для упоминаний
    if (!state.members || !state.members.length) {
      state.members = await api.get(`/workspaces/${state.wsId}/members`).catch(() => []);
    }
    const memberOpts = (state.members || [])
      .map((m) => `<option value="${m.user_id}">${esc(m.display_name || m.email || m.user_id.slice(0, 6))}</option>`)
      .join('');

    form.innerHTML = `
      <textarea class="input" data-cmt-text placeholder="Комментарий…"></textarea>
      <div class="row" style="gap:8px;margin-top:6px;flex-wrap:wrap;align-items:center;">
        <button class="btn primary sm" data-cmt-send>Отправить</button>
        <span class="mono">упомянуть:</span>
        <select class="rolepick" data-cmt-mention>
          <option value="">＠ выбрать…</option>${memberOpts}
        </select>
      </div>
      <div class="row" data-cmt-chips style="gap:6px;margin-top:6px;flex-wrap:wrap;"></div>`;

    box._mentions = [];
    await reloadComments(kind, id, list);
  }

  // отображение имени участника по id
  function memberName(uid) {
    const m = (state.members || []).find((x) => x.user_id === uid);
    return m ? (m.display_name || m.email || uid.slice(0, 6)) : uid.slice(0, 6);
  }

  // выбор упоминания из выпадающего списка
  document.addEventListener('change', (e) => {
    const sel = e.target.closest('[data-cmt-mention]');
    if (!sel || !sel.value) return;
    const box = sel.closest('.cmtbox');
    box._mentions = box._mentions || [];
    if (!box._mentions.includes(sel.value)) {
      box._mentions.push(sel.value);
      renderMentionChips(box);
    }
    sel.value = '';
  });

  function renderMentionChips(box) {
    const wrap = box.querySelector('[data-cmt-chips]');
    if (!wrap) return;
    wrap.innerHTML = (box._mentions || [])
      .map((uid) => `<span class="chip acc btn-like" data-cmt-unmention="${uid}">@${esc(memberName(uid))} ✕</span>`)
      .join('');
  }

  document.addEventListener('click', (e) => {
    const chip = e.target.closest('[data-cmt-unmention]');
    if (!chip) return;
    const box = chip.closest('.cmtbox');
    box._mentions = (box._mentions || []).filter((u) => u !== chip.dataset.cmtUnmention);
    renderMentionChips(box);
  });

  async function reloadComments(kind, id, list) {
    try {
      const items = await api.get(`${cmtBase(kind, id)}/comments`);
      list.innerHTML = items.length
        ? items.map((c) => {
            const nm = memberName(c.author_id);
            return `<div class="feed comment-feed"><div class="it comment-row">
            <div class="av" title="${esc(nm)}">${initials(nm)}</div>
            <div class="comment-body">
              <div class="comment-text">${esc(c.text)}</div>
              <div class="when comment-meta">${esc(nm)} · ${new Date(c.created_at).toLocaleString('ru')}</div>
            </div>
          </div></div>`;
          }).join('')
        : '<div class="muted sm">Пока нет комментариев.</div>';
    } catch {
      list.innerHTML = '<div class="muted sm">Не удалось загрузить.</div>';
    }
  }

  // Делегирование отправки комментария.
  document.addEventListener('click', async (e) => {
    const send = e.target.closest('[data-cmt-send]');
    if (!send) return;
    const box = send.closest('.cmtbox');
    const kind = box.dataset.cmt;
    const id = box.dataset.id;
    const ta = box.querySelector('[data-cmt-text]');
    const text = ta.value.trim();
    if (!text) return;
    send.disabled = true;
    try {
      const mentions = box._mentions || [];
      await api.post(`${cmtBase(kind, id)}/comments`, { text, mention_user_ids: mentions });
      ta.value = '';
      box._mentions = [];
      renderMentionChips(box);
      await reloadComments(kind, id, box.querySelector('.cmt-list'));
      refreshPet();
    } catch (err) {
      toast(err.message || 'Не удалось отправить', '');
    } finally {
      send.disabled = false;
    }
  });

  // Открытие деталей по клику (делегирование).
  document.addEventListener('click', (e) => {
    const p = e.target.closest('[data-open-project]');
    if (p) return openProject(p.dataset.openProject);
    const a = e.target.closest('[data-open-article]');
    if (a) return openArticle(a.dataset.openArticle);
    const t = e.target.closest('[data-open-task]');
    if (t) return openTask(t.dataset.openTask);
  });

  /* status-change delegation (projects + articles) */
  document.addEventListener('change', async (e) => {
    const sel = e.target.closest('[data-status]');
    if (!sel) return;
    const [kind, id] = sel.dataset.status.split(':');
    try {
      await api.patch(`/${kind}s/${id}/status`, { status: sel.value });
      toast('Статус обновлён', 'xp');
      await refreshPet();
      // если меняли из списка проектов — переставить карточку в нужную колонку
      if (kind === 'project' && $('#screen-projects')?.classList.contains('on')) {
        renderProjects();
      }
    } catch (err) {
      toast(err.message, '');
    }
  });

  /* ---------------- my tasks ---------------- */

  // Показ полей в зависимости от scope: проект, исполнитель, дедлайн — только для командных.
  // выбранные исполнители новой задачи
  let taskAssignees = [];
  function renderTaskAssigneeChips() {
    $('#taskAssigneeChips').innerHTML = taskAssignees
      .map((uid) => `<span class="chip acc btn-like" data-task-unassign="${uid}">${esc(memberName(uid))} ✕</span>`)
      .join('');
  }
  document.addEventListener('click', (e) => {
    const chip = e.target.closest('[data-task-unassign]');
    if (!chip) return;
    taskAssignees = taskAssignees.filter((u) => u !== chip.dataset.taskUnassign);
    renderTaskAssigneeChips();
  });
  // выбор исполнителя из списка → добавить чип
  $('#taskAssignee').addEventListener('change', () => {
    const v = $('#taskAssignee').value;
    if (v && !taskAssignees.includes(v)) {
      taskAssignees.push(v);
      renderTaskAssigneeChips();
    }
    $('#taskAssignee').value = '';
  });

  $('#taskScope').addEventListener('change', async () => {
    const scope = $('#taskScope').value;
    const isProj = scope === 'PROJECT';
    const isTeam = scope !== 'PERSONAL';
    $('#taskProject').style.display = isProj ? '' : 'none';
    $('#taskAssigneeWrap').style.display = isTeam ? '' : 'none';
    if (!isTeam) { taskAssignees = []; renderTaskAssigneeChips(); }

    if (isProj) {
      const projects = state.projects.length
        ? state.projects
        : await api.get(`/workspaces/${state.wsId}/projects`);
      state.projects = projects;
      $('#taskProject').innerHTML = projects.map((p) => `<option value="${p.id}">${esc(p.name)}</option>`).join('');
    }
    if (isTeam) {
      const members = await api.get(`/workspaces/${state.wsId}/members`);
      state.members = members;
      $('#taskAssignee').innerHTML =
        '<option value="">＋ добавить исполнителя…</option>' +
        members.map((m) => `<option value="${m.user_id}">${esc(m.display_name || m.email)}</option>`).join('');
    }
  });

  $('#newTaskBtn').addEventListener('click', async () => {
    const title = $('#taskTitle').value.trim();
    if (!title) return;
    const scope = $('#taskScope').value;
    const desc = $('#taskDesc').value.trim();
    const body = { scope, title, ...(desc && { description: desc }) };
    if (scope === 'WORKSPACE') body.workspace_id = state.wsId;
    if (scope === 'PROJECT') {
      const pid = $('#taskProject').value;
      if (!pid) return toast('Сначала создайте проект', '');
      body.project_id = pid;
    }
    if (scope !== 'PERSONAL' && taskAssignees.length) {
      body.assignee_ids = taskAssignees;
    }
    const due = $('#taskDue').value;
    if (due) body.due_date = due;
    try {
      await api.post('/tasks', body);
      $('#taskTitle').value = '';
      $('#taskDesc').value = '';
      $('#taskDue').value = '';
      taskAssignees = [];
      renderTaskAssigneeChips();
      toast('Задача добавлена', scope === 'PERSONAL' ? 'priv' : '');
      renderMyTasks();
    } catch (err) {
      toast(err.message, '');
    }
  });

  // ── фильтры ──
  const taskFilter = { scope: 'all', status: 'all', due: 'all' };

  document.addEventListener('click', (e) => {
    const b = e.target.closest('.filterbar .seg button');
    if (!b) return;
    const seg = b.closest('.seg');
    seg.querySelectorAll('button').forEach((x) => x.classList.toggle('on', x === b));
    taskFilter[seg.dataset.filter] = b.dataset.val;
    applyTaskFilters();
  });

  function taskMatches(t) {
    if (taskFilter.scope === 'team' && t.scope === 'PERSONAL') return false;
    if (taskFilter.scope === 'personal' && t.scope !== 'PERSONAL') return false;
    if (taskFilter.status === 'open' && t.status === 'DONE') return false;
    if (taskFilter.status === 'done' && t.status !== 'DONE') return false;
    if (taskFilter.due !== 'all') {
      if (!t.due_date) return false;
      const today = new Date().toISOString().slice(0, 10);
      if (taskFilter.due === 'overdue' && !(t.due_date < today && t.status !== 'DONE')) return false;
      if (taskFilter.due === 'soon' && t.due_date < today) return false;
    }
    return true;
  }

  function applyTaskFilters() {
    const team = (state.myTasks || []).filter((t) => t.scope !== 'PERSONAL');
    const personal = state.myPersonal || [];
    const ft = team.filter(taskMatches);
    const fp = personal.filter(taskMatches);

    // активные — только не выполненные
    const ftOpen = ft.filter((t) => t.status !== 'DONE');
    const fpOpen = fp.filter((t) => t.status !== 'DONE');
    $('#teamCount').textContent = `${ftOpen.length} открыто`;
    $('#teamTasks').innerHTML = ftOpen.length ? ftOpen.map(taskRow).join('') : '<div class="muted sm">Нет задач.</div>';
    $('#personalTasks').innerHTML = fpOpen.length ? fpOpen.map(taskRow).join('') : '<div class="muted sm">Нет задач.</div>';

    // архив выполненных
    const done = [...ft, ...fp].filter((t) => t.status === 'DONE');
    const doneSection = $('#doneSection');
    const doneTasks  = $('#doneTasks');
    const doneCount  = $('#doneCount');
    if (done.length) {
      doneSection.style.display = '';
      doneCount.textContent = done.length;
      doneTasks.innerHTML = done.map(taskRow).join('');
    } else {
      doneSection.style.display = 'none';
    }
  }

  // сворачивание/разворачивание архива
  document.addEventListener('click', (e) => {
    if (!e.target.closest('#doneToggle')) return;
    const tasks = $('#doneTasks');
    const chevron = $('#doneChevron');
    const hidden = tasks.style.display === 'none';
    tasks.style.display = hidden ? '' : 'none';
    chevron.textContent = hidden ? 'v' : '>';
  });

  async function renderMyTasks() {
    const [all, personal] = await Promise.all([
      api.get('/me/tasks'),
      api.get('/me/tasks/personal'),
    ]);
    state.myTasks = all;
    state.myPersonal = personal;
    applyTaskFilters();
  }

  /* ---------------- pet screen ---------------- */
  async function renderPet() {
    await refreshPet();
  }

  const TEAM_ACTIONS = ['думает', 'прыгает', 'ищет идею', 'пьет чай', 'читает', 'смотрит стену'];

  function renderTeamPlayground(pets) {
    const scene = $('#teamPlayground');
    if (!scene) return;
    scene.innerHTML = '';
    if (!pets.length) {
      scene.innerHTML = '<div class="muted sm">Питомцы появятся здесь, когда участники откроют Стену.</div>';
      return;
    }
    pets.slice(0, 8).forEach((pet, idx) => {
      const spot = document.createElement('div');
      spot.className = `team-pet lane-${idx % 4}`;
      spot.style.setProperty('--team-x', `${12 + ((idx * 23) % 72)}%`);
      spot.style.setProperty('--team-y', `${22 + ((idx * 31) % 54)}%`);
      spot.style.setProperty('--team-delay', `${(idx % 5) * -0.45}s`);
      const sprite = buildPixelPet(pet);
      if (pet.state) sprite.classList.add('state-' + pet.state);
      const emote = document.createElement('div');
      emote.className = 'pet-emote state-emote';
      emote.innerHTML = emoteImg(stateEmote(pet), pet.state_label || pet.state || '');
      const action = document.createElement('div');
      action.className = 'team-action';
      action.textContent = TEAM_ACTIONS[idx % TEAM_ACTIONS.length];
      const name = document.createElement('div');
      name.className = 'team-name';
      name.textContent = pet.name || 'Питомец';
      spot.append(sprite, emote, action, name);
      scene.appendChild(spot);
    });
  }

  function wallSeenKey() {
    return `petpro_wall_seen_${state.wsId || 'none'}`;
  }

  function paintWallBadge(count = state.wallUnread || 0) {
    const badge = $('#wallBadge');
    if (!badge) return;
    badge.textContent = count > 99 ? '99+' : String(count);
    badge.classList.toggle('hide', count <= 0);
  }

  async function refreshWallBadge(markSeen = false) {
    if (!state.wsId) return;
    const posts = await api.get(`/workspaces/${state.wsId}/wall?limit=50`);
    const latest = posts[0] && posts[0].id;
    const key = wallSeenKey();
    let seen = '';
    try { seen = localStorage.getItem(key) || ''; } catch (e) {}
    if (markSeen || !seen) {
      if (latest) {
        try { localStorage.setItem(key, latest); } catch (e) {}
      }
      state.wallUnread = 0;
      paintWallBadge(0);
      return;
    }
    const idx = posts.findIndex((p) => p.id === seen);
    state.wallUnread = idx < 0 ? posts.length : idx;
    paintWallBadge(state.wallUnread);
  }

  async function heartbeatWallPresence() {
    if (!state.wsId) return;
    await api.post(`/workspaces/${state.wsId}/wall/presence`, {});
  }

  /* ---------------- wall (бывш. team room) ---------------- */
  async function renderWall() {
    await heartbeatWallPresence().catch(() => {});
    // питомцы команды (справа)
    const data = await api.get(`/workspaces/${state.wsId}/team-room`).catch(() => ({ pets: [] }));
    const pets = data.pets || [];
    const online = $('#teamOnline');
    if (online) online.textContent = `онлайн: ${data.online_count || pets.length || 0}`;
    renderTeamPlayground(pets);
    $('#teamPets').innerHTML = (data.pets || [])
      .map(
        (p) => `<div class="petmini soft"><div class="av"><div class="hud">${levelOf(p.xp)}</div></div>
          <div class="meta"><b>${esc(p.name)}</b> <span class="mono">ур. ${levelOf(p.xp)} · ${p.xp} XP</span></div></div>`,
      )
      .join('') || '<div class="muted sm">На Стене сейчас никого нет.</div>';
    state.wallBefore = null;
    await loadWall(false);
    await refreshWallBadge(true);
  }

  function wallRow(p) {
    const mine = p.author_id === (state.me && state.me.id);
    const reactions = ['👍', '👎', '❤️', '😂', '🎉', '👀', '🔥'];
    const reactionHtml = reactions.map((emoji) => {
      const count = (p.reactions && p.reactions[emoji]) || 0;
      const active = (p.my_reactions || []).includes(emoji);
      return `<button class="wall-react ${active ? 'on' : ''}" data-wall-react="${p.id}" data-emoji="${emoji}">${emoji}${count ? ` ${count}` : ''}</button>`;
    }).join('');
    return `<div class="it" data-wall="${p.id}">
      <div class="av">${initials((p.author_name || '??').slice(0, 2))}</div>
      <div style="flex:1;">
        <b>${esc(p.author_name)}</b>
        ${p.text ? `<div>${esc(p.text)}</div>` : ''}
        ${p.image_data ? `<img class="wall-image" src="${esc(p.image_data)}" alt="Картинка на стене">` : ''}
        <div class="wall-reactions">${reactionHtml}</div>
        <div class="when">${new Date(p.created_at).toLocaleString('ru')}
          ${mine ? `· <span class="btn-like" data-wall-del="${p.id}" style="color:var(--danger);">удалить</span>` : ''}
          ${mine ? '' : `· <span class="btn-like" data-wall-report="${p.id}" style="color:var(--danger);">пожаловаться</span>`}
        </div>
      </div></div>`;
  }

  async function loadWall(append) {
    const q = state.wallBefore ? `?before=${state.wallBefore}` : '';
    const posts = await api.get(`/workspaces/${state.wsId}/wall${q}`);
    const html = posts.map(wallRow).join('');
    const feed = $('#wallFeed');
    if (append) feed.insertAdjacentHTML('beforeend', html);
    else feed.innerHTML = html || '<div class="muted sm">Пока пусто. Напиши первым!</div>';
    if (posts.length) state.wallBefore = posts[posts.length - 1].id;
    $('#wallMore').style.display = posts.length >= 50 ? '' : 'none';
  }

  function clearWallImage() {
    state.wallImageData = null;
    const file = $('#wallImageFile');
    if (file) file.value = '';
    const box = $('#wallImagePreview');
    if (box) {
      box.style.display = 'none';
      box.innerHTML = '';
    }
  }

  function attachWallImageFile(file) {
    if (!file) return clearWallImage();
    if (!file.type.startsWith('image/')) return toast('Можно прикрепить только картинку', '');
    if (file.size > 500 * 1024) {
      clearWallImage();
      return toast('Картинка слишком большая. Максимум 500 KB.', '');
    }
    const reader = new FileReader();
    reader.onload = () => {
      state.wallImageData = String(reader.result || '');
      $('#wallImagePreview').style.display = '';
      $('#wallImagePreview').innerHTML = `<img src="${esc(state.wallImageData)}" alt="Предпросмотр"><button class="btn sm" id="wallImageClear" type="button">Убрать</button>`;
    };
    reader.readAsDataURL(file);
  }

  function attachWallImageUrl(url) {
    const clean = String(url || '').trim();
    if (!/^https:\/\/.+\.(png|jpe?g|webp|gif)(\?.*)?$/i.test(clean)) return false;
    state.wallImageData = clean;
    $('#wallImagePreview').style.display = '';
    $('#wallImagePreview').innerHTML = `<img src="${esc(clean)}" alt="Предпросмотр"><button class="btn sm" id="wallImageClear" type="button">Убрать</button>`;
    return true;
  }

  function imageUrlFromHtml(html) {
    const doc = new DOMParser().parseFromString(html || '', 'text/html');
    const img = doc.querySelector('img[src]');
    return img ? img.getAttribute('src') : '';
  }

  $('#wallImageBtn').addEventListener('click', () => $('#wallImageFile').click());
  $('#wallImageFile').addEventListener('change', () => {
    const file = $('#wallImageFile').files && $('#wallImageFile').files[0];
    attachWallImageFile(file);
  });
  document.addEventListener('paste', (e) => {
    const active = $('.screen.on');
    if (!active || active.id !== 'screen-team') return;
    const items = Array.from((e.clipboardData && e.clipboardData.items) || []);
    const imageItem = items.find((item) => item.type && item.type.startsWith('image/'));
    if (!imageItem) return;
    const file = imageItem.getAsFile();
    if (!file) return;
    e.preventDefault();
    attachWallImageFile(file);
  });
  document.addEventListener('paste', (e) => {
    const active = $('.screen.on');
    if (!active || active.id !== 'screen-team') return;
    const htmlUrl = imageUrlFromHtml(e.clipboardData?.getData('text/html'));
    const textUrl = e.clipboardData?.getData('text/plain');
    if (attachWallImageUrl(htmlUrl || textUrl)) {
      e.preventDefault();
      toast('Картинка прикреплена', 'xp');
    }
  });
  document.addEventListener('click', (e) => {
    if (e.target.closest('#wallImageClear')) clearWallImage();
  });

  $('#wallSend').addEventListener('click', async () => {
    const text = $('#wallInput').value.trim();
    if (!text && !state.wallImageData) return;
    try {
      await api.post(`/workspaces/${state.wsId}/wall`, { text, image_data: state.wallImageData });
      $('#wallInput').value = '';
      clearWallImage();
      state.wallBefore = null;
      await loadWall(false);
      await refreshWallBadge(true);
    } catch (err) { toast(err.message, ''); }
  });
  $('#wallInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') $('#wallSend').click();
  });
  $('#wallMore').addEventListener('click', () => loadWall(true));
  document.addEventListener('click', async (e) => {
    const react = e.target.closest('[data-wall-react]');
    if (!react) return;
    try {
      await api.post(`/wall/${react.dataset.wallReact}/react`, { emoji: react.dataset.emoji });
      state.wallBefore = null;
      await loadWall(false);
    } catch (err) { toast(err.message, ''); }
  });
  document.addEventListener('click', async (e) => {
    const del = e.target.closest('[data-wall-del]');
    if (!del) return;
    if (!confirm('Удалить сообщение?')) return;
    try {
      await api.del(`/wall/${del.dataset.wallDel}`);
      state.wallBefore = null;
      await loadWall(false);
      await refreshWallBadge(true);
    } catch (err) { toast(err.message, ''); }
  });
  document.addEventListener('click', async (e) => {
    const report = e.target.closest('[data-wall-report]');
    if (!report) return;
    if (!confirm('Пожаловаться и удалить сообщение со Стены?')) return;
    try {
      await api.post(`/wall/${report.dataset.wallReport}/report`, {});
      state.wallBefore = null;
      await loadWall(false);
      await refreshWallBadge(true);
      toast('Сообщение удалено со Стены', '');
    } catch (err) { toast(err.message, ''); }
  });

  /* ---------------- game room ---------------- */
  const RARITY_LABEL = { common: 'обычный', rare: 'редкий', epic: 'эпик', legendary: 'легендарный' };

  async function renderGameRoom() {
    await refreshPet();
    // каталог магазина (один раз кэшируем)
    if (!state.shopCatalog) {
      const cat = await api.get('/shop/items');
      state.shopCatalog = cat.items;
      cat.items.forEach((it) => (SHOP_INDEX[it.id] = it));
      $('#casePrice').textContent = cat.case_price;
    }
    const panel = $('#shopPanel');
    if (panel) panel.hidden = !state.shopOpen;
    const toggle = $('#shopToggle');
    if (toggle) toggle.classList.toggle('primary', state.shopOpen);
    renderDailyBonus();
    renderShop();
    loadSudoku();
  }

  function renderDailyBonus() {
    const status = $('#dailyStatus');
    const btn = $('#claimDaily');
    if (!status || !btn) return;
    const today = new Date().toISOString().slice(0, 10);
    const claimed = (state.pet?.daily_claimed_on || '') === today;
    status.textContent = claimed ? 'Бонус на сегодня уже получен.' : '';
    btn.disabled = claimed;
  }

  /* ──────────────── ежедневная судоку 6×6 ──────────────── */
  const sudoku = { size: 6, br: 2, bc: 3, puzzle: null, cells: null, sel: null, solved: false };

  async function loadSudoku() {
    try {
      const d = await api.get('/games/sudoku/daily');
      sudoku.size = d.size;
      sudoku.br = d.block_rows;
      sudoku.bc = d.block_cols;
      sudoku.puzzle = d.puzzle;
      // cells: текущее состояние поля (копия задачи, 0 = пусто)
      sudoku.cells = d.puzzle.map((row) => row.slice());
      sudoku.solved = d.solved_today;
      $('#sudokuReward').textContent = d.reward;
      $('#sudokuStatus').textContent = d.solved_today ? '✓ решена сегодня' : 'не решена';
      $('#sudokuStatus').classList.toggle('xp', d.solved_today);
      $('#sudokuMsg').textContent = d.solved_today
        ? 'Сегодня уже пройдена. Возвращайся завтра за новой 🎉'
        : '';
      renderSudokuBoard();
      renderSudokuPad();
    } catch (err) {
      $('#sudokuMsg').textContent = err.message || 'Не удалось загрузить судоку';
    }
  }

  function renderSudokuBoard() {
    const board = $('#sudokuBoard');
    if (!board || !sudoku.cells) return;
    const { size, br, bc } = sudoku;
    board.style.setProperty('--sg', size);
    let html = '';
    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        const given = sudoku.puzzle[r][c] !== 0;
        const v = sudoku.cells[r][c];
        const cls = [
          'sudoku-cell',
          given ? 'given' : 'editable',
          sudoku.sel && sudoku.sel[0] === r && sudoku.sel[1] === c ? 'sel' : '',
          c % bc === bc - 1 && c !== size - 1 ? 'br' : '',
          r % br === br - 1 && r !== size - 1 ? 'bb' : '',
        ].join(' ');
        html += `<div class="${cls}" data-sr="${r}" data-sc="${c}">${v || ''}</div>`;
      }
    }
    board.innerHTML = html;
  }

  function renderSudokuPad() {
    const pad = $('#sudokuPad');
    if (!pad) return;
    let html = '';
    for (let n = 1; n <= sudoku.size; n++) {
      html += `<button class="btn sudoku-key" data-sk="${n}">${n}</button>`;
    }
    html += '<button class="btn sudoku-key erase" data-sk="0">⌫</button>';
    pad.innerHTML = html;
  }

  // выбор клетки
  document.addEventListener('click', (e) => {
    const cell = e.target.closest('.sudoku-cell');
    if (cell && !cell.classList.contains('given')) {
      sudoku.sel = [Number(cell.dataset.sr), Number(cell.dataset.sc)];
      renderSudokuBoard();
    }
  });

  // ввод цифры с пэда
  document.addEventListener('click', (e) => {
    const key = e.target.closest('[data-sk]');
    if (!key || !sudoku.sel) return;
    const [r, c] = sudoku.sel;
    if (sudoku.puzzle[r][c] !== 0) return; // нельзя менять данные
    sudoku.cells[r][c] = Number(key.dataset.sk);
    renderSudokuBoard();
  });

  // ввод с клавиатуры (1-6, Backspace/Delete)
  document.addEventListener('keydown', (e) => {
    if (!$('#screen-gameroom')?.classList.contains('on')) return;
    if (!sudoku.sel) return;
    const [r, c] = sudoku.sel;
    if (sudoku.puzzle[r][c] !== 0) return;
    if (/^[1-9]$/.test(e.key) && Number(e.key) <= sudoku.size) {
      sudoku.cells[r][c] = Number(e.key);
      renderSudokuBoard();
    } else if (e.key === 'Backspace' || e.key === 'Delete' || e.key === '0') {
      sudoku.cells[r][c] = 0;
      renderSudokuBoard();
    }
  });

  $('#sudokuReset')?.addEventListener('click', () => {
    if (!sudoku.puzzle) return;
    sudoku.cells = sudoku.puzzle.map((row) => row.slice());
    sudoku.sel = null;
    $('#sudokuMsg').textContent = '';
    renderSudokuBoard();
  });

  $('#sudokuCheck')?.addEventListener('click', async () => {
    if (!sudoku.cells) return;
    // не отправляем, если есть пустые клетки
    const hasBlank = sudoku.cells.some((row) => row.some((v) => !v));
    if (hasBlank) {
      $('#sudokuMsg').textContent = 'Заполни все клетки перед проверкой.';
      return;
    }
    const btn = $('#sudokuCheck');
    btn.disabled = true;
    try {
      const res = await api.post('/games/sudoku/solve', { solution: sudoku.cells });
      $('#sudokuMsg').textContent = res.message;
      if (res.correct) {
        sudoku.solved = true;
        $('#sudokuStatus').textContent = '✓ решена сегодня';
        $('#sudokuStatus').classList.add('xp');
        if (res.coins_awarded > 0) {
          toast(`+${res.coins_awarded} монет за судоку 🪙`, 'xp');
          await refreshPet();
        }
      }
    } catch (err) {
      $('#sudokuMsg').textContent = err.message || 'Ошибка проверки';
    } finally {
      btn.disabled = false;
    }
  });

  function itemPreview(it) {
    if (it.type === 'character') return `<div class="character-item-preview">${characterImage(it.id, it.name)}</div>`;
    if (it.type === 'food') return `<div class="swatch-prev food-prev">${iconImg(itemIcon(it), it.name, 'lg')}</div>`;
    if (it.type === 'hat') return `<div class="swatch-prev hat-prev">${hatImg(it)}</div>`;
    if (it.type === 'bg') return `<div class="swatch-prev" style="background:${it.data};"></div>`;
    return `<div class="swatch-prev" style="background:${it.data};"></div>`; // body/accent
  }

  function renderShop() {
    const pet = state.pet || {};
    const inv = pet.inventory || [];
    const tab = state.shopTab || 'all';
    $('#shopTabs')?.querySelectorAll('[data-shop-tab]').forEach((b) => {
      b.classList.toggle('on', b.dataset.shopTab === tab);
    });
    const hiddenTypes = new Set(['body', 'accent']);
    const catalogOnlyTypes = new Set(['body', 'accent', 'species', 'character']);
    const items = (state.shopCatalog || []).filter((it) => {
      if (hiddenTypes.has(it.type)) return false;
      return tab === 'all' || it.type === tab;
    });
    $('#shopGrid').innerHTML = items
      .map((it) => {
        const foodCount = Number(pet.food_inventory?.[it.id] || 0);
        const owned = it.type !== 'food' && inv.includes(it.id);
        const catalogOnly = catalogOnlyTypes.has(it.type);
        const selectedCharacter = it.type === 'character' && pet.species === it.id;
        const lockedCharacter = it.type === 'character' && Number(pet.level || 1) < Number(it.min_level || 1);
        const cls = `shopcard ${owned ? 'owned' : ''} ${catalogOnly ? 'catalog-only' : ''}`;
        const action = catalogOnly
          ? 'только рулетка'
          : selectedCharacter
          ? 'выбран'
          : owned
            ? 'в коллекции'
            : lockedCharacter
              ? `с ${it.min_level} уровня`
              : `${iconLabel('coin', String(it.price))}${it.type === 'food' && foodCount ? ` <span class="food-count-inline">x${foodCount}</span>` : ''}`;
        return `<div class="${cls}" data-shop="${it.id}" data-owned="${owned ? 1 : 0}" data-catalog-only="${catalogOnly ? 1 : 0}">
          ${itemPreview(it)}
          <div class="nm">${esc(it.name)}</div>
          <div class="rar rar-${it.rarity}">${RARITY_LABEL[it.rarity]}</div>
          <div class="sm" style="margin-top:4px;">${action}</div>
        </div>`;
      })
      .join('') || '<div class="muted sm">В этой вкладке пока пусто.</div>';
    renderBackpack();
    renderFoodBags();
  }

  function inventoryCard(it, compact = false) {
    const pet = state.pet || {};
    const eq = pet.equipped || {};
    const equipped = it.type === 'character' ? pet.species === it.id : eq[it.type] === it.id;
    return `<div class="shopcard bagitem ${equipped ? 'equipped' : ''}" data-inventory="${it.id}" title="${equipped ? 'Снять' : 'Надеть'}">
      ${itemPreview(it)}
      ${compact ? '' : `<div class="nm">${esc(it.name)}</div><div class="rar rar-${it.rarity}">${RARITY_LABEL[it.rarity]}</div>`}
      <div class="sm" style="margin-top:4px;">${it.type === 'character' ? (equipped ? 'выбран' : 'выбрать') : (equipped ? 'надето' : 'надеть')}</div>
    </div>`;
  }

  function renderBackpack() {
    const pet = state.pet || {};
    const items = (pet.inventory || [])
      .map((id) => SHOP_INDEX[id])
      .filter((it) => it && !['body', 'accent', 'species', 'character'].includes(it.type));
    const full = $('#inventoryGrid');
    if (full) {
      full.innerHTML = items.length
        ? items.map((it) => inventoryCard(it)).join('')
        : '<div class="muted sm">Рюкзак пуст. Открой кейс или купи предмет.</div>';
    }
    const dock = $('#dockBackpack');
    if (dock) {
      const pageSize = 4;
      const pages = Math.max(1, Math.ceil(items.length / pageSize));
      state.dockBagPage = Math.max(0, Math.min(state.dockBagPage || 0, pages - 1));
      const pageItems = items.slice(state.dockBagPage * pageSize, state.dockBagPage * pageSize + pageSize);
      dock.innerHTML = `<div class="dock-bag-title">Рюкзак</div>${
        items.length
          ? `<div class="dock-bag-grid">${pageItems.map((it) => inventoryCard(it, true)).join('')}</div>
            <div class="dock-bag-pager">
              <button class="dock-page-btn" data-dock-bag-page="-1" ${pages <= 1 ? 'disabled' : ''} aria-label="Назад">&lt;</button>
              <span>${state.dockBagPage + 1}/${pages}</span>
              <button class="dock-page-btn" data-dock-bag-page="1" ${pages <= 1 ? 'disabled' : ''} aria-label="Вперед">&gt;</button>
            </div>`
          : '<div class="muted sm">Пусто</div>'
      }`;
    }
  }

  function foodEntries() {
    const food = state.pet?.food_inventory || {};
    return Object.entries(food)
      .map(([id, count]) => ({ it: SHOP_INDEX[id], count: Number(count || 0) }))
      .filter((entry) => entry.it && entry.count > 0);
  }

  function foodCard(entry, compact = false) {
    const { it, count } = entry;
    const data = it.data || {};
    const stats = compact
      ? ''
      : `<div class="sm food-stats">+${Number(data.hunger || 0)} сытость</div>`;
    return `<div class="shopcard bagitem fooditem" data-food="${it.id}" draggable="true" title="Перетащи на питомца или кликни: ${esc(it.name)}">
      ${itemPreview(it)}
      <span class="food-count">x${count}</span>
      ${compact ? '' : `<div class="nm">${esc(it.name)}</div><div class="rar rar-${it.rarity}">${RARITY_LABEL[it.rarity]}</div>`}
      ${stats}
    </div>`;
  }

  function renderFoodShelf(el, title, compact = false) {
    const items = foodEntries();
    el.classList.toggle('is-empty', items.length === 0);
    el.title = items.length === 0 ? 'Купить еду в магазине' : '';
    const pageSize = 4;
    const pages = Math.max(1, Math.ceil(items.length / pageSize));
    state.foodBagPage = Math.max(0, Math.min(state.foodBagPage || 0, pages - 1));
    const pageItems = items.slice(state.foodBagPage * pageSize, state.foodBagPage * pageSize + pageSize);
    const slots = items.length
      ? Array.from({ length: pageSize }, (_, idx) =>
          pageItems[idx] ? foodCard(pageItems[idx], compact) : '<div class="food-slot empty"></div>',
        ).join('')
      : `<button class="food-shop-cta ${compact ? 'compact' : ''}" type="button" data-open-food-shop>
          ${iconLabel('apple', 'Купить еду')}
        </button>`;
    el.innerHTML = `<div class="dock-bag-title">${title}</div>
      <div class="dock-bag-grid food-grid">${slots}</div>
      <div class="dock-bag-pager">
        <button class="dock-page-btn" data-food-page="-1" ${pages <= 1 ? 'disabled' : ''} aria-label="Назад">&lt;</button>
        <span>${state.foodBagPage + 1}/${pages}</span>
        <button class="dock-page-btn" data-food-page="1" ${pages <= 1 ? 'disabled' : ''} aria-label="Вперед">&gt;</button>
      </div>`;
  }

  function renderFoodBags() {
    const belt = $('#foodBelt');
    if (belt) renderFoodShelf(belt, 'Еда для питомца');
    const dock = $('#dockFoodBag');
    if (dock) renderFoodShelf(dock, 'Еда', true);
  }

  async function openFoodShop() {
    state.shopOpen = true;
    state.shopTab = 'food';
    await go('gameroom');
    const panel = $('#shopPanel');
    if (panel && !panel.hidden) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-dock-bag-page]');
    if (!btn) return;
    e.preventDefault();
    const pet = state.pet || {};
    const total = (pet.inventory || []).map((id) => SHOP_INDEX[id]).filter(Boolean).length;
    const pages = Math.max(1, Math.ceil(total / 4));
    state.dockBagPage = (state.dockBagPage + Number(btn.dataset.dockBagPage) + pages) % pages;
    renderBackpack();
  });

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-food-page]');
    if (!btn) return;
    e.preventDefault();
    const pages = Math.max(1, Math.ceil(foodEntries().length / 4));
    state.foodBagPage = (state.foodBagPage + Number(btn.dataset.foodPage) + pages) % pages;
    renderFoodBags();
  });

  $('#shopTabs')?.addEventListener('click', (e) => {
    const tab = e.target.closest('[data-shop-tab]');
    if (!tab) return;
    state.shopTab = tab.dataset.shopTab;
    renderShop();
  });

  // клик по товару: в каталоге покупаем, экипировка живет в рюкзаке
  $('#shopGrid').addEventListener('click', async (e) => {
    const card = e.target.closest('[data-shop]');
    if (!card) return;
    const id = card.dataset.shop;
    const owned = card.dataset.owned === '1';
    if (card.dataset.catalogOnly === '1') {
      toast('Персонажи будут выбиваться через отдельную рулетку.', '');
      return;
    }
    if (owned) {
      toast('Уже в рюкзаке. Надеть можно ниже в рюкзаке.', 'xp');
      return;
    }
    try {
      state.pet = await api.post('/shop/buy', { item_id: id });
      paintPet(state.pet);
      renderShop();
      toast(SHOP_INDEX[id]?.type === 'food' ? 'Еда добавлена!' : 'Куплено!', 'xp');
    } catch (err) { toast(err.message, ''); }
  });

  document.addEventListener('click', async (e) => {
    const card = e.target.closest('[data-inventory]');
    if (!card) return;
    try {
      state.pet = await api.post('/shop/equip', { item_id: card.dataset.inventory });
      paintPet(state.pet);
      renderShop();
    } catch (err) { toast(err.message, ''); }
  });

  function caseTile(it, winner = false) {
    return `<div class="case-tile rar-${it.rarity}" ${winner ? 'data-case-winner="1"' : ''}>
      ${itemPreview(it)}
      <div class="nm">${esc(it.name)}</div>
      <div class="rar rar-${it.rarity}">${RARITY_LABEL[it.rarity]}</div>
    </div>`;
  }

  function runCaseRoll(resultItem) {
    const casePool = (state.shopCatalog || []).filter(
      (it) => !['food', 'body', 'accent', 'species', 'character'].includes(it.type),
    );
    const pool = casePool.length ? casePool : [resultItem];
    const winnerIndex = 24;
    const roll = Array.from({ length: 34 }, (_, idx) =>
      idx === winnerIndex ? resultItem : pool[Math.floor(Math.random() * pool.length)],
    );
    $('#caseResult').innerHTML = `<div class="case-roulette">
      <div class="case-marker"></div>
      <div class="case-strip">${roll.map((it, idx) => caseTile(it, idx === winnerIndex)).join('')}</div>
    </div>`;
    const roulette = $('#caseResult .case-roulette');
    const strip = $('#caseResult .case-strip');
    const winner = $('#caseResult .case-tile[data-case-winner="1"]');
    strip.style.transition = 'none';
    strip.style.transform = `translateX(${roulette.clientWidth + 24}px)`;
    const winnerCenter = winner.offsetLeft + winner.offsetWidth / 2;
    const markerCenter = roulette.clientWidth / 2;
    const targetX = markerCenter - winnerCenter;
    requestAnimationFrame(() => {
      strip.getBoundingClientRect();
      strip.style.transition = '';
      strip.style.transform = `translateX(${targetX}px)`;
    });
    return new Promise((resolve) => setTimeout(() => {
      winner.classList.add('winner');
      resolve();
    }, 2600));
  }

  $('#openCase').addEventListener('click', async () => {
    const btn = $('#openCase');
    btn.disabled = true;
    try {
      const res = await api.post('/shop/open-case', {});
      const it = res.item;
      await runCaseRoll(it);
      $('#caseResult').insertAdjacentHTML(
        'beforeend',
        `<div class="case-final shopcard ${res.is_new ? 'owned' : ''}">${itemPreview(it)}
          <div class="nm">${esc(it.name)}</div>
          <div class="rar rar-${it.rarity}">${RARITY_LABEL[it.rarity]}</div>
          <div class="sm">${res.is_new ? iconLabel('present', 'Новый предмет!') : iconLabel('small_coin', 'Дубликат - вернули монеты')}</div>
        </div>`,
      );
      await refreshPet();
      renderShop();
      toast(res.is_new ? `Выпал: ${it.name}!` : 'Дубликат', res.is_new ? 'lvl' : 'xp');
    } catch (err) { toast(err.message, ''); }
    finally { btn.disabled = false; }
  });

  // игры с питомцем — лёгкие локальные действия (поднимают настроение визуально)
  const playAnim = (iconName) => {
    const screens = ['#dockPetScreen', '#screen-pet .petscreen']
      .map((sel) => $(sel))
      .filter(Boolean);
    screens.forEach((screen) => {
      const sprite = screen.querySelector('.pixelpet');
      if (sprite) {
        sprite.classList.add('state-happy');
        setTimeout(() => sprite.classList.remove('state-happy'), 1500);
      }
      if (PET_EMOTES[iconName]) {
        showPetEmote(screen, iconName, 'burst');
        return;
      }
      const burst = document.createElement('div');
      burst.appendChild(iconNode(iconName, 'xl'));
      burst.style.cssText = 'position:absolute;top:30%;left:50%;transform:translateX(-50%);font-size:32px;z-index:6;animation:toastin .4s;pointer-events:none;';
      screen.appendChild(burst);
      setTimeout(() => burst.remove(), 1200);
    });
  };
  function updatePlayControls() {
    const pet = state.pet || {};
    const rules = {
      playFeed: {
        disabled: Number(pet.hunger || 0) >= 95,
        title: 'Питомец уже сыт',
      },
      playPet: {
        disabled: Number(pet.hunger || 0) <= 5 || Number(pet.energy || 0) <= 5,
        title: Number(pet.hunger || 0) <= 5 ? 'Сначала покорми питомца' : 'Питомец спит без сил',
      },
      playBall: {
        disabled: Number(pet.hunger || 0) <= 10 || Number(pet.energy || 0) < 12,
        title: Number(pet.hunger || 0) <= 10 ? 'Питомец голоден' : 'Нужно минимум 12 энергии',
      },
      playSleep: {
        disabled: Number(pet.energy || 0) >= 80,
        title: 'Сон доступен, когда энергия ниже 80',
      },
      petSleep: {
        disabled: Number(pet.energy || 0) >= 80,
        title: 'Сон доступен, когда энергия ниже 80',
      },
    };
    Object.entries(rules).forEach(([id, rule]) => {
      const btn = $('#' + id);
      if (!btn) return;
      btn.disabled = rule.disabled;
      btn.title = rule.disabled ? rule.title : '';
      btn.classList.toggle('disabled', rule.disabled);
    });
  }

  function highlightFoodBags() {
    $$('#foodBelt, #dockFoodBag').forEach((el) => {
      el.classList.add('need-food');
      setTimeout(() => el.classList.remove('need-food'), 1600);
    });
  }

  async function playWithPet(action, iconName, message, itemId = null) {
    try {
      const payload = itemId ? { action, item_id: itemId } : { action };
      state.pet = await api.post('/pets/me/play', payload);
      paintPet(state.pet);
      playAnim(iconName);
      renderShop();
      const coins = action === 'feed' || action === 'sleep' ? '' : iconLabel('coin', '+25');
      $('#playMsg').innerHTML = `${esc(message)} ${coins}`;
    } catch (err) {
      $('#playMsg').textContent = err.message;
      toast(err.message, '');
      await refreshPet().catch(() => {});
    }
  }

  async function feedWithFood(itemId) {
    const it = SHOP_INDEX[itemId];
    if (!it) return;
    await playWithPet('feed', itemIcon(it), `Питомец съел: ${it.name}`, itemId);
  }

  let draggedFoodId = null;

  function foodDropScreens() {
    return $$('.petscreen').filter((screen) => !screen.closest('#petcreate'));
  }

  function setFoodDropReady(ready) {
    foodDropScreens().forEach((screen) => {
      screen.classList.toggle('food-drop-ready', ready);
      if (!ready) screen.classList.remove('food-drop-over');
    });
  }

  function foodDragId(e) {
    return e.dataTransfer?.getData('application/x-petpro-food') || draggedFoodId || '';
  }

  document.addEventListener('dragstart', (e) => {
    const card = e.target.closest('[data-food]');
    if (!card) return;
    draggedFoodId = card.dataset.food;
    card.classList.add('dragging-food');
    e.dataTransfer.effectAllowed = 'copy';
    e.dataTransfer.setData('application/x-petpro-food', draggedFoodId);
    e.dataTransfer.setData('text/plain', draggedFoodId);
    setFoodDropReady(true);
  });

  document.addEventListener('dragend', (e) => {
    e.target.closest('[data-food]')?.classList.remove('dragging-food');
    draggedFoodId = null;
    setFoodDropReady(false);
  });

  document.addEventListener('dragover', (e) => {
    const screen = e.target.closest('.petscreen');
    if (!screen || screen.closest('#petcreate') || !foodDragId(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    screen.classList.add('food-drop-over');
  });

  document.addEventListener('dragleave', (e) => {
    const screen = e.target.closest('.petscreen');
    if (!screen || screen.contains(e.relatedTarget)) return;
    screen.classList.remove('food-drop-over');
  });

  document.addEventListener('drop', (e) => {
    const screen = e.target.closest('.petscreen');
    const itemId = foodDragId(e);
    if (!screen || screen.closest('#petcreate') || !itemId) return;
    e.preventDefault();
    draggedFoodId = null;
    setFoodDropReady(false);
    if (Number(state.pet?.hunger || 0) >= 95) {
      $('#playMsg').textContent = 'Питомец уже сыт.';
      return;
    }
    feedWithFood(itemId);
  });

  document.addEventListener('click', (e) => {
    const card = e.target.closest('[data-food]');
    if (!card) return;
    e.preventDefault();
    feedWithFood(card.dataset.food);
  });

  document.addEventListener('click', (e) => {
    const foodLink = e.target.closest('[data-open-food-shop], #foodBelt.is-empty, #dockFoodBag.is-empty');
    if (!foodLink) return;
    e.preventDefault();
    openFoodShop();
  });

  $('#playFeed')?.addEventListener('click', () => {
    if (Number(state.pet?.hunger || 0) >= 95) {
      $('#playMsg').textContent = 'Питомец уже сыт.';
      return;
    }
    const items = foodEntries();
    highlightFoodBags();
    if (items.length) {
      $('#playMsg').textContent = 'Выбери еду на полке ниже или справа.';
      return;
    }
    $('#playMsg').textContent = 'Еды нет. Открываю магазин еды.';
    openFoodShop();
  });
  $('#playPet').addEventListener('click', () => playWithPet('pet', 'pickup_heart', 'Питомцу приятно'));
  $('#playBall').addEventListener('click', () => playWithPet('ball', 'music', 'Игра в мячик - весело!'));
  $('#playSleep')?.addEventListener('click', () => playWithPet('sleep', 'sleep', 'Питомец выспался и восстановил энергию.'));
  $('#petSleep')?.addEventListener('click', () => {
    go('gameroom');
    playWithPet('sleep', 'sleep', 'Питомец выспался и восстановил энергию.');
  });
  $('#shopToggle')?.addEventListener('click', () => {
    state.shopOpen = !state.shopOpen;
    renderGameRoom();
  });
  $('#claimDaily')?.addEventListener('click', async () => {
    const btn = $('#claimDaily');
    btn.disabled = true;
    try {
      const res = await api.post('/pets/me/daily', {});
      state.pet = res.pet;
      paintPet(state.pet);
      renderDailyBonus();
      toast(`+${res.coins_awarded} монет`, 'xp');
    } catch (err) {
      toast(err.message, '');
      renderDailyBonus();
    }
  });

  /* ---------------- notifications ---------------- */
  const UI_NOTIFICATION_TYPES = new Set(['TASK_ASSIGNED', 'DEADLINE']);

  async function refreshNotifBadge() {
    const list = await api.get('/notifications');
    const unread = list.filter((n) => UI_NOTIFICATION_TYPES.has(n.type) && !n.is_read).length;
    const badge = $('#notifBadge');
    badge.textContent = unread;
    badge.classList.toggle('hide', unread === 0);
  }

  async function renderNotifications() {
    const list = (await api.get('/notifications')).filter((n) => UI_NOTIFICATION_TYPES.has(n.type));
    $('#notifList').innerHTML = list.length
      ? list
          .map(
            (n) => `<div class="task ${n.is_read ? 'done' : ''}" data-notif="${n.id}"
                 data-entity-type="${n.entity_type || ''}" data-entity-id="${n.entity_id || ''}"
                 style="cursor:pointer;">
              <div class="t"><b>${esc(n.title)}</b>${n.body ? ' — ' + esc(n.body) : ''}
                <div class="mono">${new Date(n.created_at).toLocaleString('ru')}${n.entity_type ? ' · нажмите, чтобы открыть' : ''}</div></div>
              ${n.is_read ? '' : '<span class="chip acc btn-like" data-read="' + n.id + '">прочитать</span>'}
            </div>`,
          )
          .join('')
      : '<div class="muted sm">Уведомлений нет.</div>';
    await refreshNotifBadge();
  }

  // переход к источнику уведомления
  function openNotifTarget(entityType, entityId) {
    if (!entityType || !entityId) return;
    if (entityType === 'task') openTask(entityId);
    else if (entityType === 'project') openProject(entityId);
    else if (entityType === 'article') openArticle(entityId);
  }

  document.addEventListener('click', async (e) => {
    // кнопка «прочитать» — только отметить, без перехода
    const r = e.target.closest('[data-read]');
    if (r) {
      e.stopPropagation();
      await api.patch(`/notifications/${r.dataset.read}/read`, {});
      renderNotifications();
      return;
    }
    // клик по самому уведомлению — отметить прочитанным и перейти к источнику
    const note = e.target.closest('#notifList [data-notif]');
    if (!note) return;
    const id = note.dataset.notif;
    const et = note.dataset.entityType;
    const eid = note.dataset.entityId;
    api.patch(`/notifications/${id}/read`, {}).then(() => refreshNotifBadge()).catch(() => {});
    openNotifTarget(et, eid);
  });

  $('#readAllBtn').addEventListener('click', async () => {
    await api.patch('/notifications/read-all', {});
    renderNotifications();
  });

  /* ---------------- start ---------------- */
  if (api.isAuthed()) {
    enterApp().catch(() => {
      api.clearTokens();
    });
  }
})();
