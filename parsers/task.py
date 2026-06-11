from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID


@dataclass
class ParserRunTask:
    task_id: UUID
    parser_name: str
    date_from: datetime
    date_to: datetime
    source_type: str
    filters: dict[str, Any] = field(default_factory=dict)
    max_items: Optional[int] = 1000
    delay_seconds: float = 0
    delay_between_items: float = 0
    parse_all_categories: bool = False
