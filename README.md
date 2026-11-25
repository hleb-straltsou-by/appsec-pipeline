# appsec-pipeline

A security pipeline for a small service, built step by step on GitHub Actions. Every check runs in CI — no local
tooling required.

> ⚠️ `app/` is **deliberately vulnerable** (marked `VULN-1…3`). Don't deploy it. The secret in it is fake.

## Pipeline

| Stage | Tool | Status |
|---|---|---|
| SAST | Semgrep (`p/default`) | ✅ |
| Secrets | gitleaks (full git history) | ✅ |
| Image + IaC | Trivy | planned |
| SBOM | Syft (CycloneDX) | planned |
| DAST | OWASP ZAP baseline against the service started in CI | planned |
| Custom rule | Own Semgrep rule for a real bug class | planned |

Findings from every tool go to **Security → Code scanning** as SARIF.

## Policy: block only what's new

| Event | Scope | On findings |
|---|---|---|
| Pull request | Only what the PR adds (Semgrep `--baseline-commit`, gitleaks on the PR commits) | **Check fails** — blocks the merge |
| Push to `main` | Full code and full git history | Reported to the Security tab, **doesn't fail** |

Why: existing findings are debt to triage, not a reason to block every PR. If every PR inherits 300 old findings, teams
switch the scanner off within a month. The gate is on *new* problems only.

## Supply-chain hygiene in the workflow
- Third-party actions pinned by **commit SHA**, not by tag (tags can be moved).
- Tool versions pinned; the gitleaks binary is verified against the release checksums before it runs.
- `GITHUB_TOKEN` has `contents: read` by default; only the jobs that upload SARIF get `security-events: write`.

## The demo service

`app/app.py` — a tiny notes API (Flask + SQLite) with planted bugs and their fixed counterparts:

| ID | Bug | Vulnerable endpoint | Fixed endpoint | Caught by |
|---|---|---|---|---|
| VULN-1 | SQL injection (cross-tenant read) | `/notes/search` | `/notes/search-safe` | Semgrep |
| VULN-2 | Command injection (`shell=True`) | `/diag/ping` | `/diag/ping-safe` | Semgrep |
| VULN-3 | Hardcoded secret | `PAYMENTS_API_KEY` | — (env / secret manager) | gitleaks |

The fixed endpoints must **not** be reported — a quick check for false positives.

## Exercise: does the gate work?

1. Create a branch and add a new vulnerable endpoint, for example:
   ```python
   @app.get("/notes/by-title")
   def by_title():
       title = request.args.get("title", "")
       with db() as conn:
           rows = conn.execute(f"SELECT id FROM notes WHERE title = '{title}'").fetchall()
       return jsonify([dict(r) for r in rows])
   ```
2. Open a pull request.
3. Expected: **Semgrep fails** and annotates the new line; the old VULN-1/2 are **not** reported on the PR (baseline);
   gitleaks passes (no new secret).
4. Then push a commit to the same branch with a fake token and watch gitleaks fail the PR.

Write down: run time, false positives, how findings look in the PR and in the Security tab.
