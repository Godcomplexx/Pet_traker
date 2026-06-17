(function () {
  'use strict';

  const state = {
    taskId: null,
    attachments: [],
    previewUrls: new Map(),
  };

  const $ = (selector, root = document) => root.querySelector(selector);

  function esc(value) {
    return String(value ?? '').replace(/[&<>"]/g, (char) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
    }[char]));
  }

  function setSafeHtml(target, html) {
    const doc = new DOMParser().parseFromString(String(html || ''), 'text/html');
    doc.querySelectorAll('script, iframe, object, embed, link, meta').forEach((node) => node.remove());
    doc.querySelectorAll('*').forEach((node) => {
      Array.from(node.attributes).forEach((attr) => {
        const name = attr.name.toLowerCase();
        const value = attr.value.trim();
        if (name.startsWith('on') || ((name === 'href' || name === 'src') && /^javascript:/i.test(value))) {
          node.removeAttribute(attr.name);
        }
      });
    });
    target.replaceChildren(...Array.from(doc.body.childNodes));
  }

  function apiOrigin() {
    return String(window.api?.base || '').replace(/\/api\/?$/, '');
  }

  function apiUrl(path) {
    return `${window.api.base}${path}`;
  }

  function downloadUrl(att) {
    return `${apiOrigin()}${att.download_url}`;
  }

  function authHeaders() {
    const token = window.api?.getTokens?.()?.access_token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  function setStatus(text) {
    const node = $('#taskAttachmentStatus');
    if (node) node.textContent = text || '';
  }

  function formatSize(bytes) {
    const value = Number(bytes || 0);
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
    return `${(value / 1024 / 1024).toFixed(1)} MB`;
  }

  function isImage(att) {
    return String(att.content_type || '').startsWith('image/');
  }

  function icon(att) {
    if (isImage(att)) return 'IMG';
    if (att.content_type === 'application/pdf') return 'PDF';
    if (String(att.original_name || '').match(/\.(csv|xls|xlsx)$/i)) return 'XLS';
    if (String(att.original_name || '').match(/\.(doc|docx)$/i)) return 'DOC';
    return 'FILE';
  }

  function setTaskId(taskId) {
    if (!taskId || state.taskId === taskId) return;
    state.taskId = taskId;
    if ($('#screen-taskdetail')?.classList.contains('on')) loadAttachments();
  }

  function clearPreviewUrls() {
    state.previewUrls.forEach((url) => URL.revokeObjectURL(url));
    state.previewUrls.clear();
  }

  async function hydratePreviews() {
    for (const att of state.attachments) {
      if (!isImage(att) || state.previewUrls.has(att.id)) continue;
      try {
        const res = await fetch(downloadUrl(att), { headers: authHeaders() });
        if (!res.ok) continue;
        const blob = await res.blob();
        state.previewUrls.set(att.id, URL.createObjectURL(blob));
      } catch {
        // Preview is optional; download still works.
      }
    }
    render(false);
  }

  function render(loadPreviews = true) {
    const count = $('#taskAttachmentCount');
    const list = $('#taskAttachmentList');
    if (count) count.textContent = String(state.attachments.length);
    if (!list) return;
    if (!state.attachments.length) {
      setSafeHtml(list, '<div class="muted sm task-attachment-empty">Файлов пока нет.</div>');
      return;
    }
    setSafeHtml(list, state.attachments.map((att) => {
      const preview = state.previewUrls.has(att.id)
        ? `<img class="task-attachment-preview" src="${esc(state.previewUrls.get(att.id))}" alt="${esc(att.original_name)}">`
        : `<div class="task-attachment-icon">${esc(icon(att))}</div>`;
      return `<div class="task-attachment-item" data-attachment="${esc(att.id)}">
        ${preview}
        <div class="task-attachment-meta">
          <b>${esc(att.original_name)}</b>
          <span class="mono">v${esc(att.version)} · ${esc(formatSize(att.size_bytes))} · ${esc(att.content_type)}</span>
        </div>
        <button class="btn sm" data-attachment-download="${esc(att.id)}" type="button">Скачать</button>
        <button class="btn sm" data-attachment-delete="${esc(att.id)}" type="button">×</button>
      </div>`;
    }).join(''));
    if (loadPreviews) hydratePreviews();
  }

  async function loadAttachments() {
    if (!window.api || !state.taskId) return;
    setStatus('');
    try {
      clearPreviewUrls();
      state.attachments = await window.api.get(`/tasks/${state.taskId}/attachments`);
      render();
    } catch (error) {
      const list = $('#taskAttachmentList');
      if (list) setSafeHtml(list, `<div class="muted sm">Не удалось загрузить файлы: ${esc(error.message || error)}</div>`);
    }
  }

  async function uploadSelected() {
    const input = $('#taskAttachmentFile');
    const file = input?.files?.[0];
    if (!file || !state.taskId) return;
    setStatus('Загрузка...');
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await fetch(apiUrl(`/tasks/${state.taskId}/attachments`), {
        method: 'POST',
        headers: authHeaders(),
        body: form,
      });
      const body = await res.json().catch(() => null);
      if (!res.ok) throw new Error((body && (body.detail || body.message)) || `HTTP ${res.status}`);
      input.value = '';
      setStatus('Файл загружен.');
      await loadAttachments();
    } catch (error) {
      setStatus(error.message || 'Не удалось загрузить файл');
    }
  }

  async function downloadAttachment(id) {
    const att = state.attachments.find((item) => item.id === id);
    if (!att) return;
    const res = await fetch(downloadUrl(att), { headers: authHeaders() });
    if (!res.ok) {
      setStatus('Не удалось скачать файл');
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = att.original_name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 500);
  }

  async function deleteAttachment(id) {
    try {
      await window.api.del(`/attachments/${id}`);
      setStatus('Файл удалён.');
      await loadAttachments();
    } catch (error) {
      setStatus(error.message || 'Не удалось удалить файл');
    }
  }

  document.addEventListener('click', (event) => {
    const task = event.target.closest('[data-open-task]');
    if (task) setTaskId(task.dataset.openTask);
    const notif = event.target.closest('#notifList [data-entity-type="task"][data-entity-id]');
    if (notif) setTaskId(notif.dataset.entityId);
  }, true);

  document.addEventListener('click', async (event) => {
    if (event.target.closest('#taskAttachmentUpload')) {
      await uploadSelected();
      return;
    }
    const download = event.target.closest('[data-attachment-download]');
    if (download) {
      await downloadAttachment(download.dataset.attachmentDownload);
      return;
    }
    const del = event.target.closest('[data-attachment-delete]');
    if (del) {
      await deleteAttachment(del.dataset.attachmentDelete);
    }
  });

  const observer = new MutationObserver(() => {
    if ($('#screen-taskdetail')?.classList.contains('on') && state.taskId) {
      loadAttachments();
    }
  });
  if (document.body) observer.observe(document.body, { attributes: true, subtree: true, attributeFilter: ['class'] });

  window.petproTaskAttachments = {
    open: setTaskId,
    load: loadAttachments,
  };
})();
