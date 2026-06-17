"""Workspace demo content for first-run onboarding."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import (
    ArticleRole,
    ArticleStatus,
    ProjectRole,
    ProjectStatus,
    ProjectType,
    TaskPriority,
    TaskScope,
    TaskStatus,
    TaskType,
    TaskVisibility,
)
from app.models import Article, ArticleMember, Comment, Project, ProjectMember, Task, TaskChecklistItem, WallPost


async def seed_workspace_demo(db: AsyncSession, *, workspace_id: str, user_id: str) -> None:
    """Create a compact, realistic starter workspace once per workspace."""
    if await _has_demo_content(db, workspace_id):
        return
    today = date.today()
    project = await _create_demo_project(db, workspace_id, user_id, today)
    article = await _create_demo_article(db, workspace_id, user_id, project.id, today)
    tasks = await _create_demo_tasks(db, workspace_id, user_id, project.id, article.id, today)
    _add_demo_checklist_and_comment(db, workspace_id, user_id, tasks[1].id)
    _add_demo_wall_post(db, workspace_id, user_id, datetime.now(timezone.utc))


async def _has_demo_content(db: AsyncSession, workspace_id: str) -> bool:
    project_count = await db.scalar(select(func.count(Project.id)).where(Project.workspace_id == workspace_id))
    article_count = await db.scalar(select(func.count(Article.id)).where(Article.workspace_id == workspace_id))
    task_count = await db.scalar(select(func.count(Task.id)).where(Task.workspace_id == workspace_id))
    return bool((project_count or 0) + (article_count or 0) + (task_count or 0))


async def _create_demo_project(db: AsyncSession, workspace_id: str, user_id: str, today: date) -> Project:
    project = Project(
        workspace_id=workspace_id,
        owner_id=user_id,
        name="Демо-проект: исследовательский спринт",
        description="Стартовый проект показывает задачи, статью, дедлайны и kanban-статусы.",
        type=ProjectType.RESEARCH,
        status=ProjectStatus.ACTIVE,
        deadline=today + timedelta(days=21),
        position=0,
    )
    db.add(project)
    await db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user_id, role=ProjectRole.PROJECT_OWNER))
    return project


async def _create_demo_article(
    db: AsyncSession, workspace_id: str, user_id: str, project_id: str, today: date
) -> Article:
    article = Article(
        workspace_id=workspace_id,
        project_id=project_id,
        owner_id=user_id,
        title="Демо-статья: план эксперимента",
        description="Черновик публикации для проверки article board, задач статьи и обсуждений.",
        status=ArticleStatus.WRITING,
        target_journal="LabMate Demo Journal",
        deadline=today + timedelta(days=35),
        position=0,
    )
    db.add(article)
    await db.flush()
    db.add(ArticleMember(article_id=article.id, user_id=user_id, role=ArticleRole.AUTHOR))
    return article


async def _create_demo_tasks(
    db: AsyncSession,
    workspace_id: str,
    user_id: str,
    project_id: str,
    article_id: str,
    today: date,
) -> list[Task]:
    tasks = [
        _task({"workspace_id": workspace_id, "user_id": user_id, "title": "Собрать требования к эксперименту", "scope": TaskScope.PROJECT, "type": TaskType.RESEARCH, "priority": TaskPriority.HIGH, "due_date": today + timedelta(days=3), "project_id": project_id}),
        _task({"workspace_id": workspace_id, "user_id": user_id, "title": "Подготовить протокол и чеклист запуска", "scope": TaskScope.PROJECT, "type": TaskType.EXPERIMENT, "priority": TaskPriority.MEDIUM, "due_date": today + timedelta(days=7), "project_id": project_id, "status": TaskStatus.IN_PROGRESS}),
        _task({"workspace_id": workspace_id, "user_id": user_id, "title": "Написать введение для демо-статьи", "scope": TaskScope.ARTICLE, "type": TaskType.WRITING, "priority": TaskPriority.MEDIUM, "due_date": today + timedelta(days=10), "article_id": article_id, "status": TaskStatus.IN_REVIEW}),
        _task({"workspace_id": workspace_id, "user_id": user_id, "title": "Пригласить коллегу в лабораторию", "scope": TaskScope.WORKSPACE, "type": TaskType.ADMIN, "priority": TaskPriority.LOW, "due_date": today + timedelta(days=14), "position": 3}),
        _personal_task(user_id, today + timedelta(days=1)),
    ]
    db.add_all(tasks)
    await db.flush()
    return tasks


def _task(spec: dict) -> Task:
    user_id = spec["user_id"]
    return Task(
        workspace_id=spec["workspace_id"],
        project_id=spec.get("project_id"),
        article_id=spec.get("article_id"),
        owner_id=user_id,
        created_by=user_id,
        assignee_id=user_id,
        assignees=[user_id],
        title=spec["title"],
        description="Демо-задача показывает работу доски, дедлайнов и detail-view.",
        scope=spec["scope"],
        visibility=_visibility(spec["scope"]),
        status=spec.get("status", TaskStatus.TODO),
        type=spec["type"],
        priority=spec["priority"],
        due_date=spec["due_date"],
        position=spec.get("position", 0),
    )


def _personal_task(user_id: str, due_date: date) -> Task:
    return Task(
        workspace_id=None,
        owner_id=user_id,
        created_by=user_id,
        assignee_id=user_id,
        assignees=[user_id],
        title="Личная задача: настроить питомца",
        description="Личные задачи видны только владельцу и не попадают в активность workspace.",
        scope=TaskScope.PERSONAL,
        visibility=TaskVisibility.PRIVATE,
        status=TaskStatus.TODO,
        type=TaskType.PERSONAL,
        priority=TaskPriority.LOW,
        due_date=due_date,
        position=0,
    )


def _visibility(scope: TaskScope) -> TaskVisibility:
    return {
        TaskScope.PROJECT: TaskVisibility.PROJECT,
        TaskScope.ARTICLE: TaskVisibility.ARTICLE,
        TaskScope.WORKSPACE: TaskVisibility.WORKSPACE,
    }.get(scope, TaskVisibility.PRIVATE)


def _add_demo_checklist_and_comment(db: AsyncSession, workspace_id: str, user_id: str, task_id: str) -> None:
    db.add_all(
        [
            TaskChecklistItem(task_id=task_id, created_by=user_id, title="Проверить доступность данных", kind="CHECK", is_done=True, position=0),
            TaskChecklistItem(task_id=task_id, created_by=user_id, title="Согласовать критерии качества", kind="CHECK", position=1),
            TaskChecklistItem(task_id=task_id, created_by=user_id, title="Подзадача: подготовить шаблон отчета", kind="SUBTASK", position=2),
        ]
    )
    db.add(
        Comment(
            workspace_id=workspace_id,
            task_id=task_id,
            author_id=user_id,
            text="Стартовый комментарий: здесь можно вести быстрый чат по задаче.",
            visibility=TaskVisibility.PROJECT,
        )
    )


def _add_demo_wall_post(db: AsyncSession, workspace_id: str, user_id: str, created_at: datetime) -> None:
    db.add(
        WallPost(
            workspace_id=workspace_id,
            author_id=user_id,
            text="Добро пожаловать в LabMate. Это демо-лаборатория для проверки основных сценариев.",
            created_at=created_at,
        )
    )
