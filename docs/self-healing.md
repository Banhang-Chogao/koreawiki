# Self-Healing Deployment System

KoreaWiki automatically detects CI/CD failures, applies playbook fixes from
`scientist.md`, re-validates, and opens a recovery PR — without force-deploying
a red build.

## Architecture

```
Build & Deploy / QA fails
        │
        ▼
Self-Healing Recovery workflow  (.github/workflows/self-healing.yml)
        │
        ├─ download failed run logs (gh run view --log)
        ├─ python3 scripts/self_healing.py recover
        │     ├─ categorize (Hugo / QA / SEO / markdown / …)
        │     ├─ apply deterministic fixes (scientist playbook)
        │     ├─ validate full suite (max 5 rounds)
        │     └─ write reports/self-healing/<ts>-<run>/
        │
        ├─ if patches exist → branch self-heal/run-… + PR
        ├─ if status=recovered → enable auto-merge when allowed
        └─ if still red after 5 rounds → STOP + Recovery Report / Issue
                 (never force deploy)
```

## Triggers

| Event | Behavior |
|-------|----------|
| `workflow_run` completed **failure** on `Build & Deploy` or `QA` | Auto recovery |
| `workflow_dispatch` | Manual recovery (optional run id) |

Does **not** re-enter recovery when the Self-Healing workflow itself fails
(loop guard). Round number is inferred from recent `[self-heal N/5]` commits.

## Components

| Path | Role |
|------|------|
| `AGENTS.md` | Rules for coding agents during recovery |
| `scientist.md` | Historical defects + proven fixes |
| `scripts/self_healing.py` | Analyze / fix / validate / report |
| `.github/workflows/self-healing.yml` | GitHub Actions orchestration |
| `reports/self-healing/` | Logs, diagnostics, recovery reports |

## CLI

```bash
python3 scripts/self_healing.py analyze --log /tmp/workflow.log
python3 scripts/self_healing.py fix --log /tmp/workflow.log
python3 scripts/self_healing.py validate
python3 scripts/self_healing.py recover --log /tmp/workflow.log --round 1
```

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | Recovered — all validations green |
| 1 | Partial / still red — report written |
| 2 | Max rounds exceeded |

## Safety

- No fabricated content  
- No deletion of valid articles to silence linters  
- No forced Pages deploy on red checks  
- Max **5** recovery rounds  
- Fix commits use noreply author email for GitHub privacy  

## Local simulation

```bash
# Capture a failed run
gh run list --workflow=build.yml --limit 5
gh run view <id> --log > /tmp/wf.log

python3 scripts/self_healing.py recover --log /tmp/wf.log --round 1
```

## After merge

Normal **Build & Deploy** runs on `main` and publishes GitHub Pages only when
its own validations pass.
