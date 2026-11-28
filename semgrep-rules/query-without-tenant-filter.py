# Tests for query-without-tenant-filter. Run: semgrep --test semgrep-rules/
# Each "ruleid" line must be reported on the next line, each "ok" line must not.


def bad(conn, note_id, title):
    # ruleid: query-without-tenant-filter
    conn.execute("SELECT id, title, body FROM notes WHERE id = ?", (note_id,))

    # ruleid: query-without-tenant-filter
    conn.execute("select * from notes")

    # ruleid: query-without-tenant-filter
    conn.execute("UPDATE notes SET title = ? WHERE id = ?", (title, note_id))

    # ruleid: query-without-tenant-filter
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))

    # ruleid: query-without-tenant-filter
    conn.execute("SELECT id FROM notes WHERE title = ? OR tenant_name = ?", (title, title))


def good(conn, tenant, note_id, title):
    # ok: query-without-tenant-filter
    conn.execute("SELECT id, title, body FROM notes WHERE tenant = ? AND id = ?", (tenant, note_id))

    # ok: query-without-tenant-filter
    conn.execute("UPDATE notes SET title = ? WHERE id = ? AND tenant = ?", (title, note_id, tenant))

    # ok: query-without-tenant-filter
    conn.execute("DELETE FROM notes WHERE tenant = ? AND id = ?", (tenant, note_id))

    # ok: query-without-tenant-filter
    conn.execute("SELECT id FROM users WHERE id = ?", (note_id,))

    # ok: query-without-tenant-filter
    conn.execute("INSERT INTO notes (tenant, title, body) VALUES (?, ?, ?)", (tenant, title, ""))


# Suppression (nosemgrep) is not tested here: in `--test` the rule id has no path prefix, in a scan it is
# `semgrep-rules.query-without-tenant-filter`. The scan of app/app.py checks the real suppression.
