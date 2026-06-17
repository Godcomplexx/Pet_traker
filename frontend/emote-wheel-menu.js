(function () {
  'use strict';

  const EMOTE_DIR = 'assets/emotes/pipoya';
  const RPS = {
    rock: { label: 'Камень', short: 'К', index: 86 },
    scissors: { label: 'Ножницы', short: 'Н', index: 87 },
    paper: { label: 'Бумага', short: 'Б', index: 88 },
  };

  const group = (id, label, icon, entries) => ({ id, label, icon, entries });
  const action = (id) => ({ action: id });
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
    group('game', 'Игры', 85, [action('rock'), action('scissors'), action('paper')]),
  ];

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

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"]/g, (char) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
    }[char]));
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

  function buildMenu(target, mode, handlers) {
    const categories = mode === 'pet' ? PET_GROUPS : WALL_GROUPS;
    let active = categories[0].id;
    const root = document.createElement('div');
    root.className = `emote-wheel ${mode === 'pet' ? 'pet-mode' : 'wall-mode'}`;
    root.setAttribute('role', 'menu');

    const center = document.createElement('button');
    center.type = 'button';
    center.className = 'emote-wheel-center';
    center.addEventListener('click', handlers.closeMenu);
    root.appendChild(center);

    const categoryRing = document.createElement('div');
    categoryRing.className = 'emote-category-ring';
    const itemRing = document.createElement('div');
    itemRing.className = 'emote-item-ring';
    root.append(categoryRing, itemRing);

    root.addEventListener('click', (event) => {
      if (event.target.closest('.emote-choice, .emote-wheel-center')) return;
      const box = root.getBoundingClientRect();
      const distance = Math.hypot(event.clientX - (box.left + box.width / 2), event.clientY - (box.top + box.height / 2));
      if (distance < box.width * 0.30 || distance > box.width * 0.50) return;
      const degrees = (Math.atan2(event.clientY - (box.top + box.height / 2), event.clientX - (box.left + box.width / 2)) * 180 / Math.PI + 450) % 360;
      active = categories[Math.round(degrees / (360 / categories.length)) % categories.length].id;
      event.preventDefault();
      event.stopPropagation();
      render();
    }, true);

    function render() {
      const selected = categories.find((category) => category.id === active) || categories[0];
      center.innerHTML = `<b>${escapeHtml(selected.label)}</b><span>Esc</span>`;
      categoryRing.replaceChildren(...categories.map((category, index) => {
        const button = categoryButton(category, index, categories.length, () => {
          active = category.id;
          render();
        });
        button.classList.toggle('on', category.id === selected.id);
        return button;
      }));
      itemRing.replaceChildren(...selected.entries.map((entry, index) => itemButton(target, entry, index, selected.entries.length, mode, handlers)));
    }

    render();
    return root;
  }

  function categoryButton(category, index, total, onClick) {
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
    button.addEventListener('click', onClick);
    return button;
  }

  function itemButton(target, entry, index, total, mode, handlers) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'emote-node emote-choice';
    setRadialPosition(button, index, total, 66);
    if (typeof entry === 'object' && entry.action) {
      button.classList.add('emote-rps');
      button.title = RPS[entry.action].label;
      button.appendChild(rpsEmoteImg(entry.action));
      button.addEventListener('click', () => handlers.inviteRps(target, entry.action));
      return button;
    }
    button.title = `Emote ${entry + 1}`;
    button.appendChild(emoteImg(entry));
    button.addEventListener('click', () => handlers.chooseEmote(target, entry, mode));
    return button;
  }

  function buildRpsChoiceMenu(challenge, handlers) {
    const root = document.createElement('div');
    root.className = 'emote-wheel rps-choice-mode';
    root.setAttribute('role', 'menu');
    const center = document.createElement('button');
    center.type = 'button';
    center.className = 'emote-wheel-center';
    center.innerHTML = '<b>Ваш ход</b><span>Esc</span>';
    center.addEventListener('click', handlers.closeMenu);
    const itemRing = document.createElement('div');
    itemRing.className = 'emote-item-ring';
    ['rock', 'scissors', 'paper'].forEach((key, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'emote-node emote-rps';
      button.title = RPS[key].label;
      button.appendChild(rpsEmoteImg(key));
      setRadialPosition(button, index, 3, 86);
      button.addEventListener('click', () => handlers.chooseRpsResponse(challenge, key));
      itemRing.appendChild(button);
    });
    root.append(center, itemRing);
    return root;
  }

  window.petproEmoteWheelMenu = {
    RPS,
    buildMenu,
    buildRpsChoiceMenu,
    emoteImg,
    emotePath,
    escapeHtml,
    rpsEmoteImg,
  };
})();
