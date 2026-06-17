(function () {
  'use strict';

  const STATUSES = [
    { id: 'TODO', title: 'TODO' },
    { id: 'IN_PROGRESS', title: 'В работе' },
    { id: 'IN_REVIEW', title: 'На проверке' },
    { id: 'DONE', title: 'Готово' },
  ];
  const TYPES = [
    'RESEARCH',
    'WRITING',
    'REVIEW',
    'FORMATTING',
    'DEVELOPMENT',
    'DESIGN',
    'TESTING',
    'DEPLOYMENT',
    'EXPERIMENT',
    'SUBMISSION',
    'RESPONSE_TO_REVIEWER',
    'ADMIN',
    'PERSONAL',
    'OTHER',
  ];
  const PRIORITIES = ['LOW', 'MEDIUM', 'HIGH', 'URGENT'];
  const COLUMN_KEY = 'petpro.taskBoard.columns';

  const state = {
    tasks: [],
    members: [],
    projects: [],
    selected: new Set(),
    hiddenColumns: new Set(readColumns()),
    draggedId: null,
    loading: false,
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

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

  function readColumns() {
    try {
      return JSON.parse(localStorage.getItem(COLUMN_KEY) || '[]');
    } catch {
      return [];
    }
  }

  function writeColumns() {
    try {
      localStorage.setItem(COLUMN_KEY, JSON.stringify(Array.from(state.hiddenColumns)));
    } catch {
      // localStorage is optional for this progressive enhancement.
    }
  }

  function getScopeFilter() {
    return $('.seg[data-filter="scope"] .on')?.dataset.val || 'all';
  }

  function getStatusFilter() {
    return $('.seg[data-filter="status"] .on')?.dataset.val || 'all';
  }

  function getDueFilter() {
    return $('.seg[data-filter="due"] .on')?.dataset.val || 'all';
  }

  function todayIso() {
    return new Date().toISOString().slice(0, 10);
  }

  function memberName(userId) {
    if (!userId) return 'Без исполнителя';
    const member = state.members.find((item) => item.user_id === userId);
    return member?.display_name || member?.email || userId.slice(0, 6);
  }

  function projectName(projectId) {
    if (!projectId) return 'Без проекта';
    const project = state.projects.find((item) => item.id === projectId);
    return project?.name || 'Проект';
  }

  function initials(name) {
    const source = String(name || '?').trim();
    return source
      .split(/[\s._-]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => Array.from(part)[0] || '')
      .join('')
      .toUpperCase() || '?';
  }

  function assigneesOf(task) {
    if (Array.isArray(task.assignees) && task.assignees.length) return task.assignees;
    return task.assignee_id ? [task.assignee_id] : [];
  }

  function passesFilters(task) {
    const query = ($('#taskBoardSearch')?.value || '').trim().toLowerCase();
    const assignee = $('#taskBoardAssignee')?.value || 'all';
    const type = $('#taskBoardType')?.value || 'all';
    const priority = $('#taskBoardPriority')?.value || 'all';
    const scope = getScopeFilter();
    const status = getStatusFilter();
    const due = getDueFilter();

    if (scope === 'team' && task.scope === 'PERSONAL') return false;
    if (scope === 'personal' && task.scope !== 'PERSONAL') return false;
    if (status === 'open' && task.status === 'DONE') return false;
    if (status === 'done' && task.status !== 'DONE') return false;
    if (type !== 'all' && task.type !== type) return false;
    if (priority !== 'all' && task.priority !== priority) return false;
    if (assignee !== 'all' && !assigneesOf(task).includes(assignee)) return false;
    if (query) {
      const haystack = `${task.title || ''} ${task.description || ''} ${task.type || ''} ${task.priority || ''}`.toLowerCase();
      if (!haystack.includes(query)) return false;
    }
    if (due !== 'all') {
      if (!task.due_date) return false;
      const today = todayIso();
      if (due === 'overdue' && !(task.due_date < today && task.status !== 'DONE')) return false;
      if (due === 'soon' && task.due_date < today) return false;
    }
    return true;
  }

  function groupKey(task) {
    const mode = $('#taskBoardGroup')?.value || 'none';
    if (mode === 'scope') return task.scope === 'PERSONAL' ? 'Личные' : 'Командные';
    if (mode === 'project') return projectName(task.project_id);
    if (mode === 'assignee') {
      const assignees = assigneesOf(task);
      return assignees.length ? assignees.map(memberName).join(', ') : 'Без исполнителя';
    }
    return 'Все задачи';
  }

  function statusClass(status) {
    return `status-${String(status || 'TODO').toLowerCase().replace(/_/g, '-')}`;
  }

  function taskCard(task) {
    const selected = state.selected.has(task.id);
    const assignees = assigneesOf(task);
    const due = task.due_date ? `<span class="board-due">${esc(task.due_date)}</span>` : '';
    const project = task.project_id ? `<span class="tag">${esc(projectName(task.project_id))}</span>` : '';
    const avatarStack = assignees.length
      ? `<div class="board-avstack">${assignees.slice(0, 3).map((id) => {
          const name = memberName(id);
          return `<span class="board-av" title="${esc(name)}">${esc(initials(name))}</span>`;
        }).join('')}${assignees.length > 3 ? `<span class="board-av more">+${assignees.length - 3}</span>` : ''}</div>`
      : '<span class="muted sm">без исполнителя</span>';

    return `<article class="acard task-board-card ${statusClass(task.status)} ${selected ? 'selected' : ''}" data-task="${esc(task.id)}" data-board-task="${esc(task.id)}" data-open-task="${esc(task.id)}" draggable="true">
      <div class="task-card-top">
        <label class="task-select" title="Выбрать задачу">
          <input type="checkbox" data-task-select="${esc(task.id)}" ${selected ? 'checked' : ''}>
        </label>
        <span class="prio ${esc(task.priority || 'MEDIUM')}"></span>
        <span class="tag">${esc(task.type || 'OTHER')}</span>
        <span class="tag">${esc(task.scope || '')}</span>
      </div>
      <div class="ttl">${esc(task.title)}</div>
      ${task.description ? `<div class="task-card-desc">${esc(task.description)}</div>` : ''}
      <div class="foot">
        ${avatarStack}
        <span class="grow"></span>
        ${project}
        ${due}
      </div>
      <div class="task-card-move">
        <button class="btn sm" data-task-step="-1" data-task-id="${esc(task.id)}" type="button">←</button>
        <button class="btn sm" data-task-step="1" data-task-id="${esc(task.id)}" type="button">→</button>
      </div>
    </article>`;
  }

  function renderColumn(status, tasks) {
    const visibleTasks = tasks.filter((task) => task.status === status.id);
    return `<section class="kcol task-kcol ${statusClass(status.id)}" data-board-status="${status.id}">
      <div class="kcol-head">
        <span class="statusdot"></span>
        <b>${esc(status.title)}</b>
        <span class="kcol-cnt">${visibleTasks.length}</span>
      </div>
      <div class="kcol-body" data-drop-status="${status.id}">
        ${visibleTasks.length ? visibleTasks.map(taskCard).join('') : '<div class="kcol-empty">Пусто</div>'}
      </div>
    </section>`;
  }

  function renderPicker() {
    const picker = $('#taskColumnPicker');
    if (!picker) return;
    setSafeHtml(picker, STATUSES.map((status) => {
      const checked = !state.hiddenColumns.has(status.id);
      return `<label class="chip btn-like task-column-toggle">
        <input type="checkbox" data-task-column="${status.id}" ${checked ? 'checked' : ''}>
        ${esc(status.title)}
      </label>`;
    }).join(''));
  }

  function renderBulkbar() {
    const bar = $('#taskBulkbar');
    const count = $('#taskBulkCount');
    if (!bar || !count) return;
    count.textContent = String(state.selected.size);
    bar.hidden = state.selected.size === 0;
  }

  function render() {
    const board = $('#taskBoard');
    if (!board) return;
    renderPicker();
    renderBulkbar();

    const tasks = state.tasks.filter(passesFilters);
    const groups = new Map();
    tasks.forEach((task) => {
      const key = groupKey(task);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(task);
    });
    groups.forEach((items) => {
      items.sort((left, right) => {
        const lp = Number(left.position || 0);
        const rp = Number(right.position || 0);
        if (lp !== rp) return lp - rp;
        return String(left.created_at || '').localeCompare(String(right.created_at || ''));
      });
    });

    if (!tasks.length) {
      setSafeHtml(board, '<div class="muted sm task-board-empty">Нет задач под выбранные фильтры.</div>');
      return;
    }

    setSafeHtml(board, Array.from(groups.entries()).map(([name, items]) => {
      const columns = STATUSES
        .filter((status) => !state.hiddenColumns.has(status.id))
        .map((status) => renderColumn(status, items))
        .join('');
      return `<section class="task-swimlane">
        <div class="task-swimlane-head">
          <h3>${esc(name)}</h3>
          <span class="mono">${items.length}</span>
        </div>
        <div class="board task-status-board">${columns}</div>
      </section>`;
    }).join(''));
  }

  function fillFilters() {
    const assignee = $('#taskBoardAssignee');
    const type = $('#taskBoardType');
    const priority = $('#taskBoardPriority');
    if (assignee) {
      setSafeHtml(assignee, '<option value="all">все исполнители</option>' +
        state.members.map((member) => `<option value="${esc(member.user_id)}">${esc(member.display_name || member.email || member.user_id.slice(0, 6))}</option>`).join(''));
    }
    if (type) setSafeHtml(type, '<option value="all">все типы</option>' + TYPES.map((item) => `<option value="${item}">${item}</option>`).join(''));
    if (priority) setSafeHtml(priority, '<option value="all">любой приоритет</option>' + PRIORITIES.map((item) => `<option value="${item}">${item}</option>`).join(''));
  }

  async function loadBoard() {
    if (
      !window.api ||
      !window.api.isAuthed ||
      !window.api.isAuthed() ||
      state.loading ||
      !$('#taskBoard')
    ) {
      return;
    }
    state.loading = true;
    try {
      const [team, personal, workspaces] = await Promise.all([
        window.api.get('/me/tasks'),
        window.api.get('/me/tasks/personal'),
        window.api.get('/workspaces').catch(() => []),
      ]);
      const wsId = workspaces && workspaces[0] && workspaces[0].id;
      const [members, projects] = wsId
        ? await Promise.all([
            window.api.get(`/workspaces/${wsId}/members`).catch(() => []),
            window.api.get(`/workspaces/${wsId}/projects`).catch(() => []),
          ])
        : [[], []];
      const byId = new Map();
      [...team, ...personal].forEach((task) => byId.set(task.id, task));
      state.tasks = Array.from(byId.values());
      state.members = members;
      state.projects = projects;
      fillFilters();
      render();
    } catch (error) {
      const board = $('#taskBoard');
      if (board) setSafeHtml(board, `<div class="muted sm task-board-empty">Не удалось загрузить доску: ${esc(error.message || error)}</div>`);
    } finally {
      state.loading = false;
    }
  }

  function idsInColumn(body) {
    return $$('[data-board-task]', body).map((card) => card.dataset.boardTask).filter(Boolean);
  }

  async function moveTask(taskId, status, order) {
    const previous = state.tasks.map((task) => ({ ...task }));
    const task = state.tasks.find((item) => item.id === taskId);
    if (task) task.status = status;
    render();
    try {
      await window.api.patch(`/tasks/${taskId}/move`, { status, order });
      await loadBoard();
    } catch (error) {
      state.tasks = previous;
      render();
      alert(error.message || 'Не удалось переместить задачу');
    }
  }

  function insertDraggedCard(body, event) {
    const card = $(`[data-board-task="${CSS.escape(state.draggedId)}"]`);
    if (!card || !body) return;
    const cards = $$('[data-board-task]', body).filter((item) => item !== card);
    const before = cards.find((item) => {
      const rect = item.getBoundingClientRect();
      return event.clientY < rect.top + rect.height / 2;
    });
    body.insertBefore(card, before || null);
  }

  document.addEventListener('dragstart', (event) => {
    const card = event.target.closest('[data-board-task]');
    if (!card) return;
    state.draggedId = card.dataset.boardTask;
    card.classList.add('dragging');
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', state.draggedId);
  });

  document.addEventListener('dragend', (event) => {
    event.target.closest('[data-board-task]')?.classList.remove('dragging');
    $$('.kcol-body.drop-hover').forEach((item) => item.classList.remove('drop-hover'));
    state.draggedId = null;
  });

  document.addEventListener('dragover', (event) => {
    const body = event.target.closest('[data-drop-status]');
    if (!body || !state.draggedId) return;
    event.preventDefault();
    body.classList.add('drop-hover');
    insertDraggedCard(body, event);
  });

  document.addEventListener('dragleave', (event) => {
    const body = event.target.closest('[data-drop-status]');
    if (body && !body.contains(event.relatedTarget)) body.classList.remove('drop-hover');
  });

  document.addEventListener('drop', async (event) => {
    const body = event.target.closest('[data-drop-status]');
    if (!body || !state.draggedId) return;
    event.preventDefault();
    body.classList.remove('drop-hover');
    const taskId = state.draggedId;
    const status = body.dataset.dropStatus;
    const order = idsInColumn(body);
    state.draggedId = null;
    await moveTask(taskId, status, order);
  });

  document.addEventListener('click', async (event) => {
    const checkbox = event.target.closest('[data-task-select]');
    if (checkbox) {
      event.stopPropagation();
      const id = checkbox.dataset.taskSelect;
      checkbox.checked ? state.selected.add(id) : state.selected.delete(id);
      render();
      return;
    }

    const stepButton = event.target.closest('[data-task-step]');
    if (stepButton) {
      event.preventDefault();
      event.stopPropagation();
      const task = state.tasks.find((item) => item.id === stepButton.dataset.taskId);
      if (!task) return;
      const current = STATUSES.findIndex((status) => status.id === task.status);
      const next = STATUSES[current + Number(stepButton.dataset.taskStep)];
      if (next) await moveTask(task.id, next.id, []);
      return;
    }

    const columnToggle = event.target.closest('[data-task-column]');
    if (columnToggle) {
      columnToggle.checked ? state.hiddenColumns.delete(columnToggle.dataset.taskColumn) : state.hiddenColumns.add(columnToggle.dataset.taskColumn);
      writeColumns();
      render();
      return;
    }

    const bulk = event.target.closest('[data-task-bulk]');
    if (bulk && state.selected.size) {
      const ids = Array.from(state.selected);
      for (const id of ids) {
        await window.api.patch(`/tasks/${id}/move`, { status: bulk.dataset.taskBulk, order: [] });
      }
      state.selected.clear();
      await loadBoard();
      return;
    }

    if (event.target.closest('#taskBulkClear')) {
      state.selected.clear();
      render();
    }
  });

  document.addEventListener('input', (event) => {
    if (event.target.closest('#taskBoardSearch')) render();
  });

  document.addEventListener('change', (event) => {
    if (event.target.closest('#taskBoardAssignee, #taskBoardType, #taskBoardPriority, #taskBoardGroup')) render();
  });

  document.addEventListener('click', (event) => {
    if (event.target.closest('.filterbar .seg button')) setTimeout(render, 0);
    if (event.target.closest('#newTaskBtn')) setTimeout(loadBoard, 700);
    if (event.target.closest('[data-go="mytasks"]')) setTimeout(loadBoard, 400);
  });

  const teamList = $('#teamTasks');
  if (teamList) {
    new MutationObserver(() => {
      if ($('#screen-mytasks')?.classList.contains('on')) loadBoard();
    }).observe(teamList, { childList: true });
  }

  window.petproTaskBoard = { load: loadBoard, render };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadBoard);
  } else {
    loadBoard();
  }
})();
