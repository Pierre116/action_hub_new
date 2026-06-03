Run the full backend test suite and report results:
```bash
cd action_hub && ../.venv/bin/python -m pytest tests/ -q --tb=short
```
Summarize: total passed, total failed, any new failures vs the baseline in `AGENT_STATUS.md`.
