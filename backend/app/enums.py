import enum


class WorkspaceRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    PROJECT_LEAD = "PROJECT_LEAD"
    EDITOR = "EDITOR"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


class ProjectRole(str, enum.Enum):
    PROJECT_OWNER = "PROJECT_OWNER"
    LEAD = "LEAD"
    CONTRIBUTOR = "CONTRIBUTOR"
    REVIEWER = "REVIEWER"
    OBSERVER = "OBSERVER"


class ArticleRole(str, enum.Enum):
    AUTHOR = "AUTHOR"
    CO_AUTHOR = "CO_AUTHOR"
    REVIEWER = "REVIEWER"
    EDITOR = "EDITOR"
    OBSERVER = "OBSERVER"


class ProjectType(str, enum.Enum):
    RESEARCH = "RESEARCH"
    SOFTWARE = "SOFTWARE"
    PUBLICATION = "PUBLICATION"
    EXPERIMENT = "EXPERIMENT"
    ADMIN = "ADMIN"
    OTHER = "OTHER"


class ProjectStatus(str, enum.Enum):
    IDEA = "IDEA"
    PLANNING = "PLANNING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"
    ARCHIVED = "ARCHIVED"


class ArticleStatus(str, enum.Enum):
    IDEA = "IDEA"
    PLANNING = "PLANNING"
    WRITING = "WRITING"
    INTERNAL_REVIEW = "INTERNAL_REVIEW"
    REVISION = "REVISION"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class TaskScope(str, enum.Enum):
    WORKSPACE = "WORKSPACE"
    PROJECT = "PROJECT"
    ARTICLE = "ARTICLE"
    PERSONAL = "PERSONAL"


class TaskVisibility(str, enum.Enum):
    PRIVATE = "PRIVATE"
    WORKSPACE = "WORKSPACE"
    PROJECT = "PROJECT"
    ARTICLE = "ARTICLE"


class TaskType(str, enum.Enum):
    RESEARCH = "RESEARCH"
    WRITING = "WRITING"
    REVIEW = "REVIEW"
    FORMATTING = "FORMATTING"
    DEVELOPMENT = "DEVELOPMENT"
    DESIGN = "DESIGN"
    TESTING = "TESTING"
    DEPLOYMENT = "DEPLOYMENT"
    EXPERIMENT = "EXPERIMENT"
    SUBMISSION = "SUBMISSION"
    RESPONSE_TO_REVIEWER = "RESPONSE_TO_REVIEWER"
    ADMIN = "ADMIN"
    PERSONAL = "PERSONAL"
    OTHER = "OTHER"


class TaskStatus(str, enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class RewardType(str, enum.Enum):
    XP = "XP"
    FOOD = "FOOD"
    MOOD = "MOOD"
    ENERGY = "ENERGY"
    ITEM = "ITEM"


class PrivacyLevel(str, enum.Enum):
    PRIVATE = "PRIVATE"
    WORKSPACE = "WORKSPACE"


class EventStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class DomainEventType(str, enum.Enum):
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_REOPENED = "TASK_REOPENED"
    PROJECT_STATUS_CHANGED = "PROJECT_STATUS_CHANGED"
    ARTICLE_STATUS_CHANGED = "ARTICLE_STATUS_CHANGED"
    COMMENT_ADDED = "COMMENT_ADDED"


class NotificationType(str, enum.Enum):
    TASK_ASSIGNED = "TASK_ASSIGNED"
    MENTION = "MENTION"
    DEADLINE = "DEADLINE"
    WALL_POST = "WALL_POST"
