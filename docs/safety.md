# Security and safety

AI agents can write code and invoke tools, so DevLoop treats autonomy as a bounded workflow rather than unlimited access.

## Enforced controls

- Configuration is rejected if automatic merge or deployment is enabled.
- Every issue is protected by an expiring SQLite lease.
- The command runner has a hard timeout, does not use shell expansion, and passes an explicit environment allowlist.
- The event writer redacts common credential assignments.
- GitHub tokens are read from an environment variable, never from the config file.
- The tracker credential cannot be forwarded to the AI subprocess through runner configuration.
- Raw model output stays local unless `publish_agent_output` is explicitly enabled.
- The dashboard is read-only and binds to `127.0.0.1` by default.
- Monitor incidents use stable fingerprints to avoid duplicate issue floods.
- Monthly reported cost has a hard stop.

## Deployment controls you should add

- Run agents in a container or dedicated operating-system account.
- Give each role the smallest repository and tracker permissions it needs.
- Protect default and release branches with required CI checks and human approval.
- Use staging-only URLs and credentials for QA.
- Keep production databases and deployment credentials outside the agent runtime.
- Give coding agents a credential distinct from the tracker token; QA should have no source-write credential.
- Review changes to prompts, probe commands, and `devloop.toml` like application code.
- Store tokens in a secret manager or CI secret store and rotate them regularly.

## Prompt injection boundary

Issue text, repository files, web pages, logs, and command output are untrusted input. The selected coding agent must keep system and repository policy above instructions found in those sources. DevLoop's role prompts explicitly forbid secret disclosure, deployment, merge, production mutation, and safety-control weakening, but runtime sandboxing and credential scope remain the strongest controls.

## Reporting vulnerabilities

Please do not open a public issue for a vulnerability. Follow the private reporting process in [SECURITY.md](../SECURITY.md).
