(function () {
  'use strict';

  const api = window.api;
  if (!api) return;

  const $ = (selector, root = document) => root.querySelector(selector);

  let workspaceCache = null;
  let auditLoading = false;
  let gamificationLoading = false;

  function clear(node) {
    if (node) node.replaceChildren();
  }

  function text(tag, value, className) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = value == null || value === '' ? '—' : String(value);
    return node;
  }

  function setStatus(selector, message) {
    const node = $(selector);
    if (node) node.textContent = message || '';
  }

  async function currentWorkspaceId() {
    if (workspaceCache) return workspaceCache;
    const workspaces = await api.get('/workspaces');
    workspaceCache = workspaces && workspaces[0] && workspaces[0].id;
    return workspaceCache || null;
  }

  function resetWorkspaceCache() {
    workspaceCache = null;
  }

  function shortId(value) {
    return value ? String(value).slice(0, 8) : 'system';
  }

  function formatDate(value) {
    if (!value) return '';
    try {
      return new Date(value).toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return String(value);
    }
  }

  function formatValue(value) {
    if (value == null || value === '') return '—';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  }

  function changedFields(entry) {
    if (entry.details && Array.isArray(entry.details.changed_fields)) {
      return entry.details.changed_fields;
    }
    const keys = new Set([
      ...Object.keys(entry.before || {}),
      ...Object.keys(entry.after || {}),
    ]);
    return Array.from(keys);
  }

  function renderAuditEntry(entry) {
    const item = document.createElement('div');
    item.className = 'audit-entry';

    const head = document.createElement('div');
    head.className = 'audit-entry-head';

    const title = text('b', entry.action || 'event', 'audit-action');
    const meta = text(
      'span',
      `${formatDate(entry.created_at)} · ${entry.entity_type || 'entity'} · actor ${shortId(entry.actor_id)}`,
      'audit-meta'
    );

    head.append(title, meta);
    item.append(head);

    if (entry.target_user_id) {
      item.append(text('div', `target user ${shortId(entry.target_user_id)}`, 'audit-meta'));
    }

    const fields = changedFields(entry).slice(0, 4);
    if (fields.length) {
      const diff = document.createElement('div');
      diff.className = 'audit-diff';
      fields.forEach((field) => {
        diff.append(text(
          'div',
          `${field}: ${formatValue(entry.before && entry.before[field])} -> ${formatValue(entry.after && entry.after[field])}`
        ));
      });
      item.append(diff);
    }

    return item;
  }

  async function loadAudit() {
    const list = $('#auditList');
    if (!list || auditLoading || !api.isAuthed()) return;

    auditLoading = true;
    clear(list);
    setStatus('#auditStatus', 'Загрузка журнала...');

    try {
      const wsId = await currentWorkspaceId();
      if (!wsId) {
        setStatus('#auditStatus', 'Сначала создайте лабораторию.');
        return;
      }

      const filter = $('#auditEntityFilter')?.value || '';
      const params = new URLSearchParams({ limit: '30' });
      if (filter) params.set('entity_type', filter);

      const rows = await api.get(`/workspaces/${wsId}/audit-log?${params.toString()}`);
      $('#auditCount') && ($('#auditCount').textContent = rows.length ? String(rows.length) : '');
      setStatus(
        '#auditStatus',
        rows.length ? 'Последние изменения в лаборатории.' : 'Пока нет событий для выбранного фильтра.'
      );
      rows.forEach((entry) => list.append(renderAuditEntry(entry)));
    } catch (err) {
      $('#auditCount') && ($('#auditCount').textContent = '');
      if (err && err.status === 403) {
        setStatus('#auditStatus', 'Журнал доступен только OWNER/ADMIN.');
      } else {
        setStatus('#auditStatus', err?.message || 'Не удалось загрузить журнал аудита.');
      }
    } finally {
      auditLoading = false;
    }
  }

  function rule(label, value) {
    const item = document.createElement('div');
    item.className = 'reward-rule';
    item.append(text('b', label), text('span', value));
    return item;
  }

  function renderRewardRules(rules) {
    const root = $('#rewardRules');
    if (!root) return;

    clear(root);
    if (!rules) {
      root.append(text('div', 'Правила наград пока недоступны.', 'note'));
      return;
    }

    const xp = rules.xp || {};
    const coins = rules.coins || {};
    const care = rules.care || {};
    const task = xp.task_completed || {};
    const comments = xp.comment_added || {};
    const articles = xp.article_status || {};
    const games = coins.daily_games || {};
    const teamCare = care.team_task || {};

    [
      rule('Задача команды', `+${task.team || 0} XP, личная +${task.personal || 0} XP, бонус дедлайна +${task.before_due_bonus || 0} XP`),
      rule('Проект DONE', `+${(xp.project_status && xp.project_status.DONE) || 0} XP`),
      rule('Статьи', `submitted +${articles.SUBMITTED || 0}, accepted +${articles.ACCEPTED || 0}, published +${articles.PUBLISHED || 0} XP`),
      rule('Комментарии', `+${comments.amount || 0} XP, лимит ${comments.daily_cap || 0} за ${comments.window_hours || 24} ч`),
      rule('Ежедневный вход', `+${coins.daily_login || 0} монет`),
      rule('Мини-игры', `sudoku +${games.sudoku || 0}, zip +${games.zip || 0}, minesweeper +${games.minesweeper || 0} монет`),
      rule('RPS на стене', `+${coins.rps_win || 0} монет за победу`),
      rule('Уход за питомцем', `командная задача: сытость +${teamCare.hunger || 0}, энергия +${teamCare.energy || 0}, настроение +${teamCare.mood || 0}`),
    ].forEach((node) => root.append(node));
  }

  async function syncGamification() {
    const muted = $('#gamificationMuted');
    const rulesRoot = $('#rewardRules');
    if ((!muted && !rulesRoot) || gamificationLoading || !api.isAuthed()) return;

    gamificationLoading = true;
    setStatus('#gamificationStatus', 'Загрузка настроек...');

    try {
      const [pet, rules] = await Promise.all([
        api.get('/pets/me'),
        api.gamificationRules(),
      ]);
      const isMuted = !!pet.gamification_muted;
      if (muted) muted.checked = isMuted;
      document.body.classList.toggle('gamification-muted', isMuted);
      renderRewardRules(rules);
      setStatus('#gamificationStatus', isMuted ? 'Тихий режим включен.' : 'Тихий режим выключен.');
    } catch (err) {
      setStatus('#gamificationStatus', err?.message || 'Не удалось загрузить настройки геймификации.');
      renderRewardRules(null);
    } finally {
      gamificationLoading = false;
    }
  }

  async function updateGamificationMuted() {
    const muted = $('#gamificationMuted');
    if (!muted || !api.isAuthed()) return;

    muted.disabled = true;
    setStatus('#gamificationStatus', 'Сохранение...');
    try {
      const pet = await api.petSettings({ gamification_muted: muted.checked });
      const isMuted = !!pet.gamification_muted;
      muted.checked = isMuted;
      document.body.classList.toggle('gamification-muted', isMuted);
      setStatus('#gamificationStatus', isMuted ? 'Тихий режим включен.' : 'Тихий режим выключен.');
    } catch (err) {
      muted.checked = !muted.checked;
      setStatus('#gamificationStatus', err?.message || 'Не удалось сохранить настройку.');
    } finally {
      muted.disabled = false;
    }
  }

  function wire() {
    $('#auditRefresh')?.addEventListener('click', loadAudit);
    $('#auditEntityFilter')?.addEventListener('change', loadAudit);
    $('#gamificationMuted')?.addEventListener('change', updateGamificationMuted);

    document.addEventListener('click', (event) => {
      const nav = event.target.closest('[data-go]');
      if (!nav) return;
      if (nav.dataset.go === 'lab') setTimeout(loadAudit, 250);
      if (nav.dataset.go === 'pet') setTimeout(syncGamification, 250);
    });

    document.addEventListener('visibilitychange', () => {
      if (document.hidden) return;
      if ($('#screen-lab')?.classList.contains('on')) loadAudit();
      if ($('#screen-pet')?.classList.contains('on')) syncGamification();
    });

    window.addEventListener('storage', resetWorkspaceCache);
  }

  wire();
  setTimeout(() => {
    if ($('#screen-lab')?.classList.contains('on')) loadAudit();
    if ($('#screen-pet')?.classList.contains('on')) syncGamification();
  }, 700);

  window.petproProductPolish = {
    loadAudit,
    syncGamification,
    resetWorkspaceCache,
  };
})();
