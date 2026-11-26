"""Service settings (PR exercise, step 2).

VULN-5: a "temporary" hardcoded key — the classic way secrets reach git. FAKE value, never valid anywhere.
The PR gate (gitleaks on the PR commits) must fail on this file.
The fix: read it from the environment / a secret manager, e.g. os.environ["REFUNDS_API_KEY"].
"""
REFUNDS_API_KEY = "sk_test_F3W6lbzX5BqvonWrNNQbHrJreXFReZrL"
