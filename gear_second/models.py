from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class GovernanceInfo:
    routing_policy: Optional[str] = None
    system_boundaries: Optional[str] = None
    open_tasks: Optional[str] = None
    routing_log_tail: Optional[str] = None
    venture_claude_md: Optional[str] = None
    sources_loaded: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)


@dataclass
class RepoContext:
    cwd: str = ""
    repo_root: Optional[str] = None
    is_git_repo: bool = False
    branch: Optional[str] = None
    venture: Optional[str] = None
    task_id: Optional[str] = None
    mode: str = "auto"
    backend_model: Optional[str] = None
    governance: GovernanceInfo = field(default_factory=GovernanceInfo)
    recent_changes: List[str] = field(default_factory=list)
    protected_paths: List[str] = field(default_factory=list)
