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
  };

  const esc = (s) =>
    String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const initials = (name) =>
    (name || '?').split(/\s+/).map((w) => w[0]).join('').slice(0, 2).toUpperCase();

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
      team: renderTeam,
      notif: renderNotifications,
    };
    if (loaders[name]) loaders[name]();
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
    if (!pet.customized) {
      showPetCreator(pet);
      return;
    }
    launchApp();
  }

  function launchApp() {
    $('#onboard').classList.remove('on');
    $('#petcreate').classList.remove('on');
    $('#app').style.display = 'grid';
    $('#meName').innerHTML = `${esc(state.me.display_name)}<div class="mono">${esc(state.me.email)}</div>`;
    $('#meAvatar').textContent = initials(state.me.display_name);

    renderWorkspacePicker();
    refreshPet();
    refreshNotifBadge();
    startPolling();
    go('dashboard');
  }

  function startPolling() {
    if (state.pollTimer) clearInterval(state.pollTimer);
    state.pollTimer = setInterval(async () => {
      if (!api.isAuthed() || !state.wsId) return;
      try {
        await refreshNotifBadge();
        const active = $('.screen.on');
        const name = active ? active.id.replace('screen-', '') : '';
        if (name === 'dashboard') await refreshDashboardLive();
        if (name === 'team') await renderTeam();
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
  const SPECIES_LIST = [
    { id: 'capybara', label: '🦫 Капибара' },
    { id: 'cat', label: '🐱 Кот' },
    { id: 'dog', label: '🐶 Пёс' },
    { id: 'frog', label: '🐸 Лягушка' },
    { id: 'axolotl', label: '🦎 Аксолотль' },
  ];
  const BODY_COLORS = ['#9dbf9b', '#b5acce', '#c9a5ba', '#a8c4d4', '#d4c4a8', '#c4b5a0', '#a8b8c8', '#b8c8a8'];
  const ACCENT_COLORS = ['#7a9e78', '#9b8fbd', '#b08a9e', '#7a9eb0', '#b09a7a', '#9a8a78', '#8a9ab0', '#9aaa8a'];

  const pcDraft = { name: 'Кодзи', species: 'capybara', body_color: '#9dbf9b', accent_color: '#b08a9e' };

  function pcPreview() {
    const screen = $('#petcreate .petscreen');
    const old = screen.querySelector('.pixelpet');
    if (old) old.remove();
    screen.appendChild(buildPixelPet(pcDraft));
  }

  function showPetCreator(pet) {
    // Префилл из существующего питомца (на случай повторной настройки).
    pcDraft.name = pet.name && pet.name !== 'Питомец' ? pet.name : 'Кодзи';
    pcDraft.species = pet.species || 'capybara';
    pcDraft.body_color = pet.body_color || '#9dbf9b';
    pcDraft.accent_color = pet.accent_color || '#b08a9e';
    $('#pcName').value = pcDraft.name;

    $('#pcSpecies').innerHTML = SPECIES_LIST.map(
      (s) => `<div class="species-opt ${s.id === pcDraft.species ? 'on' : ''}" data-species="${s.id}">${s.label}</div>`,
    ).join('');
    $('#pcBody').innerHTML = BODY_COLORS.map(
      (c) => `<div class="swatch ${c === pcDraft.body_color ? 'on' : ''}" data-body="${c}" style="background:${c}"></div>`,
    ).join('');
    $('#pcAccent').innerHTML = ACCENT_COLORS.map(
      (c) => `<div class="swatch ${c === pcDraft.accent_color ? 'on' : ''}" data-accent="${c}" style="background:${c}"></div>`,
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
    const body = e.target.closest('[data-body]');
    if (body) {
      pcDraft.body_color = body.dataset.body;
      $$('#pcBody .swatch').forEach((x) => x.classList.toggle('on', x === body));
      pcPreview();
      return;
    }
    const acc = e.target.closest('[data-accent]');
    if (acc) {
      pcDraft.accent_color = acc.dataset.accent;
      $$('#pcAccent .swatch').forEach((x) => x.classList.toggle('on', x === acc));
      pcPreview();
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
      toast(`${pet.name} готов! 🎉`, 'xp');
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
      .map((w) => `<option value="${w.id}">🧪 ${esc(w.name)}</option>`)
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

  // Перерисовать спрайт во всех экранах-«дисплеях» с учётом состояния.
  function paintSprites(pet) {
    $$('.petscreen').forEach((screen) => {
      const old = screen.querySelector('.pixelpet');
      if (old) old.remove();
      const sprite = buildPixelPet(pet);
      if (pet.state) sprite.classList.add('state-' + pet.state);
      screen.appendChild(sprite);
    });
  }

  const STATE_EMOJI = { happy: '😊', ok: '🙂', sad: '😟', hungry: '🍽️', sleepy: '😴' };

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
    // Подпись состояния (тамагочи).
    const emoji = STATE_EMOJI[pet.state] || '';
    $$('[data-petstate]').forEach((e) => (e.textContent = `${emoji} ${pet.state_label || ''}`.trim()));
    paintSprites(pet);
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
      if (pet.state === 'hungry') toast('Питомец проголодался — закрой задачу 🍽️', '');
      else if (pet.state === 'sad') toast('Питомец загрустил без работы 😟', '');
      else if (pet.state === 'sleepy') toast('Питомцу нужен отдых 😴', '');
      else if (pet.state === 'happy') toast('Питомец доволен! 😊', 'xp');
    }
    state.prevState = pet.state;
    state.prevXp = pet.xp;
    state.pet = pet;
    paintPet(pet);
  }

  $('#renamePetBtn').addEventListener('click', async () => {
    const name = prompt('Имя питомца:', state.pet ? state.pet.name : '');
    if (!name) return;
    await api.patch('/pets/me', { name });
    await refreshPet();
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
    $('#dashHi').textContent = `Привет, ${state.me.display_name.split(' ')[0]} 👋`;
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
    $('#dashTasks').innerHTML = tasks.length
      ? tasks.slice(0, 8).map(taskRow).join('')
      : '<div class="muted sm">Задач пока нет — создайте на «Мои задачи».</div>';

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
          (p) => `<div class="acard soft" style="cursor:pointer;" data-open-project="${p.id}">
            <div class="row"><span class="tag ptype">${p.type}</span></div>
            <div class="ttl">${esc(p.name)}</div>
          </div>`,
        )
        .join('');
      return `<div class="colm"><div class="colhead soft"><b>${st}</b><span class="cnt">${inCol.length}</span></div>${cards}</div>`;
    }).join('');
  }

  $('#newProjectBtn').addEventListener('click', async () => {
    const name = $('#projName').value.trim();
    if (!name) return;
    await api.post(`/workspaces/${state.wsId}/projects`, { name, type: $('#projType').value });
    $('#projName').value = '';
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
    await api.post(`/workspaces/${state.wsId}/articles`, { title });
    $('#artTitle').value = '';
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
    try {
      await api.post('/tasks', { scope: 'PROJECT', project_id: state.openProject, title });
      $('#pdNewTask').value = '';
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

    const tasks = await api.get(`/projects/${a.project_id}/tasks`).catch(() => []);
    const own = tasks.filter((t) => t.article_id === id);
    $('#adTaskCount').textContent = `${own.length}`;
    $('#adTasks').innerHTML = own.length ? own.map(taskRowLinked).join('') : '<div class="muted sm">Нет задач статьи.</div>';

    renderMemberManager('article', id, a.workspace_id);
    mountComments('article', id);
  }

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
    $('#tdTitle').textContent = t.title;
    $('#tdMeta').textContent = `${t.scope} · ${t.type} · ${t.status}${t.due_date ? ' · до ' + t.due_date : ''}`;
    $('#tdDesc').textContent = t.description || 'Без описания';
    $('#tdToggle').textContent = t.status === 'DONE' ? 'Переоткрыть' : 'Закрыть задачу';
    mountComments('task', id);
  }

  $('#tdBack').addEventListener('click', () => go(NAV_PARENT.taskdetail));

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

    form.innerHTML = `
      <textarea class="input" data-cmt-text placeholder="Комментарий… упоминайте через @email"></textarea>
      <button class="btn primary sm" data-cmt-send style="margin-top:6px;">Отправить</button>`;

    await reloadComments(kind, id, list);
  }

  async function reloadComments(kind, id, list) {
    try {
      const items = await api.get(`${cmtBase(kind, id)}/comments`);
      list.innerHTML = items.length
        ? items.map((c) => `<div class="feed"><div class="it">
            <div class="av">${initials((c.author_id || '').slice(0, 2))}</div>
            <div><span>${esc(c.text)}</span><div class="when">${new Date(c.created_at).toLocaleString('ru')}</div></div>
          </div></div>`).join('')
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
      await api.post(`${cmtBase(kind, id)}/comments`, { text });
      ta.value = '';
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
    } catch (err) {
      toast(err.message, '');
    }
  });

  /* ---------------- my tasks ---------------- */

  // Показ полей в зависимости от scope: проект, исполнитель, дедлайн — только для командных.
  $('#taskScope').addEventListener('change', async () => {
    const scope = $('#taskScope').value;
    const isProj = scope === 'PROJECT';
    const isTeam = scope !== 'PERSONAL';
    $('#taskProject').style.display = isProj ? '' : 'none';
    $('#taskAssignee').style.display = isTeam ? '' : 'none';
    $('#taskDue').style.display = isTeam ? '' : 'none';

    if (isProj) {
      const projects = state.projects.length
        ? state.projects
        : await api.get(`/workspaces/${state.wsId}/projects`);
      state.projects = projects;
      $('#taskProject').innerHTML = projects.map((p) => `<option value="${p.id}">${esc(p.name)}</option>`).join('');
    }
    if (isTeam) {
      // Список участников лаборатории для выбора исполнителя.
      const members = await api.get(`/workspaces/${state.wsId}/members`);
      state.members = members;
      $('#taskAssignee').innerHTML =
        '<option value="">без исполнителя</option>' +
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
    if (scope !== 'PERSONAL') {
      const a = $('#taskAssignee').value;
      if (a) body.assignee_id = a;
    }
    const due = $('#taskDue').value;
    if (due) body.due_date = due;
    try {
      await api.post('/tasks', body);
      $('#taskTitle').value = '';
      $('#taskDesc').value = '';
      $('#taskDue').value = '';
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
    chevron.textContent = hidden ? '▼' : '▶';
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

  /* ---------------- team room ---------------- */
  async function renderTeam() {
    const data = await api.get(`/workspaces/${state.wsId}/team-room`);
    $('#teamPets').innerHTML = data.pets
      .map(
        (p) => `<div class="petmini soft"><div class="av"><div class="hud">${levelOf(p.xp)}</div></div>
          <div class="meta"><b>${esc(p.name)}</b> <span class="mono">ур. ${levelOf(p.xp)} · ${p.xp} XP</span></div></div>`,
      )
      .join('') || '<div class="muted sm">Нет питомцев.</div>';
    $('#teamFeed').innerHTML = data.activity.length
      ? data.activity.map(feedRow).join('')
      : '<div class="muted sm">Пока тихо.</div>';
  }

  /* ---------------- notifications ---------------- */
  async function refreshNotifBadge() {
    const list = await api.get('/notifications');
    const unread = list.filter((n) => !n.is_read).length;
    const badge = $('#notifBadge');
    badge.textContent = unread;
    badge.classList.toggle('hide', unread === 0);
  }

  async function renderNotifications() {
    const list = await api.get('/notifications');
    $('#notifList').innerHTML = list.length
      ? list
          .map(
            (n) => `<div class="task ${n.is_read ? 'done' : ''}" data-notif="${n.id}">
              <div class="t"><b>${esc(n.title)}</b>${n.body ? ' — ' + esc(n.body) : ''}
                <div class="mono">${n.type} · ${new Date(n.created_at).toLocaleString('ru')}</div></div>
              ${n.is_read ? '' : '<span class="chip acc btn-like" data-read="' + n.id + '">прочитать</span>'}
            </div>`,
          )
          .join('')
      : '<div class="muted sm">Уведомлений нет.</div>';
    await refreshNotifBadge();
  }

  document.addEventListener('click', async (e) => {
    const r = e.target.closest('[data-read]');
    if (!r) return;
    await api.patch(`/notifications/${r.dataset.read}/read`, {});
    renderNotifications();
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
