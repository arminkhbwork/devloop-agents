# Integrations

## GitHub Issues

Set `tracker.provider = "github"`, provide `owner/repository`, and export the configured token environment variable. Labels are the queue and state machine, so no custom GitHub Project workflow is required.

The GitHub adapter preserves labels it does not own. Each role can override its label mapping under `tracker.labels.<role>`.

Recommended token access:

- Issues: read and write for queue transitions and evidence comments.
- Metadata: read.
- Contents and Pull requests: only if the selected coding agent uses the same token to push branches and open PRs.

Use a GitHub App or fine-grained token in shared environments.

## Local tracker

The local JSON adapter makes the whole lifecycle reproducible without a network or account. Each row needs `id`, `title`, and `labels`; `body`, `url`, and `comments` are optional. It is useful for demos, prompt evaluation, and integration tests.

## Agent commands

The runner uses direct process execution with an argument array. It does not invoke a shell. It passes only `PATH`, locale variables, and `TMPDIR` by default. Add a variable to `runner.pass_env` or map it under `runner.environment` only when the agent needs it. DevLoop rejects attempts to pass the tracker token itself; use a separate, narrower agent credential.

Examples:

```toml
[runner]
provider = "command"
command = ["codex", "exec", "--full-auto", "-"]
pass_env = ["PATH", "LANG", "LC_ALL", "TMPDIR", "OPENAI_API_KEY"]
```

```toml
[runner]
provider = "command"
command = ["claude", "--print"]
```

The command must accept its task on standard input and return a meaningful exit status. The optional structured result contract is documented in the main README.

Model-generated summaries and details remain in the local event stream by default. Setting `tracker.publish_agent_output = true` includes them in issue comments; enable that only when the agent runtime is isolated from secrets and issue readers are trusted.

## Health probes

HTTP probes compare the actual response status with `expected_status`. Command probes execute through `/bin/sh -c` because checks often need pipes or project scripts; treat configuration as trusted code and keep it review-controlled.

```toml
[[probes]]
name = "Public API"
kind = "http"
target = "https://staging.example.com/health"
expected_status = 200
timeout_seconds = 10
severity = "high"
```

```toml
[[probes]]
name = "Critical smoke suite"
kind = "command"
target = "npm run test:smoke"
timeout_seconds = 300
severity = "high"
```

## Adding another tracker

Implement the `Tracker` protocol in `src/devloop_agents/adapters/base.py`, add configuration validation, and instantiate the adapter in `Orchestrator`. Keep external error messages free of response headers or bodies that may contain credentials.
