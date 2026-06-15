(function () {
  'use strict';

  const boxSelector = '.task-chat-box';
  let mePromise = null;
  let currentTaskId = null;
  let typingTimer = null;

  function getBox() {
    return document.querySelector(boxSelector);
  }

  function getMe() {
    if (!window.api || !window.api.isAuthed || !window.api.isAuthed()) {
      return Promise.resolve(null);
    }
    if (!mePromise) {
      mePromise = window.api.get('/auth/me').catch(() => null);
    }
    return mePromise;
  }

  function scrollChatToBottom(box) {
    const list = box && box.querySelector('.cmt-list');
    if (!list) return;
    list.scrollTop = list.scrollHeight;
  }

  function esc(value) {
    return String(value ?? '').replace(/[&<>"]/g, (char) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
    }[char]));
  }

  function setTaskId(taskId) {
    if (taskId) currentTaskId = taskId;
  }

  function ensureTyping(box) {
    if (!box || box.querySelector('.task-chat-typing')) return;
    const typing = document.createElement('div');
    typing.className = 'task-chat-typing muted sm';
    typing.hidden = true;
    box.querySelector('.cmt-list')?.after(typing);
  }

  function showTyping(name) {
    const box = getBox();
    const typing = box?.querySelector('.task-chat-typing');
    if (!typing) return;
    typing.textContent = `${name || 'Участник'} печатает...`;
    typing.hidden = false;
    clearTimeout(typingTimer);
    typingTimer = setTimeout(() => {
      typing.hidden = true;
    }, 2200);
  }

  async function appendComment(comment) {
    if (!comment || comment.entity_id !== currentTaskId) return;
    const box = getBox();
    const list = box?.querySelector('.cmt-list');
    if (!box || !list || list.querySelector(`[data-live-comment="${CSS.escape(comment.comment_id)}"]`)) {
      return;
    }
    const me = await getMe();
    const isMine = me && comment.author_id === me.id;
    const name = comment.author_name || (isMine ? me.display_name || me.email : comment.author_id);
    const row = document.createElement('div');
    row.className = `comment-row${isMine ? ' mine' : ''}`;
    row.dataset.liveComment = comment.comment_id || '';
    row.innerHTML = `<div class="comment-body">
      <div class="comment-meta"><b>${esc(name)}</b><span>${esc(new Date(comment.created_at || Date.now()).toLocaleString('ru'))}</span></div>
      <div class="comment-text">${esc(comment.text)}</div>
    </div>`;
    list.appendChild(row);
    scrollChatToBottom(box);
  }

  function handleLive(event) {
    const payload = event?.payload || {};
    if (payload.entity_type !== 'task' || payload.entity_id !== currentTaskId) return;
    if (event.type === 'comment.created') appendComment(payload);
    if (event.type === 'comment.updated' || event.type === 'comment.deleted') {
      document.dispatchEvent(new CustomEvent('petpro:task-chat-stale', { detail: payload }));
    }
  }

  async function markOwnMessages(box) {
    const me = await getMe();
    if (!box || !me) return;

    const names = new Set(
      [me.display_name, me.email].filter(Boolean).map((value) => String(value).trim())
    );
    if (!names.size) return;

    box.querySelectorAll('.comment-row').forEach((row) => {
      const name = row.querySelector('.comment-meta b')?.textContent.trim();
      row.classList.toggle('mine', !!name && names.has(name));
    });
  }

  function enhanceTaskChat() {
    const box = getBox();
    if (!box) return;

    const textarea = box.querySelector('[data-cmt-text]');
    if (textarea) {
      textarea.placeholder = 'Сообщение в чат задачи...';
      textarea.rows = 3;
    }
    ensureTyping(box);

    const send = box.querySelector('[data-cmt-send]');
    const actions = send && send.closest('.row');
    if (actions) actions.classList.add('cmt-actions');

    markOwnMessages(box);
    requestAnimationFrame(() => scrollChatToBottom(box));
  }

  document.addEventListener('keydown', (event) => {
    const textarea = event.target.closest(`${boxSelector} [data-cmt-text]`);
    if (!textarea) return;
    if (event.key !== 'Enter' || event.shiftKey || event.ctrlKey || event.altKey || event.metaKey) {
      return;
    }

    event.preventDefault();
    textarea.closest(boxSelector)?.querySelector('[data-cmt-send]')?.click();
  });

  document.addEventListener('input', (event) => {
    const textarea = event.target.closest(`${boxSelector} [data-cmt-text]`);
    if (!textarea || !currentTaskId || !window.api?.isAuthed?.()) return;
    const now = Date.now();
    const last = Number(textarea.dataset.typingSent || 0);
    if (now - last < 1800) return;
    textarea.dataset.typingSent = String(now);
    window.api.post(`/tasks/${currentTaskId}/typing`, {}).catch(() => {});
  });

  document.addEventListener('click', (event) => {
    const task = event.target.closest('[data-open-task]');
    if (task) setTaskId(task.dataset.openTask);
    const notif = event.target.closest('#notifList [data-entity-type="task"][data-entity-id]');
    if (notif) setTaskId(notif.dataset.entityId);
  }, true);

  document.addEventListener(
    'click',
    (event) => {
      if (!event.target.closest(`${boxSelector} [data-cmt-send]`)) return;
      setTimeout(enhanceTaskChat, 80);
    },
    true
  );

  const observer = new MutationObserver((mutations) => {
    if (
      mutations.some(
        (mutation) =>
          mutation.target instanceof Element &&
          (mutation.target.matches(boxSelector) || mutation.target.closest(boxSelector))
      )
    ) {
      enhanceTaskChat();
    }
  });

  if (document.body) {
    observer.observe(document.body, { childList: true, subtree: true });
    enhanceTaskChat();
  } else {
    document.addEventListener('DOMContentLoaded', () => {
      observer.observe(document.body, { childList: true, subtree: true });
      enhanceTaskChat();
    });
  }

  window.addEventListener('petpro:live', (event) => handleLive(event.detail));
  window.addEventListener('petpro:task-typing', (event) => {
    const payload = event.detail || {};
    if (payload.task_id === currentTaskId) showTyping(payload.display_name);
  });

  window.petproTaskChat = {
    open: setTaskId,
    enhance: enhanceTaskChat,
  };
})();
