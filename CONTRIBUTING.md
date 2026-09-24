# Contributing

Contributions are welcome through focused pull requests.

1. Open an issue describing the user problem and proposed behavior.
2. Create a branch from `main`.
3. Add tests for behavioral changes.
4. Run `python -m unittest discover -s tests -v` and `python -m compileall -q src tests`.
5. Open a pull request explaining the behavior, safety impact, and validation.

Keep adapters vendor-specific and the orchestrator provider-neutral. Do not commit tokens, customer data, internal hostnames, proprietary prompts, or copied issue content.

