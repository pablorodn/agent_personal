from pydantic import BaseModel


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
