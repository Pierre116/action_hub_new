"""
apply_seed.py — Load data from reseed_from_export.py into the current DB schema.
Handles schema mismatches by filtering out columns that don't exist in the target.
Does NOT modify reseed_from_export.py.
"""
import re
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DB_PATH    = SCRIPT_DIR / "db" / "actionhub.db"
RESEED_PY  = SCRIPT_DIR / "reseed_from_export.py"


def extract_seed_sql(reseed_path: Path) -> str:
    """Extract the SEED_SQL string from reseed_from_export.py."""
    content = reseed_path.read_text(encoding="utf-8")
    marker = 'SEED_SQL = """'
    start = content.find(marker)
    if start == -1:
        print("ERROR: could not find SEED_SQL in reseed_from_export.py", file=sys.stderr)
        sys.exit(1)
    start += len(marker)
    end = content.find('"""', start)
    return content[start:end]


def get_target_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """Return column names for a table in the target DB."""
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def apply_insert(conn: sqlite3.Connection, statement: str) -> tuple[str, int, int]:
    """
    Parse an INSERT OR IGNORE statement, filter to columns that exist
    in the target schema, and execute.
    Returns (table_name, inserted, skipped).
    """
    # Parse: INSERT OR IGNORE INTO t_xxx (col1, col2, ...) VALUES
    m = re.match(
        r"INSERT\s+OR\s+IGNORE\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*",
        statement,
        re.IGNORECASE,
    )
    if not m:
        return ("?", 0, 0)

    table = m.group(1)
    src_cols = [c.strip() for c in m.group(2).split(",")]

    # Get target columns
    target_cols = get_target_columns(conn, table)
    if not target_cols:
        print(f"  SKIP {table} — not in target schema")
        return (table, 0, 0)

    # Find which source column indices to keep
    keep_indices = []
    keep_cols = []
    for i, col in enumerate(src_cols):
        if col in target_cols:
            keep_indices.append(i)
            keep_cols.append(col)

    if not keep_cols:
        print(f"  SKIP {table} — no matching columns")
        return (table, 0, 0)

    dropped = set(src_cols) - set(keep_cols)
    if dropped:
        print(f"  {table}: dropping columns not in schema: {dropped}")

    # Extract value tuples — find everything after VALUES
    values_start = m.end()
    values_text = statement[values_start:].rstrip().rstrip(";")

    # Parse each row tuple
    rows = _parse_value_rows(values_text)

    col_list = ", ".join(keep_cols)
    placeholders = ", ".join(["?"] * len(keep_cols))
    insert_sql = f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({placeholders})"

    inserted = 0
    skipped = 0
    for row_values in rows:
        filtered = [row_values[i] for i in keep_indices]
        try:
            conn.execute(insert_sql, filtered)
            inserted += 1
        except sqlite3.Error as exc:
            skipped += 1
            print(f"  WARN {table}: {exc}")

    return (table, inserted, skipped)


def _parse_value_rows(text: str) -> list[list]:
    """
    Parse SQL value rows like:
      (1, 'foo', NULL, 'bar''s'),
      (2, 'baz', NULL, 'qux');
    Returns list of lists of Python values.
    """
    rows = []
    i = 0
    while i < len(text):
        # Find next opening paren
        i = text.find("(", i)
        if i == -1:
            break
        i += 1  # skip '('
        values = []
        while i < len(text):
            # Skip whitespace
            while i < len(text) and text[i] in " \t\r\n":
                i += 1
            if i >= len(text):
                break
            if text[i] == ")":
                i += 1
                break

            if text[i] == ",":
                i += 1
                continue

            # Parse value
            if text[i] == "'":
                # String literal — handle escaped quotes ('')
                i += 1
                val_chars = []
                while i < len(text):
                    if text[i] == "'":
                        if i + 1 < len(text) and text[i + 1] == "'":
                            val_chars.append("'")
                            i += 2
                        else:
                            i += 1
                            break
                    else:
                        val_chars.append(text[i])
                        i += 1
                values.append("".join(val_chars))
            elif text[i:i+4].upper() == "NULL":
                values.append(None)
                i += 4
            elif text[i:i+2].upper() == "X'":
                # Hex blob
                i += 2
                end = text.index("'", i)
                hex_str = text[i:end]
                values.append(bytes.fromhex(hex_str))
                i = end + 1
            else:
                # Number
                end = i
                while end < len(text) and text[end] not in ",) \t\r\n":
                    end += 1
                num_str = text[i:end]
                try:
                    if "." in num_str:
                        values.append(float(num_str))
                    else:
                        values.append(int(num_str))
                except ValueError:
                    values.append(num_str)
                i = end

        if values:
            rows.append(values)

    return rows


def main() -> int:
    if not RESEED_PY.exists():
        print(f"ERROR: {RESEED_PY} not found", file=sys.stderr)
        return 1
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found — run init_db.py first", file=sys.stderr)
        return 1

    print(f"Extracting SEED_SQL from {RESEED_PY.name} …")
    seed_sql = extract_seed_sql(RESEED_PY)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = OFF")

    # Split by finding each INSERT OR IGNORE statement block
    # A block ends with ); at column start or after a newline
    insert_starts = [m.start() for m in re.finditer(r"INSERT\s+OR\s+IGNORE\s+INTO", seed_sql, re.IGNORECASE)]
    matches = []
    for idx, start in enumerate(insert_starts):
        end = insert_starts[idx + 1] if idx + 1 < len(insert_starts) else len(seed_sql)
        block = seed_sql[start:end].rstrip()
        # Remove trailing comments/blank lines after the semicolon
        semi_pos = block.rfind(";")
        if semi_pos != -1:
            block = block[:semi_pos + 1]
        matches.append(block)
    print(f"Found {len(matches)} INSERT statements")

    total_inserted = 0
    total_skipped = 0

    for stmt in matches:
        stmt = stmt.strip()
        if not stmt:
            continue
        table, ins, skp = apply_insert(conn, stmt)
        if ins or skp:
            print(f"  {table}: {ins} inserted, {skp} skipped")
        total_inserted += ins
        total_skipped += skp

    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()

    print(f"\nDone — {total_inserted} rows inserted, {total_skipped} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
