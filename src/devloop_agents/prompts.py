from __future__ import annotations

from importlib.resources import files

from .config import AppConfig
from .models import Role, WorkItem


def render_prompt(role: Role, item: WorkItem, config: AppConfig) -> str:
    template = files("devloop_agents").joinpath("templates", f"{role}.md").read_text(encoding="utf-8")
    replacements = {
        "{{project_name}}": config.project.name,
        "{{workspace}}": str(config.project.workspace),
        "{{default_branch}}": config.project.default_branch,
        "{{target_url}}": config.project.target_url or "not configured",
        "{{item_id}}": item.id,
        "{{item_title}}": item.title,
        "{{item_body}}": item.body or "No description provided.",
        "{{item_url}}": item.url or "local tracker",
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template

