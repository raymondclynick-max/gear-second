from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


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


@dataclass
class OllamaStatus:
    running: bool = False
    model_available: bool = False
    model_name: Optional[str] = None
    host: str = "http://localhost:11434"
    error: Optional[str] = None


@dataclass
class SessionState:
    session_id: str = ""
    created_at_utc: str = ""
    updated_at_utc: str = ""
    venture: Optional[str] = None
    repo_name: Optional[str] = None
    repo_path: Optional[str] = None
    branch: Optional[str] = None
    task_id: Optional[str] = None
    mode: str = "auto"
    backend_model: Optional[str] = None
    governance_sources: List[str] = field(default_factory=list)
    inspected_files: List[str] = field(default_factory=list)
    changed_files: List[str] = field(default_factory=list)
    commands_run: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    handoff_path: Optional[str] = None
    status: str = "active"   # active | completed | blocked | handoff_ready | aborted | error
    session_dir: Optional[str] = None
