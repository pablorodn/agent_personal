from pydantic import BaseModel, Field


class GitHubListReposArgs(BaseModel):
    per_page: int = Field(default=30, ge=1, le=100)


class GitHubListIssuesArgs(BaseModel):
    owner: str
    repo: str
    state: str = "open"


class GitHubCreateIssueArgs(BaseModel):
    owner: str
    repo: str
    title: str
    body: str | None = None


class GitHubCreateRepoArgs(BaseModel):
    name: str
    private: bool = True


class ReadFileArgs(BaseModel):
    path: str
    offset: int | None = None
    limit: int | None = None


class WriteFileArgs(BaseModel):
    path: str
    content: str


class EditFileArgs(BaseModel):
    path: str
    old_string: str
    new_string: str


class BashArgs(BaseModel):
    command: str
    timeout_seconds: int = Field(default=30, ge=1, le=120)


class ScheduleTaskArgs(BaseModel):
    prompt: str
    run_at: str | None = None
    cron_expr: str | None = None
    timezone: str = "UTC"
