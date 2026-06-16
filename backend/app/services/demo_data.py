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
from app.models import (
    Article,
    ArticleMember,
    Comment,
    Project,
    ProjectMember,
    Task,
    TaskChecklistItem,
    WallPost,
)


async def seed_workspace_demo(db: AsyncSession, *, workspace_id: str, user_id: str) -> None:
    """Create a compact, realistic starter workspace.

    The function is intentionally idempotent for a workspace: if any work items already
    exist, it leaves the workspace untouched.
    """
    existing_items = await db.scalar(
        select(func.count(Project.id)).where(Project.workspace_id == workspace_id)
    )
    existing_items += await db.scalar(
        select(func.count(Article.id)).where(Article.workspace_id == workspace_id)
    )
    existing_items += await db.scalar(
        select(func.count(Task.id)).where(Task.workspace_id == workspace_id)
    )
    if existing_items:
        return

    today = date.today()
    now = datetime.now(timezone.utc)

    project = Project(
        workspace_id=workspace_id,
        owner_id=user_id,
        name="Демо-проект: исследовательский спринт",
        description=(
            "Стартовый проект показывает, как связать задачи, статью, дедлайны "
            "и kanban-статусы в одной лаборатории."
        ),
        type=ProjectType.RESEARCH,
        status=ProjectStatus.ACTIVE,
        deadline=today + timedelta(days=21),
        position=0,
    )
    db.add(project)
    await db.flush()

    db.add(
        ProjectMember(
            project_id=project.id,
            user_id=user_id,
            role=ProjectRole.PROJECT_OWNER,
        )
    )

    article = Article(
        workspace_id=workspace_id,
        project_id=project.id,
        owner_id=user_id,
        title="Демо-статья: план эксперимента",
        description=(
            "Черновик публикации для проверки article board, задач статьи "
            "и обсуждения внутри команды."
        ),
        status=ArticleStatus.WRITING,
        target_journal="LabMate Demo Journal",
        deadline=today + timedelta(days=35),
        position=0,
    )
    db.add(article)
    await db.flush()

    db.add(
        ArticleMember(
            article_id=article.id,
            user_id=user_id,
            role=ArticleRole.AUTHOR,
        )
    )

    tasks = [
        Task(
            workspace_id=workspace_id,
            project_id=project.id,
            owner_id=user_id,
            created_by=user_id,
            assignee_id=user_id,
            assignees=[user_id],
            title="Собрать требования к эксперименту",
            description="Опишите гипотезу, метрики успеха и ограничения по данным.",
            scope=TaskScope.PROJECT,
            visibility=TaskVisibility.PROJECT,
            status=TaskStatus.TODO,
            type=TaskType.RESEARCH,
            priority=TaskPriority.HIGH,
            due_date=today + timedelta(days=3),
            position=0,
        ),
        Task(
            workspace_id=workspace_id,
            project_id=project.id,
            owner_id=user_id,
            created_by=user_id,
            assignee_id=user_id,
            assignees=[user_id],
            title="Подготовить протокол и чеклист запуска",
            description="Эта задача содержит чеклист и подзадачи как пример декомпозиции.",
            scope=TaskScope.PROJECT,
            visibility=TaskVisibility.PROJECT,
            status=TaskStatus.IN_PROGRESS,
            type=TaskType.EXPERIMENT,
            priority=TaskPriority.MEDIUM,
            due_date=today + timedelta(days=7),
            position=1,
        ),
        Task(
            workspace_id=workspace_id,
            article_id=article.id,
            owner_id=user_id,
            created_by=user_id,
            assignee_id=user_id,
            assignees=[user_id],
            title="Написать введение для демо-статьи",
            description="Проверьте, как article task отображается в задачах и detail-view.",
            scope=TaskScope.ARTICLE,
            visibility=TaskVisibility.ARTICLE,
            status=TaskStatus.IN_REVIEW,
            type=TaskType.WRITING,
            priority=TaskPriority.MEDIUM,
            due_date=today + timedelta(days=10),
            position=2,
        ),
        Task(
            workspace_id=workspace_id,
            owner_id=user_id,
            created_by=user_id,
            assignee_id=user_id,
            assignees=[user_id],
            title="Пригласить коллегу в лабораторию",
            description="Скопируйте код приглашения на экране лаборатории.",
            scope=TaskScope.WORKSPACE,
            visibility=TaskVisibility.WORKSPACE,
            status=TaskStatus.TODO,
            type=TaskType.ADMIN,
            priority=TaskPriority.LOW,
            due_date=today + timedelta(days=14),
            position=3,
        ),
        Task(
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
            due_date=today + timedelta(days=1),
            position=0,
        ),
    ]
    db.add_all(tasks)
    await db.flush()

    checklist_task = tasks[1]
    db.add_all(
        [
            TaskChecklistItem(
                task_id=checklist_task.id,
                created_by=user_id,
                title="Проверить доступность данных",
                kind="CHECK",
                is_done=True,
                position=0,
            ),
            TaskChecklistItem(
                task_id=checklist_task.id,
                created_by=user_id,
                title="Согласовать критерии качества",
                kind="CHECK",
                position=1,
            ),
            TaskChecklistItem(
                task_id=checklist_task.id,
                created_by=user_id,
                title="Подзадача: подготовить шаблон отчета",
                kind="SUBTASK",
                position=2,
            ),
        ]
    )

    db.add(
        Comment(
            workspace_id=workspace_id,
            task_id=checklist_task.id,
            author_id=user_id,
            text=(
                "Стартовый комментарий: здесь можно вести быстрый чат по задаче, "
                "добавлять чеклист и отслеживать изменения."
            ),
            visibility=TaskVisibility.PROJECT,
        )
    )

    db.add(
        WallPost(
            workspace_id=workspace_id,
            author_id=user_id,
            text=(
                "Добро пожаловать в LabMate. Это демо-лаборатория: откройте доску задач, "
                "проект, статью и питомца, чтобы быстро посмотреть основные сценарии."
            ),
            created_at=now,
        )
    )
