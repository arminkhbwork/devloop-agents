from __future__ import annotations

import hashlib
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .config import ProbeConfig


@dataclass(slots=True)
class ProbeResult:
    name: str
    healthy: bool
    summary: str
    fingerprint: str
    severity: str


def _fingerprint(probe: ProbeConfig) -> str:
    raw = f"{probe.kind}:{probe.name}:{probe.target}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def execute_probe(probe: ProbeConfig, workspace: Path | None = None) -> ProbeResult:
    fingerprint = _fingerprint(probe)
    if probe.kind == "http":
        try:
            request = urllib.request.Request(probe.target, headers={"User-Agent": "devloop-agents"})
            with urllib.request.urlopen(request, timeout=probe.timeout_seconds) as response:
                status = response.status
            healthy = status == probe.expected_status
            summary = f"HTTP {status}; expected {probe.expected_status}"
        except (urllib.error.URLError, TimeoutError) as error:
            healthy = False
            summary = f"HTTP probe failed: {error}"
    elif probe.kind == "command":
        try:
            completed = subprocess.run(
                ["/bin/sh", "-c", probe.target],
                cwd=workspace,
                text=True,
                capture_output=True,
                timeout=probe.timeout_seconds,
                check=False,
            )
            healthy = completed.returncode == 0
            detail = (completed.stdout or completed.stderr).strip().replace("\n", " ")[:300]
            summary = f"Command exited {completed.returncode}" + (f": {detail}" if detail else "")
        except subprocess.TimeoutExpired:
            healthy = False
            summary = f"Command exceeded {probe.timeout_seconds}s timeout"
    else:
        healthy = False
        summary = f"Unsupported probe kind: {probe.kind}"
    return ProbeResult(probe.name, healthy, summary, fingerprint, probe.severity)
