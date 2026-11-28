# appsec-pipeline

A security pipeline for a small service, built step by step on GitHub Actions. Every check runs in CI — no local
tooling required.

> ⚠️ `app/` is **deliberately vulnerable** (marked `VULN-1…3`). Don't deploy it. The secret in it is fake.

## Pipeline

| Stage | Tool | Status |
|---|---|---|
| SAST | Semgrep (`p/default`) | ✅ |
| Secrets | gitleaks (full git history) | ✅ |
| Image + Dockerfile | Trivy (`image`, `config`) | ✅ |
| SBOM | Syft (CycloneDX) → artifact; Trivy rescans the SBOM | ✅ |
| DAST, passive (PR) | OWASP ZAP: crawler baseline + API scan in safe mode (`-S`) over `api/openapi.yaml` | ✅ |
| DAST, active (nightly) | OWASP ZAP API scan with attack payloads → tracking issue | ✅ |
| Custom rule | Own Semgrep rule for a real bug class | planned |

Findings from every tool go to **Security → Code scanning** as SARIF.

## Policy: block only what's new

| Event | Scope | On findings |
|---|---|---|
| Pull request | Only what the PR adds (Semgrep `--baseline-commit`, gitleaks on the PR commits) | **Check fails** — blocks the merge |
| Push to `main` | Full code and full git history | Reported to the Security tab, **doesn't fail** |
| Image (any event) | Built image: OS + Python packages; Dockerfile | Everything reported; **fails only on fixable CRITICAL** |
| DAST passive (PR, push) | Service started in CI; ZAP observes responses, sends no attacks | Report + artifact; **fails only on rules marked FAIL** in `.zap/rules.tsv` |
| DAST active (nightly 02:17 UTC) | Same throwaway container; ZAP attacks every endpoint from the spec | Never fails the build; High findings → **one living issue** (comment per night). SLA for High: 7 days |

Why: existing findings are debt to triage, not a reason to block every PR. If every PR inherits 300 old findings, teams
switch the scanner off within a month. The gate is on *new* problems only.

## DAST notes
- **A crawler finds almost nothing on a JSON API** — there are no links to follow. The PR job runs both and shows the
  difference: the crawler alone reached 4 URLs, the OpenAPI spec gave ZAP 8. The spec is the attack surface.
- **Passive DAST does not find injection.** Only the active scan (nightly) sends payloads; it found the SQL injection
  (rule 40018) and the command injection (90020) that the passive run could not see.
- **Rule actions live in `.zap/rules.tsv`.** FAIL: problems the application itself owns (debug errors, PII, cookie
  flags). WARN: headers usually set at the ingress in production (CSP, HSTS, X-Content-Type-Options) — a CI container is
  not a production-parity stand, so they're verified there, not blocked here.
- **Active scans only against a throwaway target.** Payloads can corrupt data and lock accounts; never a shared
  environment, never production.
- **Pinned scanner gets old.** ZAP is pinned by digest (2.16.1), and ZAP itself warns "out of date" (10116): pinning
  trades freshness for reproducibility, so the pin needs a scheduled update (Renovate / Dependabot).

## Supply-chain hygiene in the workflow
- Third-party actions pinned by **commit SHA**, not by tag (tags can be moved).
- Tool versions pinned with a **cooldown** (newest release older than 14 days); every downloaded binary
  (gitleaks, Trivy, Syft) is verified against the release checksums before it runs; the ZAP image is pinned by digest.
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
