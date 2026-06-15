(function () {
  'use strict';

  let source = null;
  let reconnectTimer = null;
  let boardTimer = null;
  let notificationTimer = null;

  const TASK_EVENTS = new Set(['task.created', 'task.updated', 'task.moved']);
  const DETAIL_EVENTS = new Set([
    'task.updated',
    'task.moved',
    'task.checklist_updated',
    'attachment.created',
    'attachment.deleted',
  ]);
  const NOTIFICATION_EVENTS = new Set([
    'notification.created',
    'notification.read',
    'notifications.read_all',
  ]);

  function esc(value) {
    return String(value ?? '').replace(/[&<>"]/g, (char) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
    }[char]));
  }

  function tokens() {
    return window.api?.getTokens?.();
  }

  function eventUrl() {
    const access = tokens()?.access_token;
    if (!access || !window.api?.base) return null;
    return `${window.api.base}/live/events?token=${encodeURIComponent(access)}`;
  }

  function setStatus(connected) {
    document.documentElement.classList.toggle('live-connected', connected);
    document.documentElement.classList.toggle('live-disconnected', !connected);
  }

  function scheduleReconnect(delay = 2500) {
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connect, delay);
  }

  function debounceBoard() {
    clearTimeout(boardTimer);
    boardTimer = setTimeout(() => {
      window.petproTaskBoard?.load?.();
    }, 250);
  }

  function updateUnreadClasses(notifications) {
    const unreadTaskIds = new Set(
      notifications
        .filter((item) => !item.is_read && item.type === 'MENTION' && item.entity_type === 'task')
        .map((item) => item.entity_id)
        .filter(Boolean)
    );
    document.querySelectorAll('[data-task]').forEach((node) => {
      const hasUnread = unreadTaskIds.has(node.dataset.task);
      node.classList.toggle('has-unread-comment', hasUnread);
      const chip = node.querySelector('[data-unread-comment-chip]');
      if (chip) chip.hidden = !hasUnread;
    });
  }

  function renderNotificationList(notifications) {
    const list = document.querySelector('#notifList');
    if (!list || !document.querySelector('#screen-notif')?.classList.contains('on')) return;
    const rows = notifications.length
      ? notifications.map((item) => `<div class="task ${item.is_read ? 'done' : ''}" data-notif="${esc(item.id)}"
          data-entity-type="${esc(item.entity_type || '')}" data-entity-id="${esc(item.entity_id || '')}"
          style="cursor:pointer;">
          <div class="t"><b>${esc(item.title)}</b>${item.body ? ' — ' + esc(item.body) : ''}
            <div class="mono">${esc(new Date(item.created_at).toLocaleString('ru'))}${item.entity_type ? ' · нажмите, чтобы открыть' : ''}</div>
          </div>
          ${item.is_read ? '' : `<span class="chip acc btn-like" data-read="${esc(item.id)}">прочитать</span>`}
        </div>`).join('')
      : '<div class="muted sm">Уведомлений нет.</div>';
    list.innerHTML = rows;
  }

  async function refreshNotifications() {
    if (!window.api?.isAuthed?.()) return;
    clearTimeout(notificationTimer);
    notificationTimer = setTimeout(async () => {
      const badge = document.querySelector('#notifBadge');
      try {
        const allowed = new Set(['TASK_ASSIGNED', 'DEADLINE', 'MENTION']);
        const notifications = (await window.api.get('/notifications')).filter((item) => allowed.has(item.type));
        const unread = notifications.filter((item) => !item.is_read).length;
        if (badge) {
          badge.textContent = String(unread);
          badge.classList.toggle('hide', unread === 0);
        }
        updateUnreadClasses(notifications);
        renderNotificationList(notifications);
      } catch {
        // Keep the existing badge/list if the refresh races with logout.
      }
    }, 120);
  }

  function handleDetail(event) {
    const payload = event.payload || {};
    if (!DETAIL_EVENTS.has(event.type)) return;
    if (event.type === 'task.checklist_updated' && payload.task_id) {
      window.petproTaskChecklist?.load?.();
    }
    if ((event.type === 'attachment.created' || event.type === 'attachment.deleted') && payload.task_id) {
      window.petproTaskAttachments?.load?.();
    }
  }

  function handleEvent(raw) {
    const event = JSON.parse(raw.data);
    window.dispatchEvent(new CustomEvent('petpro:live', { detail: event }));

    if (TASK_EVENTS.has(event.type)) debounceBoard();
    if (NOTIFICATION_EVENTS.has(event.type)) refreshNotifications();
    if (event.type === 'comment.created' || event.type === 'comment.updated' || event.type === 'comment.deleted') {
      refreshNotifications();
    }
    handleDetail(event);
  }

  function connect() {
    clearTimeout(reconnectTimer);
    if (!window.api?.isAuthed?.()) return;
    const url = eventUrl();
    if (!url) return;
    if (source) source.close();

    source = new EventSource(url);
    source.addEventListener('live.ready', () => {
      setStatus(true);
      refreshNotifications();
    });
    [
      'notification.created',
      'notification.read',
      'notifications.read_all',
      'comment.created',
      'comment.updated',
      'comment.deleted',
      'task.created',
      'task.updated',
      'task.moved',
      'task.checklist_updated',
      'attachment.created',
      'attachment.deleted',
    ].forEach((type) => source.addEventListener(type, handleEvent));
    source.addEventListener('task.typing', (raw) => {
      const event = JSON.parse(raw.data);
      window.dispatchEvent(new CustomEvent('petpro:task-typing', { detail: event.payload || {} }));
    });
    source.onerror = () => {
      setStatus(false);
      if (source) source.close();
      source = null;
      scheduleReconnect();
    };
  }

  function disconnect() {
    clearTimeout(reconnectTimer);
    if (source) source.close();
    source = null;
    setStatus(false);
  }

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      refreshNotifications();
      if (!source) connect();
    }
  });
  document.addEventListener('click', (event) => {
    if (event.target.closest('[data-go="notif"]')) refreshNotifications();
  });

  window.petproLive = { connect, disconnect, refreshNotifications };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', connect);
  } else {
    connect();
  }
})();
