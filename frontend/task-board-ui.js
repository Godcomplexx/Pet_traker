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

  function writeColumns(hiddenColumns) {
    try {
      localStorage.setItem(COLUMN_KEY, JSON.stringify(Array.from(hiddenColumns)));
    } catch {
      // localStorage is optional for this progressive enhancement.
    }
  }

  function taskCard(task, ctx) {
    const selected = ctx.state.selected.has(task.id);
    const assignees = ctx.assigneesOf(task);
    const due = task.due_date ? `<span class="board-due">${esc(task.due_date)}</span>` : '';
    const project = task.project_id ? `<span class="tag">${esc(ctx.projectName(task.project_id))}</span>` : '';
    const avatarStack = assignees.length
      ? `<div class="board-avstack">${assignees.slice(0, 3).map((id) => {
          const name = ctx.memberName(id);
          return `<span class="board-av" title="${esc(name)}">${esc(ctx.initials(name))}</span>`;
        }).join('')}${assignees.length > 3 ? `<span class="board-av more">+${assignees.length - 3}</span>` : ''}</div>`
      : '<span class="muted sm">без исполнителя</span>';

    return `<article class="acard task-board-card ${ctx.statusClass(task.status)} ${selected ? 'selected' : ''}" data-task="${esc(task.id)}" data-board-task="${esc(task.id)}" data-open-task="${esc(task.id)}" draggable="true">
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

  function renderColumn(status, tasks, ctx) {
    const visibleTasks = tasks.filter((task) => task.status === status.id);
    return `<section class="kcol task-kcol ${ctx.statusClass(status.id)}" data-board-status="${status.id}">
      <div class="kcol-head">
        <span class="statusdot"></span>
        <b>${esc(status.title)}</b>
        <span class="kcol-cnt">${visibleTasks.length}</span>
      </div>
      <div class="kcol-body" data-drop-status="${status.id}">
        ${visibleTasks.length ? visibleTasks.map((task) => taskCard(task, ctx)).join('') : '<div class="kcol-empty">Пусто</div>'}
      </div>
    </section>`;
  }

  function renderPicker(picker, hiddenColumns) {
    setSafeHtml(picker, STATUSES.map((status) => {
      const checked = !hiddenColumns.has(status.id);
      return `<label class="chip btn-like task-column-toggle">
        <input type="checkbox" data-task-column="${status.id}" ${checked ? 'checked' : ''}>
        ${esc(status.title)}
      </label>`;
    }).join(''));
  }

  function fillFilters({ assignee, type, priority, members }) {
    if (assignee) {
      setSafeHtml(assignee, '<option value="all">все исполнители</option>' +
        members.map((member) => `<option value="${esc(member.user_id)}">${esc(member.display_name || member.email || member.user_id.slice(0, 6))}</option>`).join(''));
    }
    if (type) setSafeHtml(type, '<option value="all">все типы</option>' + TYPES.map((item) => `<option value="${item}">${item}</option>`).join(''));
    if (priority) setSafeHtml(priority, '<option value="all">любой приоритет</option>' + PRIORITIES.map((item) => `<option value="${item}">${item}</option>`).join(''));
  }

  window.petproTaskBoardUi = {
    STATUSES,
    TYPES,
    PRIORITIES,
    esc,
    fillFilters,
    readColumns,
    renderColumn,
    renderPicker,
    setSafeHtml,
    writeColumns,
  };
})();
