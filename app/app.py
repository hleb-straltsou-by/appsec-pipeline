"""Notes API — a deliberately vulnerable demo service for the security pipeline.

DO NOT DEPLOY. Planted bugs are marked with VULN comments; each one should be caught by a pipeline stage:
  VULN-1  SQL injection          -> Semgrep (SAST)
  VULN-2  command injection      -> Semgrep (SAST)
  VULN-3  hardcoded secret       -> gitleaks (secrets)
The safe counterparts show what the fix looks like and should NOT be reported.
"""
import os
import sqlite3
import subprocess

from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "/tmp/notes.db")

# VULN-3: hardcoded secret. FAKE value, never valid anywhere; it exists so gitleaks has something to find.
PAYMENTS_API_KEY = "sk_test_pW0LVLR1aQfp9zLewr1zwfck8YVm3nuR"


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, tenant TEXT, title TEXT, body TEXT)")
        # Intentionally cross-tenant: a seeding check that returns no tenant data.
        if conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 0:  # nosemgrep: query-without-tenant-filter
            conn.executemany(
                "INSERT INTO notes (tenant, title, body) VALUES (?, ?, ?)",
                [("acme", "Q4 plan", "internal"), ("acme", "Hiring", "2 roles"), ("globex", "Secret", "other tenant")],
            )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/notes/search")
def search_notes():
    tenant = request.args.get("tenant", "")
    q = request.args.get("q", "")
    # VULN-1: user input concatenated into SQL. q = "' OR '1'='1" returns other tenants' notes.
    sql = f"SELECT id, title FROM notes WHERE tenant = '{tenant}' AND title LIKE '%{q}%'"
    with db() as conn:
        rows = conn.execute(sql).fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/notes/search-safe")
def search_notes_safe():
    tenant = request.args.get("tenant", "")
    q = request.args.get("q", "")
    # Fix for VULN-1: parameters are bound by the driver, never become SQL code.
    with db() as conn:
        rows = conn.execute(
            "SELECT id, title FROM notes WHERE tenant = ? AND title LIKE ?", (tenant, f"%{q}%")
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/notes/<int:note_id>")
def get_note(note_id):
    tenant = request.args.get("tenant", "")  # stands in for the tenant from the verified token
    # VULN-6: cross-tenant BOLA. Parameterised (no SQL injection, p/default stays silent), but the query ignores the
    # caller's tenant: acme can read globex's note by its id. Caught only by the custom rule.
    with db() as conn:
        row = conn.execute("SELECT id, tenant, title, body FROM notes WHERE id = ?", (note_id,)).fetchone()
    return (jsonify(dict(row)), 200) if row else ({"error": "not found"}, 404)


@app.get("/diag/ping")
def ping():
    host = request.args.get("host", "127.0.0.1")
    # VULN-2: shell=True with user input. host = "127.0.0.1; cat /etc/passwd" runs a second command.
    out = subprocess.run(f"ping -c 1 {host}", shell=True, capture_output=True, text=True, timeout=5)
    return {"output": out.stdout}


@app.get("/diag/ping-safe")
def ping_safe():
    host = request.args.get("host", "127.0.0.1")
    # Fix for VULN-2: argument list, no shell; the input is one argument, never a command.
    out = subprocess.run(["ping", "-c", "1", "--", host], capture_output=True, text=True, timeout=5)
    return {"output": out.stdout}


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
