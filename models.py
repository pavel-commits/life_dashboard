from dataclasses import dataclass
from typing import Optional


@dataclass
class Task:
    title: str
    description: str = ""
    priority: str = "Medium"
    due_date: Optional[str] = None
    status: str = "Todo"
    id: Optional[int] = None
