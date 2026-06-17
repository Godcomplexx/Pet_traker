(function () {
  'use strict';

  const templates = {
    article: [
      ['SUBTASK', 'Собрать источники'],
      ['SUBTASK', 'Сделать черновик'],
      ['CHECK', 'Проверить ссылки'],
      ['CHECK', 'Подготовить финальную версию'],
    ],
    experiment: [
      ['SUBTASK', 'Подготовить протокол'],
      ['CHECK', 'Проверить материалы'],
      ['SUBTASK', 'Собрать результаты'],
      ['CHECK', 'Занести данные в таблицу'],
    ],
    review: [
      ['CHECK', 'Проверить критерии готовности'],
      ['CHECK', 'Оставить комментарии'],
      ['SUBTASK', 'Исправить замечания'],
    ],
  };

  const state = {
    taskId: null,
    items: [],
    loading: false,
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

  function setTaskId(taskId) {
    if (!taskId || state.taskId === taskId) return;
    state.taskId = taskId;
    if ($('#screen-taskdetail')?.classList.contains('on')) loadChecklist();
  }

  function renderProgress() {
    const total = state.items.length;
    const done = state.items.filter((item) => item.is_done).length;
    const count = $('#taskChecklistCount');
    const fill = $('#taskChecklistFill');
    if (count) count.textContent = `${done}/${total}`;
    if (fill) fill.style.width = total ? `${Math.round((done / total) * 100)}%` : '0%';
  }

  function render() {
    const list = $('#taskChecklistList');
    if (!list) return;
    renderProgress();
    if (!state.items.length) {
      setSafeHtml(list, '<div class="muted sm task-checklist-empty">Пока нет пунктов. Добавьте чеклист или примените шаблон.</div>');
      return;
    }
    setSafeHtml(list, state.items.map((item, index) => `
      <div class="task-check-item ${item.is_done ? 'done' : ''}" data-check-item="${esc(item.id)}" data-check-kind="${esc(item.kind)}">
        <label class="task-check-toggle">
          <input type="checkbox" data-check-toggle="${esc(item.id)}" ${item.is_done ? 'checked' : ''}>
        </label>
        <span class="tag">${item.kind === 'SUBTASK' ? 'подзадача' : 'пункт'}</span>
        <span class="task-check-title">${esc(item.title)}</span>
        <button class="btn sm" data-check-move="${esc(item.id)}" data-dir="-1" ${index === 0 ? 'disabled' : ''} type="button">↑</button>
        <button class="btn sm" data-check-move="${esc(item.id)}" data-dir="1" ${index === state.items.length - 1 ? 'disabled' : ''} type="button">↓</button>
        <button class="btn sm" data-check-delete="${esc(item.id)}" type="button">×</button>
      </div>
    `).join(''));
  }

  async function loadChecklist() {
    if (!window.api || !state.taskId || state.loading) return;
    state.loading = true;
    const list = $('#taskChecklistList');
    if (list) setSafeHtml(list, '<div class="muted sm">Загрузка...</div>');
    try {
      state.items = await window.api.get(`/tasks/${state.taskId}/checklist`);
      render();
    } catch (error) {
      if (list) setSafeHtml(list, `<div class="muted sm">Не удалось загрузить чеклист: ${esc(error.message || error)}</div>`);
    } finally {
      state.loading = false;
    }
  }

  async function addItem(title, kind) {
    if (!title.trim() || !state.taskId) return;
    await window.api.post(`/tasks/${state.taskId}/checklist`, {
      title: title.trim(),
      kind,
    });
    $('#taskChecklistInput').value = '';
    await loadChecklist();
  }

  async function reorder(itemId, dir) {
    const index = state.items.findIndex((item) => item.id === itemId);
    const next = index + dir;
    if (index < 0 || next < 0 || next >= state.items.length) return;
    const copy = state.items.slice();
    [copy[index], copy[next]] = [copy[next], copy[index]];
    state.items = copy;
    render();
    await window.api.patch(`/tasks/${state.taskId}/checklist/reorder`, {
      order: copy.map((item) => item.id),
    });
    await loadChecklist();
  }

  async function applyTemplate(name) {
    const rows = templates[name] || [];
    for (const [kind, title] of rows) {
      await window.api.post(`/tasks/${state.taskId}/checklist`, { title, kind });
    }
    await loadChecklist();
  }

  document.addEventListener('click', (event) => {
    const task = event.target.closest('[data-open-task]');
    if (task) setTaskId(task.dataset.openTask);
    const notif = event.target.closest('#notifList [data-entity-type="task"][data-entity-id]');
    if (notif) setTaskId(notif.dataset.entityId);
  }, true);

  document.addEventListener('click', async (event) => {
    const add = event.target.closest('#taskChecklistAdd');
    if (add) {
      await addItem($('#taskChecklistInput')?.value || '', $('#taskChecklistKind')?.value || 'CHECK');
      return;
    }

    const toggle = event.target.closest('[data-check-toggle]');
    if (toggle) {
      await window.api.patch(`/task-checklist/${toggle.dataset.checkToggle}`, {
        is_done: toggle.checked,
      });
      await loadChecklist();
      return;
    }

    const move = event.target.closest('[data-check-move]');
    if (move) {
      await reorder(move.dataset.checkMove, Number(move.dataset.dir));
      return;
    }

    const del = event.target.closest('[data-check-delete]');
    if (del) {
      await window.api.del(`/task-checklist/${del.dataset.checkDelete}`);
      await loadChecklist();
      return;
    }

    const template = event.target.closest('[data-task-template]');
    if (template) {
      await applyTemplate(template.dataset.taskTemplate);
    }
  });

  document.addEventListener('keydown', async (event) => {
    if (!event.target.closest('#taskChecklistInput')) return;
    if (event.key !== 'Enter') return;
    event.preventDefault();
    await addItem($('#taskChecklistInput')?.value || '', $('#taskChecklistKind')?.value || 'CHECK');
  });

  const observer = new MutationObserver(() => {
    if ($('#screen-taskdetail')?.classList.contains('on') && state.taskId) {
      loadChecklist();
    }
  });
  if (document.body) observer.observe(document.body, { attributes: true, subtree: true, attributeFilter: ['class'] });

  window.petproTaskChecklist = {
    open: setTaskId,
    load: loadChecklist,
  };
})();
