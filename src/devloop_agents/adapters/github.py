from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from ..config import TrackerConfig
from ..models import AgentResult, Role, WorkItem


class GitHubError(RuntimeError):
    pass


class GitHubTracker:
    API = "https://api.github.com"

    def __init__(self, config: TrackerConfig):
        self.config = config
        self.token = os.environ.get(config.token_env, "")
        if not self.token:
            raise GitHubError(f"Missing GitHub token in {config.token_env}")

    def _request(self, method: str, path: str, payload: dict | None = None) -> object:
        body = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            f"{self.API}{path}",
            data=body,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "devloop-agents",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode() or "null")
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:500]
            raise GitHubError(f"GitHub API {method} {path} failed ({error.code}): {detail}") from error

    def queue(self, role: Role, limit: int) -> list[WorkItem]:
        label = urllib.parse.quote(self.config.labels[role]["queued"])
        rows = self._request(
            "GET", f"/repos/{self.config.repository}/issues?state=open&labels={label}&per_page={limit}"
        )
        assert isinstance(rows, list)
        return [
            WorkItem(
                id=str(row["number"]),
                title=row["title"],
                body=row.get("body") or "",
                url=row["html_url"],
                labels=[label["name"] for label in row.get("labels", [])],
                metadata={"source": "github", "author": row["user"]["login"]},
            )
            for row in rows
            if "pull_request" not in row
        ]

    def _labels(self, item: WorkItem) -> list[str]:
        row = self._request("GET", f"/repos/{self.config.repository}/issues/{item.id}")
        assert isinstance(row, dict)
        return [label["name"] for label in row.get("labels", [])]

    def _transition(self, role: Role, item: WorkItem, destination: str, comment: str) -> None:
        role_labels = set(self.config.labels[role].values())
        labels = [label for label in self._labels(item) if label not in role_labels]
        labels.append(self.config.labels[role][destination])
        self._request("PATCH", f"/repos/{self.config.repository}/issues/{item.id}", {"labels": labels})
        self._request(
            "POST", f"/repos/{self.config.repository}/issues/{item.id}/comments", {"body": comment}
        )

    def claim(self, role: Role, item: WorkItem) -> None:
        self._transition(role, item, "claimed", f"DevLoop `{role}` agent claimed this issue.")

    def complete(self, role: Role, item: WorkItem, result: AgentResult) -> None:
        body = f"### DevLoop {role} result\n\nAgent finished with status `{result.status}`."
        pull_request_url = self._safe_pull_request_url(result.pull_request_url)
        if pull_request_url:
            body += f"\n\nPull request: {pull_request_url}"
        if self.config.publish_agent_output:
            body += f"\n\n{result.summary[:2000]}"
        if self.config.publish_agent_output and result.details:
            body += f"\n\n<details><summary>Details</summary>\n\n{result.details[:6000]}\n\n</details>"
        self._transition(role, item, "completed", body)

    def _safe_pull_request_url(self, value: str | None) -> str | None:
        if not value:
            return None
        owner_repo = re.escape(self.config.repository)
        if re.fullmatch(rf"https://github\.com/{owner_repo}/pull/\d+", value):
            return value
        return None

    def fail(self, role: Role, item: WorkItem, result: AgentResult) -> None:
        body = f"### DevLoop {role} blocked\n\nAgent finished with status `{result.status}`."
        if self.config.publish_agent_output:
            body += f"\n\n{result.summary[:2000]}"
        self._transition(role, item, "blocked", body)

    def report_incident(self, title: str, body: str, fingerprint: str) -> WorkItem | None:
        managed = self.config.labels["monitor"]["managed"]
        query = urllib.parse.quote(
            f'repo:{self.config.repository} is:issue is:open label:"{managed}" "{fingerprint}"'
        )
        search = self._request("GET", f"/search/issues?q={query}&per_page=1")
        assert isinstance(search, dict)
        matches = search.get("items", [])
        if matches:
            item = WorkItem(str(matches[0]["number"]), matches[0]["title"], url=matches[0]["html_url"])
            self._request(
                "POST",
                f"/repos/{self.config.repository}/issues/{item.id}/comments",
                {"body": body},
            )
            return None
        row = self._request(
            "POST",
            f"/repos/{self.config.repository}/issues",
            {
                "title": title,
                "body": f"{body}\n\n<!-- devloop-fingerprint:{fingerprint} -->",
                "labels": [self.config.labels["monitor"]["incident"], managed],
            },
        )
        assert isinstance(row, dict)
        return WorkItem(str(row["number"]), row["title"], row.get("body") or "", row["html_url"])
