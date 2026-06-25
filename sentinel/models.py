from dataclasses import dataclass, field
from typing import List


@dataclass
class Action:
    """Something an AI agent wants to do. For the MVP this is a code change."""
    id: str
    agent: str       # which AI tool produced it (cursor, copilot, claude-code...)
    kind: str        # "code_pr" for now; email / db / deploy later
    diff: str


@dataclass
class Decision:
    """What Sentinel decided about an action."""
    action_id: str
    agent: str
    risk: int                       # 0-3
    verdict: str                    # ALLOW / ESCALATE / BLOCK
    reasons: List[str] = field(default_factory=list)
