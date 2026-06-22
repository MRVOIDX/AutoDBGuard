"""
AutoDBGuard – Risk-Aware SQL Execution System
Full backend with all agents, new tables, history, explanation, and auto-fix.
"""

import sqlite3
import os
import re
import csv
import io
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, render_template, request, jsonify

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

DB_PATH      = os.path.join(os.path.dirname(__file__), "database.db")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.1-8b-instant"

# ─────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────

CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
    "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose",
    "Austin", "Jacksonville", "Fort Worth", "Columbus", "San Francisco",
    "Charlotte", "Indianapolis", "Seattle", "Denver", "Boston",
    "Nashville", "Oklahoma City", "El Paso", "Washington DC", "Las Vegas",
    "Memphis", "Louisville", "Portland", "Baltimore", "Milwaukee",
]

def init_db():
    """Create / migrate the SQLite database and seed all tables."""
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ── users table ──────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    NOT NULL,
            age        INTEGER,
            city       TEXT,
            created_at TEXT    DEFAULT (date('now'))
        )
    """)

    # Migrate older schema: add columns if missing
    existing_cols = {r[1] for r in cursor.execute("PRAGMA table_info(users)").fetchall()}
    for col, defn in [("age","INTEGER"), ("city","TEXT"), ("created_at","TEXT")]:
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")

    # Seed users if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        users = [
            ("Alice Johnson","alice.johnson@example.com",28,"New York","2023-01-15"),
            ("Bob Smith","bob.smith@example.com",34,"Los Angeles","2023-02-20"),
            ("Carol Davis","carol.davis@example.com",22,"Chicago","2023-03-05"),
            ("David Lee","david.lee@example.com",45,"Houston","2023-03-18"),
            ("Eva Martinez","eva.martinez@example.com",31,"Phoenix","2023-04-02"),
            ("Frank Wilson","frank.wilson@example.com",38,"Philadelphia","2023-04-14"),
            ("Grace Thompson","grace.thompson@example.com",26,"San Antonio","2023-04-29"),
            ("Henry Anderson","henry.anderson@example.com",52,"San Diego","2023-05-10"),
            ("Isabella Thomas","isabella.thomas@example.com",24,"Dallas","2023-05-22"),
            ("James Jackson","james.jackson@example.com",41,"San Jose","2023-06-01"),
            ("Karen White","karen.white@example.com",33,"Austin","2023-06-15"),
            ("Liam Harris","liam.harris@example.com",29,"Jacksonville","2023-06-28"),
            ("Mia Martin","mia.martin@example.com",27,"Fort Worth","2023-07-09"),
            ("Noah Garcia","noah.garcia@example.com",36,"Columbus","2023-07-20"),
            ("Olivia Brown","olivia.brown@example.com",23,"San Francisco","2023-07-31"),
            ("Paul Miller","paul.miller@example.com",48,"Charlotte","2023-08-11"),
            ("Quinn Robinson","quinn.robinson@example.com",32,"Indianapolis","2023-08-22"),
            ("Rachel Clark","rachel.clark@example.com",25,"Seattle","2023-09-02"),
            ("Samuel Lewis","samuel.lewis@example.com",44,"Denver","2023-09-13"),
            ("Tina Walker","tina.walker@example.com",30,"Boston","2023-09-24"),
            ("Uma Hall","uma.hall@example.com",37,"Nashville","2023-10-05"),
            ("Victor Allen","victor.allen@example.com",55,"Oklahoma City","2023-10-16"),
            ("Wendy Young","wendy.young@example.com",21,"El Paso","2023-10-27"),
            ("Xander Hernandez","xander.hernandez@example.com",40,"Washington DC","2023-11-07"),
            ("Yasmine King","yasmine.king@example.com",28,"Las Vegas","2023-11-18"),
            ("Zach Wright","zach.wright@example.com",35,"Memphis","2023-11-29"),
            ("Amber Scott","amber.scott@example.com",26,"Louisville","2023-12-10"),
            ("Brian Torres","brian.torres@example.com",43,"Portland","2023-12-21"),
            ("Chloe Nguyen","chloe.nguyen@example.com",24,"Baltimore","2024-01-01"),
            ("Derek Hill","derek.hill@example.com",39,"Milwaukee","2024-01-12"),
            ("Elena Flores","elena.flores@example.com",31,"New York","2024-01-23"),
            ("Felix Green","felix.green@example.com",47,"Los Angeles","2024-02-03"),
            ("Gina Adams","gina.adams@example.com",22,"Chicago","2024-02-14"),
            ("Hugo Nelson","hugo.nelson@example.com",58,"Houston","2024-02-25"),
            ("Iris Carter","iris.carter@example.com",27,"Phoenix","2024-03-07"),
            ("Jake Mitchell","jake.mitchell@example.com",34,"San Diego","2024-03-18"),
            ("Kylie Perez","kylie.perez@example.com",20,"Austin","2024-03-29"),
            ("Leon Roberts","leon.roberts@example.com",42,"Seattle","2024-04-09"),
            ("Maya Turner","maya.turner@example.com",29,"Denver","2024-04-20"),
            ("Nathan Phillips","nathan.phillips@example.com",36,"Boston","2024-05-01"),
            ("Opal Campbell","opal.campbell@example.com",33,"San Francisco","2024-05-12"),
            ("Pedro Parker","pedro.parker@example.com",25,"Dallas","2024-05-23"),
            ("Quinn Evans","quinn.evans@example.com",38,"Charlotte","2024-06-03"),
            ("Rosa Edwards","rosa.edwards@example.com",30,"Nashville","2024-06-14"),
            ("Steve Collins","steve.collins@example.com",51,"Indianapolis","2024-06-25"),
            ("Tara Stewart","tara.stewart@example.com",23,"Las Vegas","2024-07-06"),
            ("Ulric Sanchez","ulric.sanchez@example.com",44,"Portland","2024-07-17"),
            ("Vera Morris","vera.morris@example.com",28,"Baltimore","2024-07-28"),
            ("Walter Rogers","walter.rogers@example.com",60,"Columbus","2024-08-08"),
            ("Xena Reed","xena.reed@example.com",32,"Fort Worth","2024-08-19"),
        ]
        cursor.executemany(
            "INSERT INTO users (name,email,age,city,created_at) VALUES (?,?,?,?,?)",
            users
        )
    else:
        # Backfill age/city for existing rows that have NULLs
        cursor.execute("SELECT id FROM users WHERE age IS NULL OR city IS NULL ORDER BY id")
        nullrows = [r[0] for r in cursor.fetchall()]
        for i, uid in enumerate(nullrows):
            age  = 20 + (i * 7 % 45)
            city = CITIES[i % len(CITIES)]
            cursor.execute("UPDATE users SET age=?, city=? WHERE id=?", (age, city, uid))

    # ── products table ────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            category TEXT    NOT NULL,
            price    REAL    NOT NULL,
            stock    INTEGER NOT NULL
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        products = [
            ("Wireless Headphones","Electronics",79.99,120),
            ("Mechanical Keyboard","Electronics",149.99,45),
            ("4K Monitor","Electronics",399.99,30),
            ("USB-C Hub","Electronics",39.99,200),
            ("Laptop Stand","Electronics",29.99,150),
            ("Running Shoes","Sports",89.99,80),
            ("Yoga Mat","Sports",24.99,200),
            ("Dumbbell Set","Sports",59.99,60),
            ("Water Bottle","Sports",14.99,300),
            ("Resistance Bands","Sports",12.99,250),
            ("Python Programming","Books",39.99,500),
            ("SQL Mastery","Books",29.99,300),
            ("Data Science Guide","Books",44.99,200),
            ("Clean Code","Books",34.99,400),
            ("Design Patterns","Books",49.99,150),
            ("Cotton T-Shirt","Clothing",19.99,500),
            ("Denim Jeans","Clothing",49.99,200),
            ("Winter Jacket","Clothing",129.99,80),
            ("Desk Organizer","Home",22.99,180),
            ("LED Desk Lamp","Home",35.99,120),
        ]
        cursor.executemany(
            "INSERT INTO products (name,category,price,stock) VALUES (?,?,?,?)",
            products
        )

    # ── orders table ─────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            product_id  INTEGER NOT NULL,
            quantity    INTEGER NOT NULL,
            total_price REAL    NOT NULL,
            status      TEXT    NOT NULL,
            order_date  TEXT    NOT NULL,
            FOREIGN KEY (user_id)    REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM orders")
    if cursor.fetchone()[0] == 0:
        statuses = ["completed","completed","completed","shipped","pending","cancelled"]
        orders = [
            (1,1,1,79.99,"completed","2024-01-10"),
            (2,3,2,299.98,"completed","2024-01-15"),
            (3,5,1,79.99,"shipped","2024-01-20"),
            (4,2,4,39.99,"completed","2024-01-22"),
            (5,7,6,89.99,"completed","2024-02-01"),
            (6,1,11,39.99,"completed","2024-02-05"),
            (7,9,2,149.99,"pending","2024-02-10"),
            (8,4,16,19.99,"completed","2024-02-14"),
            (9,11,8,59.99,"cancelled","2024-02-18"),
            (10,6,20,35.99,"completed","2024-02-22"),
            (11,13,12,29.99,"shipped","2024-03-01"),
            (12,3,17,49.99,"completed","2024-03-05"),
            (13,15,3,399.99,"completed","2024-03-10"),
            (14,8,9,29.98,"completed","2024-03-15"),
            (15,20,14,34.99,"pending","2024-03-20"),
            (16,2,6,89.99,"completed","2024-04-01"),
            (17,5,13,44.99,"completed","2024-04-05"),
            (18,12,18,129.99,"shipped","2024-04-10"),
            (19,7,5,29.99,"completed","2024-04-15"),
            (20,17,10,12.99,"completed","2024-04-20"),
            (21,25,15,49.99,"completed","2024-05-01"),
            (22,30,1,79.99,"pending","2024-05-05"),
            (23,10,7,24.99,"completed","2024-05-10"),
            (24,35,2,149.99,"cancelled","2024-05-15"),
            (25,4,19,22.99,"completed","2024-05-20"),
            (26,40,11,39.99,"shipped","2024-06-01"),
            (27,22,4,79.98,"completed","2024-06-05"),
            (28,14,16,39.98,"completed","2024-06-10"),
            (29,8,13,44.99,"completed","2024-06-15"),
            (30,50,20,35.99,"pending","2024-06-20"),
        ]
        cursor.executemany(
            "INSERT INTO orders (user_id,product_id,quantity,total_price,status,order_date) VALUES (?,?,?,?,?,?)",
            orders
        )

    # ── query_history table ───────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            natural_language TEXT    NOT NULL,
            original_sql     TEXT    NOT NULL,
            safe_sql         TEXT,
            risk_level       TEXT    NOT NULL,
            risk_score       INTEGER NOT NULL,
            action           TEXT    NOT NULL,
            row_count        INTEGER DEFAULT 0,
            created_at       TEXT    DEFAULT (datetime('now','localtime'))
        )
    """)

    # ── user_tables metadata ──────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_tables (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name   TEXT    NOT NULL UNIQUE,
            display_name TEXT    NOT NULL,
            source_file  TEXT    NOT NULL,
            row_count    INTEGER NOT NULL DEFAULT 0,
            created_at   TEXT    DEFAULT (datetime('now','localtime'))
        )
    """)

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# FILE UPLOAD HELPERS
# ─────────────────────────────────────────────

BUILTIN_TABLES = {"users", "products", "orders", "query_history", "user_tables"}

def sanitize_identifier(name: str) -> str:
    """Convert any string to a safe SQL snake_case identifier."""
    name = re.sub(r"[^a-zA-Z0-9_]", "_", str(name).strip())
    name = re.sub(r"_+", "_", name).strip("_").lower()
    if not name or name[0].isdigit():
        name = "t_" + name
    return name[:60]


def parse_uploaded_file(file_obj, filename: str) -> dict:
    """Parse CSV, TSV, JSON, JSONL, Excel, XML, YAML, or SQL files into columns + rows."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    raw = file_obj.read()

    # ── Excel (.xlsx / .xls) — binary, no text decode needed ────────
    if ext in ("xlsx", "xls"):
        if not HAS_OPENPYXL:
            return {"columns": [], "rows": [], "error": "openpyxl is not installed. Run: pip install openpyxl"}
        try:
            wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            ws = wb.active
            all_rows = list(ws.iter_rows(values_only=True))
            wb.close()
        except Exception as e:
            return {"columns": [], "rows": [], "error": f"Cannot read Excel file: {e}"}
        if not all_rows:
            return {"columns": [], "rows": [], "error": "Excel file appears to be empty."}
        columns = [str(c) if c is not None else f"col_{i}" for i, c in enumerate(all_rows[0])]
        rows = [[str(cell) if cell is not None else "" for cell in r] for r in all_rows[1:]]
        if not rows:
            return {"columns": [], "rows": [], "error": "Excel file has headers but no data rows."}
        return {"columns": columns, "rows": rows, "error": None}

    # All remaining formats need text decoding
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except Exception:
            return {"columns": [], "rows": [], "error": "Cannot decode file. Please save it as UTF-8."}

    # ── CSV / TSV ────────────────────────────────────────────────────
    if ext in ("csv", "tsv"):
        delimiter = "\t" if ext == "tsv" else ","
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        rows_raw = [dict(r) for r in reader]
        if not rows_raw:
            return {"columns": [], "rows": [], "error": "File appears to be empty."}
        columns = list(rows_raw[0].keys())
        rows = [[r.get(c, "") for c in columns] for r in rows_raw]
        return {"columns": columns, "rows": rows, "error": None}

    # ── JSON (array or wrapped object) ──────────────────────────────
    if ext == "json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return {"columns": [], "rows": [], "error": f"Invalid JSON: {e}"}
        if isinstance(data, dict):
            for key in ("data", "records", "rows", "results", "items"):
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
            else:
                return {"columns": [], "rows": [], "error": "JSON object format not supported. Expected an array of objects."}
        if not isinstance(data, list) or not data:
            return {"columns": [], "rows": [], "error": "JSON array is empty or not an array."}
        if not isinstance(data[0], dict):
            return {"columns": [], "rows": [], "error": "JSON array items must be objects (key-value pairs)."}
        columns = list(data[0].keys())
        rows = [[str(r.get(c, "")) for c in columns] for r in data]
        return {"columns": columns, "rows": rows, "error": None}

    # ── JSONL / NDJSON (one JSON object per line) ────────────────────
    if ext in ("jsonl", "ndjson"):
        records = []
        for i, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                return {"columns": [], "rows": [], "error": f"Invalid JSON on line {i}: {e}"}
            if not isinstance(obj, dict):
                return {"columns": [], "rows": [], "error": f"Line {i} is not a JSON object."}
            records.append(obj)
        if not records:
            return {"columns": [], "rows": [], "error": "File appears to be empty."}
        columns = list(records[0].keys())
        rows = [[str(r.get(c, "")) for c in columns] for r in records]
        return {"columns": columns, "rows": rows, "error": None}

    # ── YAML ─────────────────────────────────────────────────────────
    if ext in ("yaml", "yml"):
        if not HAS_YAML:
            return {"columns": [], "rows": [], "error": "pyyaml is not installed. Run: pip install pyyaml"}
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            return {"columns": [], "rows": [], "error": f"Invalid YAML: {e}"}
        if isinstance(data, dict):
            for key in ("data", "records", "rows", "results", "items"):
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
            else:
                # Try treating dict values as rows if all values are dicts
                if all(isinstance(v, dict) for v in data.values()):
                    data = [{"_key": k, **v} for k, v in data.items()]
                else:
                    return {"columns": [], "rows": [], "error": "YAML object format not supported. Expected a list of objects."}
        if not isinstance(data, list) or not data:
            return {"columns": [], "rows": [], "error": "YAML must contain a list of objects."}
        if not isinstance(data[0], dict):
            return {"columns": [], "rows": [], "error": "YAML list items must be objects (key-value pairs)."}
        columns = list(data[0].keys())
        rows = [[str(r.get(c, "")) for c in columns] for r in data]
        return {"columns": columns, "rows": rows, "error": None}

    # ── XML ──────────────────────────────────────────────────────────
    if ext == "xml":
        try:
            root = ET.fromstring(text)
        except ET.ParseError as e:
            return {"columns": [], "rows": [], "error": f"Invalid XML: {e}"}
        # Collect all child elements (each child = one row)
        children = list(root)
        if not children:
            return {"columns": [], "rows": [], "error": "XML root has no child elements to import as rows."}
        # Gather all unique column names from attributes + sub-element tags
        col_set = []
        col_seen = set()
        for child in children:
            for k in list(child.attrib.keys()) + [sub.tag for sub in child]:
                if k not in col_seen:
                    col_set.append(k)
                    col_seen.add(k)
        if not col_set:
            # Fall back to element text if no attributes/children
            columns = ["tag", "text"]
            rows = [[child.tag, (child.text or "").strip()] for child in children]
        else:
            columns = col_set
            rows = []
            for child in children:
                row = {}
                row.update(child.attrib)
                for sub in child:
                    row[sub.tag] = (sub.text or "").strip()
                rows.append([str(row.get(c, "")) for c in columns])
        return {"columns": columns, "rows": rows, "error": None}

    # ── SQL INSERT dump ──────────────────────────────────────────────
    if ext == "sql":
        # Extract values from INSERT INTO ... VALUES (...) statements
        insert_re = re.compile(
            r"INSERT\s+INTO\s+[`'\"]?\w+[`'\"]?\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)",
            re.IGNORECASE
        )
        matches = insert_re.findall(text)
        if not matches:
            # Try INSERT INTO table VALUES (...)  without column list
            insert_re2 = re.compile(
                r"INSERT\s+INTO\s+[`'\"]?\w+[`'\"]?\s+VALUES\s*\(([^)]+)\)",
                re.IGNORECASE
            )
            val_matches = insert_re2.findall(text)
            if not val_matches:
                return {"columns": [], "rows": [], "error": "No INSERT statements found in the SQL file."}
            rows = [_parse_sql_values(v) for v in val_matches]
            columns = [f"col_{i+1}" for i in range(max(len(r) for r in rows))]
            return {"columns": columns, "rows": rows, "error": None}

        col_str, _ = matches[0]
        columns = [c.strip().strip('`\'"') for c in col_str.split(",")]
        rows = [_parse_sql_values(v_str) for _, v_str in matches]
        return {"columns": columns, "rows": rows, "error": None}

    return {"columns": [], "rows": [], "error": f"Unsupported file type '.{ext}'. Supported: CSV, TSV, JSON, JSONL, Excel, YAML, XML, SQL."}


def _parse_sql_values(val_str: str) -> list:
    """Parse a SQL VALUES(...) string into a list of cell values."""
    vals = []
    for v in re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", val_str):
        v = v.strip()
        if v.upper() == "NULL":
            vals.append("")
        elif v.startswith("'") and v.endswith("'"):
            vals.append(v[1:-1].replace("''", "'"))
        else:
            vals.append(v)
    return vals


def analyze_schema_with_groq(columns: list, sample_rows: list, filename: str) -> dict:
    """Ask Groq to suggest a clean table name, column names, and SQL types."""
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    stem = re.sub(r"[^a-zA-Z0-9 ]", " ", stem).strip()

    sample_text = "\n".join(
        f"Row {i+1}: {dict(zip(columns, row))}"
        for i, row in enumerate(sample_rows[:5])
    )

    prompt = (
        "You are a database schema designer. Analyze the following uploaded file and generate a clean SQLite schema.\n\n"
        f"File name: {filename}\n"
        f"Raw column headers: {json.dumps(columns)}\n\n"
        f"Sample data:\n{sample_text}\n\n"
        "Return ONLY a valid JSON object (no markdown, no explanation):\n"
        "{\n"
        '  "table_name": "snake_case_name",\n'
        '  "display_name": "Human Readable Name",\n'
        '  "columns": [\n'
        '    {"original": "<raw header>", "clean_name": "snake_case_col", "type": "TEXT|INTEGER|REAL"}\n'
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- table_name: lowercase snake_case, descriptive noun based on content (e.g. customers, sales_records, employees)\n"
        "- clean_name: lowercase snake_case, no spaces, no special chars, max 40 chars\n"
        "- type: INTEGER for whole numbers, REAL for decimals/floats, TEXT for everything else\n"
        "- Include ALL columns in the same order as given\n"
        "- Do NOT invent new columns or drop any"
    )

    result = _call_groq([{"role": "user", "content": prompt}], max_tokens=1024, temperature=0.1)

    fallback = {
        "table_name":   sanitize_identifier(stem) or "imported_data",
        "display_name": stem.replace("_", " ").replace("-", " ").title() or "Imported Data",
        "columns":      [{"original": c, "clean_name": sanitize_identifier(c), "type": "TEXT"} for c in columns],
        "error": None,
    }

    if result["error"] or not result["content"]:
        return fallback

    raw = result["content"].strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        schema = json.loads(raw)
        table_name   = sanitize_identifier(schema.get("table_name", stem)) or "imported_data"
        display_name = str(schema.get("display_name", table_name.replace("_", " ").title()))[:80]
        cols_raw     = schema.get("columns", [])
        if len(cols_raw) != len(columns):
            raise ValueError("column count mismatch")
        clean_cols = [
            {
                "original":   str(c.get("original", "")),
                "clean_name": sanitize_identifier(c.get("clean_name", c.get("original", f"col_{i}"))),
                "type":       c.get("type", "TEXT") if c.get("type") in ("TEXT", "INTEGER", "REAL") else "TEXT",
            }
            for i, c in enumerate(cols_raw)
        ]
        return {"table_name": table_name, "display_name": display_name, "columns": clean_cols, "error": None}
    except Exception:
        return fallback


def coerce_value(val, typ: str):
    """Coerce a raw string value to the target SQL type."""
    if val is None or str(val).strip() == "":
        return None
    if typ == "INTEGER":
        try:
            return int(float(str(val)))
        except (ValueError, TypeError):
            return str(val)
    if typ == "REAL":
        try:
            return float(str(val))
        except (ValueError, TypeError):
            return str(val)
    return str(val)


# ─────────────────────────────────────────────
# GROQ HELPER
# ─────────────────────────────────────────────

def _call_groq(messages: list, max_tokens: int = 256, temperature: float = 0.1) -> dict:
    """Shared Groq API caller. Returns {'content': str, 'error': str|None}"""
    if not GROQ_API_KEY:
        return {"content": None, "error": "GROQ_API_KEY is not set."}
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }
    try:
        r = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        return {"content": r.json()["choices"][0]["message"]["content"].strip(), "error": None}
    except requests.exceptions.Timeout:
        return {"content": None, "error": "Groq API request timed out."}
    except requests.exceptions.HTTPError as e:
        return {"content": None, "error": f"Groq API {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"content": None, "error": str(e)}


# ─────────────────────────────────────────────
# AGENT FUNCTIONS
# ─────────────────────────────────────────────

DB_SCHEMA_CONTEXT = """
The database has three tables:

  users(id INTEGER PK, name TEXT, email TEXT, age INTEGER, city TEXT, created_at TEXT)
  products(id INTEGER PK, name TEXT, category TEXT, price REAL, stock INTEGER)
  orders(id INTEGER PK, user_id INTEGER FK→users.id, product_id INTEGER FK→products.id,
         quantity INTEGER, total_price REAL, status TEXT, order_date TEXT)

Statuses in orders: 'completed', 'shipped', 'pending', 'cancelled'
Categories in products: 'Electronics', 'Sports', 'Books', 'Clothing', 'Home'
"""


def generate_sql_with_groq(natural_language: str) -> dict:
    """Agent 1 – Natural language → SQL."""
    system_prompt = (
        "You are an expert SQL assistant.\n" + DB_SCHEMA_CONTEXT + "\n"
        "Convert the user's natural language request into a valid SQLite query.\n\n"
        "Rules:\n"
        "- Return ONLY the raw SQL — no markdown, no explanation, no code fences.\n"
        "- Use only standard SQLite syntax. End with a semicolon.\n"
        "- For JOINs across tables use the correct foreign keys.\n"
        "- Never invent columns that don't exist in the schema above.\n"
        "- Only use = for exact values like numeric IDs.\n"
        "- LIKE pattern rules — choose carefully based on the user's intent:\n"
        "    'starts with X'   → LIKE 'X%'    (no leading wildcard)\n"
        "    'ends with X'     → LIKE '%X'    (no trailing wildcard)\n"
        "    'contains X'      → LIKE '%X%'   (wildcards on both sides)\n"
        "    partial/unknown   → LIKE '%X%'   (default for vague searches)\n"
        "- String comparisons are case-insensitive via LIKE by default in SQLite.\n"
        "- Example: 'users whose name starts with A' → WHERE name LIKE 'A%'"
    )
    result = _call_groq([
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": natural_language},
    ], max_tokens=512)
    if result["error"]:
        return {"sql": None, "error": result["error"]}
    raw = result["content"]
    raw = re.sub(r"^```(?:sql)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    return {"sql": raw.strip(), "error": None}


def explain_sql_with_groq(sql: str, natural_language: str) -> str:
    """Agent 1b – Explain in plain English what the SQL does."""
    system_prompt = (
        "You are a friendly SQL tutor. Explain in 1-2 clear sentences what this SQL query does, "
        "in plain English a student can understand. Be specific about what data it retrieves or modifies. "
        "Do not repeat the SQL. Do not use technical jargon unnecessarily."
    )
    result = _call_groq([
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": f"Original request: {natural_language}\nSQL: {sql}"},
    ], max_tokens=150, temperature=0.2)
    return result["content"] or "Could not generate explanation."


def auto_fix_sql(sql: str, error: str, natural_language: str) -> dict:
    """Agent 1c – Auto-rewrite broken SQL given the execution error."""
    system_prompt = (
        "You are an expert SQL debugger.\n" + DB_SCHEMA_CONTEXT + "\n"
        "The SQL query below failed with an error. Rewrite it so it runs correctly.\n"
        "Return ONLY the corrected raw SQL — no explanation, no code fences, no markdown."
    )
    result = _call_groq([
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": f"Original request: {natural_language}\nFailed SQL: {sql}\nError: {error}"},
    ], max_tokens=512)
    if result["error"] or not result["content"]:
        return {"sql": None, "error": result["error"]}
    raw = re.sub(r"^```(?:sql)?\s*", "", result["content"], flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    return {"sql": raw.strip(), "error": None}


def analyze_structure(sql: str) -> dict:
    """Agent 2 – Structural analysis of SQL text."""
    sql_upper = sql.upper()

    for stmt in ["SELECT","INSERT","UPDATE","DELETE","DROP","ALTER","CREATE"]:
        if sql_upper.lstrip().startswith(stmt):
            stmt_type = stmt
            break
    else:
        stmt_type = "UNKNOWN"

    has_where = bool(re.search(r'\bWHERE\b', sql_upper))
    has_limit = bool(re.search(r'\bLIMIT\b',  sql_upper))
    has_drop  = bool(re.search(r'\bDROP\b',   sql_upper))
    has_alter = bool(re.search(r'\bALTER\b',  sql_upper))

    issues = []
    if has_drop:  issues.append("DROP statement detected – destructive operation")
    if has_alter: issues.append("ALTER statement detected – schema modification")
    if stmt_type == "DELETE" and not has_where: issues.append("DELETE without WHERE – would delete ALL rows")
    if stmt_type == "UPDATE" and not has_where: issues.append("UPDATE without WHERE – would update ALL rows")
    if stmt_type == "SELECT" and not has_limit: issues.append("SELECT without LIMIT – may return unbounded results")

    return {
        "statement_type": stmt_type,
        "has_where": has_where,
        "has_limit": has_limit,
        "has_drop":  has_drop,
        "has_alter": has_alter,
        "issues":    issues,
    }


def analyze_execution_plan(sql: str) -> dict:
    """Agent 3 – EXPLAIN QUERY PLAN to detect full table scans."""
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"EXPLAIN QUERY PLAN {sql}")
        rows  = cursor.fetchall()
        conn.close()
        plan_lines = [str(r) for r in rows]
        full_scan  = any("SCAN" in l.upper() and "INDEX" not in l.upper() for l in plan_lines)
        return {"plan": plan_lines, "full_scan": full_scan, "error": None}
    except Exception as e:
        return {"plan": [], "full_scan": False, "error": str(e)}


def calculate_risk(structure: dict, plan: dict) -> dict:
    """Agent 4 – Numeric risk scoring."""
    score     = 0
    breakdown = []

    if structure["has_drop"] or structure["has_alter"]:
        score += 100; breakdown.append("+100  DROP or ALTER detected")

    stmt = structure["statement_type"]
    if stmt == "DELETE" and not structure["has_where"]:
        score += 80;  breakdown.append("+80   DELETE without WHERE")
    if stmt == "UPDATE" and not structure["has_where"]:
        score += 70;  breakdown.append("+70   UPDATE without WHERE")
    if stmt == "SELECT" and not structure["has_limit"]:
        score += 30;  breakdown.append("+30   SELECT without LIMIT")
    if plan["full_scan"]:
        score += 20;  breakdown.append("+20   Full table scan detected")

    level = "LOW" if score <= 20 else "MEDIUM" if score <= 50 else "HIGH" if score <= 80 else "CRITICAL"
    return {"score": score, "level": level, "breakdown": breakdown}


def enforce_policy(sql: str, structure: dict, risk: dict) -> dict:
    """Agent 5 – Block, revise, or clear for execution."""
    level = risk["level"]
    stmt  = structure["statement_type"]

    if structure["has_drop"] or structure["has_alter"]:
        return {"action":"BLOCKED","safe_sql":None,"message":"DROP and ALTER statements are permanently blocked for safety."}
    if stmt == "DELETE" and not structure["has_where"]:
        return {"action":"BLOCKED","safe_sql":None,"message":"DELETE without a WHERE clause is blocked to prevent data loss."}
    if stmt == "UPDATE" and not structure["has_where"]:
        return {"action":"BLOCKED","safe_sql":None,"message":"UPDATE without a WHERE clause is blocked to prevent mass changes."}

    safe_sql = sql
    if stmt == "SELECT" and not structure["has_limit"]:
        safe_sql = re.sub(r'\s*;?\s*$', '', sql.strip()) + ' LIMIT 50;'

    if level == "HIGH":
        return {"action":"REVISED","safe_sql":safe_sql,"message":"Query is HIGH risk. A safer version has been prepared — review and confirm to execute."}
    if level in ("LOW","MEDIUM"):
        return {"action":"EXECUTE","safe_sql":safe_sql,"message":f"Query is {level} risk. Executing the safe version."}

    return {"action":"BLOCKED","safe_sql":None,"message":"CRITICAL risk detected. Query blocked."}


def execute_safe_sql(sql: str) -> dict:
    """Execute a validated SQL query and return results."""
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        rows    = [list(r) for r in cursor.fetchall()]
        conn.commit()
        conn.close()
        return {"columns": columns, "rows": rows, "error": None}
    except Exception as e:
        return {"columns": [], "rows": [], "error": str(e)}


def save_to_history(nl, original_sql, safe_sql, risk_level, risk_score, action, row_count):
    """Persist a query run to query_history."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO query_history (natural_language,original_sql,safe_sql,risk_level,risk_score,action,row_count) "
            "VALUES (?,?,?,?,?,?,?)",
            (nl, original_sql, safe_sql, risk_level, risk_score, action, row_count)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def orchestrator(natural_language: str) -> dict:
    """Main pipeline: generate → analyse → risk → policy → explain → execute → save."""
    # 1. Generate SQL
    gen = generate_sql_with_groq(natural_language)
    if gen["error"]:
        return {"error": gen["error"]}
    sql = gen["sql"]

    # 2. Structural analysis
    structure = analyze_structure(sql)

    # 3. Execution plan
    plan = analyze_execution_plan(sql)

    # 4. Risk assessment
    risk = calculate_risk(structure, plan)

    # 5. Policy enforcement
    policy = enforce_policy(sql, structure, risk)

    # 6. Explain what the SQL does (non-blocking)
    explanation = explain_sql_with_groq(sql, natural_language)

    # 7. Execute (only EXECUTE action)
    results   = None
    row_count = 0
    if policy["action"] == "EXECUTE" and policy["safe_sql"]:
        results = execute_safe_sql(policy["safe_sql"])
        # Auto-fix if execution failed
        if results and results["error"]:
            fix = auto_fix_sql(policy["safe_sql"], results["error"], natural_language)
            if fix["sql"]:
                fixed_structure = analyze_structure(fix["sql"])
                fixed_safe = fix["sql"]
                if fixed_structure["statement_type"] == "SELECT" and not fixed_structure["has_limit"]:
                    fixed_safe = re.sub(r'\s*;?\s*$', '', fix["sql"].strip()) + ' LIMIT 50;'
                retry = execute_safe_sql(fixed_safe)
                if not retry["error"]:
                    results         = retry
                    results["auto_fixed"]   = True
                    results["fixed_sql"]    = fixed_safe
        if results:
            row_count = len(results.get("rows", []))

    # 8. Save to history
    save_to_history(
        natural_language, sql,
        policy.get("safe_sql"), risk["level"], risk["score"],
        policy["action"], row_count
    )

    return {
        "original_sql":  sql,
        "explanation":   explanation,
        "structure":     structure,
        "plan":          plan,
        "risk":          risk,
        "policy":        policy,
        "results":       results,
    }


# ─────────────────────────────────────────────
# ROUTES – Pages
# ─────────────────────────────────────────────

@app.route("/")
def home():      return render_template("index.html")

@app.route("/app")
def app_page():  return render_template("app.html")

@app.route("/wiki")
def wiki():      return render_template("wiki.html")

@app.route("/about")
def about():     return render_template("about.html")

@app.route("/database")
def database_page(): return render_template("database.html")

@app.route("/dashboard")
def dashboard_page(): return render_template("dashboard.html")

@app.route("/simulator")
def simulator_page(): return render_template("simulator.html")

@app.route("/upload")
def upload_page(): return render_template("upload.html")


# ─────────────────────────────────────────────
# ROUTES – Query API
# ─────────────────────────────────────────────

@app.route("/api/query", methods=["POST"])
def api_query():
    data = request.get_json(force=True)
    nl   = (data.get("query") or "").strip()
    if not nl:
        return jsonify({"error": "Please enter a natural language query."}), 400
    return jsonify(orchestrator(nl))


@app.route("/api/execute_revised", methods=["POST"])
def api_execute_revised():
    """Execute a pre-validated revised SQL (from REVISED decision)."""
    data = request.get_json(force=True)
    sql  = (data.get("sql") or "").strip()
    if not sql:
        return jsonify({"error": "No SQL provided."}), 400
    results = execute_safe_sql(sql)
    return jsonify(results)


# ─────────────────────────────────────────────
# ROUTES – History API
# ─────────────────────────────────────────────

@app.route("/api/history")
def api_history():
    limit = request.args.get("limit", 20, type=int)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, natural_language, original_sql, safe_sql,
                   risk_level, risk_score, action, row_count, created_at
            FROM query_history ORDER BY id DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        conn.close()
        return jsonify({"history": [dict(zip(cols,r)) for r in rows]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# ROUTES – Dashboard Stats API
# ─────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    try:
        conn    = sqlite3.connect(DB_PATH)
        cursor  = conn.cursor()

        # Query history stats
        cursor.execute("SELECT COUNT(*) FROM query_history")
        total_queries = cursor.fetchone()[0]

        cursor.execute("SELECT risk_level, COUNT(*) FROM query_history GROUP BY risk_level")
        risk_dist = dict(cursor.fetchall())

        cursor.execute("SELECT action, COUNT(*) FROM query_history GROUP BY action")
        action_dist = dict(cursor.fetchall())

        cursor.execute("SELECT AVG(risk_score) FROM query_history")
        avg_score = round(cursor.fetchone()[0] or 0, 1)

        cursor.execute("""
            SELECT substr(natural_language,1,60), risk_level, action, risk_score, created_at
            FROM query_history ORDER BY id DESC LIMIT 10
        """)
        recent = [{"nl":r[0],"risk_level":r[1],"action":r[2],"risk_score":r[3],"created_at":r[4]}
                  for r in cursor.fetchall()]

        # DB table stats
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM products")
        product_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]

        cursor.execute("SELECT status, COUNT(*) FROM orders GROUP BY status")
        order_status = dict(cursor.fetchall())

        cursor.execute("SELECT category, COUNT(*) FROM products GROUP BY category")
        product_cats = dict(cursor.fetchall())

        cursor.execute("SELECT SUM(total_price) FROM orders WHERE status='completed'")
        total_revenue = round(cursor.fetchone()[0] or 0, 2)

        conn.close()
        db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0

        return jsonify({
            "queries": {
                "total":       total_queries,
                "risk_dist":   risk_dist,
                "action_dist": action_dist,
                "avg_score":   avg_score,
                "recent":      recent,
            },
            "db": {
                "users":         user_count,
                "products":      product_count,
                "orders":        order_count,
                "order_status":  order_status,
                "product_cats":  product_cats,
                "total_revenue": total_revenue,
                "size_bytes":    db_size,
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# ROUTES – Database Management API
# ─────────────────────────────────────────────

@app.route("/api/db/snapshot")
def api_db_snapshot():
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users ORDER BY id")
        rows    = [list(r) for r in cursor.fetchall()]
        columns = [d[0] for d in cursor.description]

        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
        create_sql = cursor.fetchone()[0]

        cursor.execute("PRAGMA table_info(users)")
        schema = [{"cid":r[0],"name":r[1],"type":r[2],"notnull":bool(r[3]),"pk":bool(r[5])}
                  for r in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]

        conn.close()
        db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0

        return jsonify({
            "columns": columns, "rows": rows,
            "create_sql": create_sql, "schema": schema,
            "stats": {"total_rows": total, "table_count": table_count, "db_size_bytes": db_size}
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/db/users", methods=["POST"])
def api_add_user():
    data  = request.get_json(force=True)
    name  = (data.get("name")  or "").strip()
    email = (data.get("email") or "").strip()
    age   = data.get("age")
    city  = (data.get("city")  or "").strip() or None
    if not name or not email:
        return jsonify({"error": "Name and email are required."}), 400
    if "@" not in email:
        return jsonify({"error": "Please enter a valid email address."}), 400
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name,email,age,city,created_at) VALUES (?,?,?,?,date('now'))",
            (name, email, age, city)
        )
        new_id = cursor.lastrowid
        conn.commit(); conn.close()
        return jsonify({"success":True,"id":new_id,"name":name,"email":email,"age":age,"city":city})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/db/users/<int:user_id>", methods=["DELETE"])
def api_delete_user(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id=?", (user_id,))
        if not cursor.fetchone():
            conn.close(); return jsonify({"error": f"User #{user_id} not found."}), 404
        cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit(); conn.close()
        return jsonify({"success":True,"deleted_id":user_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/db/users/<int:user_id>", methods=["PUT"])
def api_update_user(user_id):
    data  = request.get_json(force=True)
    name  = (data.get("name")  or "").strip()
    email = (data.get("email") or "").strip()
    if not name or not email: return jsonify({"error":"Name and email are required."}), 400
    if "@" not in email:      return jsonify({"error":"Please enter a valid email address."}), 400
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id=?", (user_id,))
        if not cursor.fetchone():
            conn.close(); return jsonify({"error":f"User #{user_id} not found."}), 404
        cursor.execute("UPDATE users SET name=?,email=? WHERE id=?", (name,email,user_id))
        conn.commit(); conn.close()
        return jsonify({"success":True,"id":user_id,"name":name,"email":email})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/db/table/<table_name>")
def api_db_table(table_name):
    """Generic read endpoint for built-in and user-uploaded tables."""
    safe_name = sanitize_identifier(table_name)
    if safe_name != table_name:
        return jsonify({"error": "Invalid table name."}), 400
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Confirm the table exists in sqlite_master
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": f"no such table: {table_name}"}), 404

        if table_name == "orders":
            # Use JOIN only when both referenced tables exist; otherwise fall back
            existing = {r[0] for r in cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
            if "users" in existing and "products" in existing:
                cursor.execute("""
                    SELECT o.id,
                           u.name  AS user_name,
                           p.name  AS product_name,
                           o.quantity,
                           o.total_price,
                           o.status,
                           o.order_date
                    FROM   orders  o
                    LEFT JOIN users    u ON u.id = o.user_id
                    LEFT JOIN products p ON p.id = o.product_id
                    ORDER BY o.id
                """)
            else:
                cursor.execute("SELECT * FROM orders ORDER BY id")
        else:
            cursor.execute(f'SELECT * FROM "{table_name}" ORDER BY id')

        rows    = [list(r) for r in cursor.fetchall()]
        columns = [d[0] for d in cursor.description]

        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        row = cursor.fetchone()
        create_sql = row[0] if row else ""

        cursor.execute(f'PRAGMA table_info("{table_name}")')
        schema = [{"cid":r[0],"name":r[1],"type":r[2],"notnull":bool(r[3]),"pk":bool(r[5])}
                  for r in cursor.fetchall()]

        cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]

        conn.close()
        db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0

        return jsonify({
            "table":      table_name,
            "columns":    columns,
            "rows":       rows,
            "create_sql": create_sql,
            "schema":     schema,
            "stats":      {"total_rows": total, "table_count": table_count, "db_size_bytes": db_size},
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _reseed_all():
    """
    Unconditionally drop-and-recreate every built-in table then reseed it.
    Runs inside a single connection/transaction for atomicity.
    """
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")

    # ── drop in reverse-dependency order ─────────────────────────
    for tbl in ("orders", "query_history", "products", "users"):
        cursor.execute(f'DROP TABLE IF EXISTS "{tbl}"')

    # ── users ─────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    NOT NULL,
            age        INTEGER,
            city       TEXT,
            created_at TEXT    DEFAULT (date('now'))
        )
    """)
    cursor.executemany(
        "INSERT INTO users (name,email,age,city,created_at) VALUES (?,?,?,?,?)",
        [
            ("Alice Johnson","alice.johnson@example.com",28,"New York","2023-01-15"),
            ("Bob Smith","bob.smith@example.com",34,"Los Angeles","2023-02-20"),
            ("Carol Davis","carol.davis@example.com",22,"Chicago","2023-03-05"),
            ("David Lee","david.lee@example.com",45,"Houston","2023-03-18"),
            ("Eva Martinez","eva.martinez@example.com",31,"Phoenix","2023-04-02"),
            ("Frank Wilson","frank.wilson@example.com",38,"Philadelphia","2023-04-14"),
            ("Grace Thompson","grace.thompson@example.com",26,"San Antonio","2023-04-29"),
            ("Henry Anderson","henry.anderson@example.com",52,"San Diego","2023-05-10"),
            ("Isabella Thomas","isabella.thomas@example.com",24,"Dallas","2023-05-22"),
            ("James Jackson","james.jackson@example.com",41,"San Jose","2023-06-01"),
            ("Karen White","karen.white@example.com",33,"Austin","2023-06-15"),
            ("Liam Harris","liam.harris@example.com",29,"Jacksonville","2023-06-28"),
            ("Mia Martin","mia.martin@example.com",27,"Fort Worth","2023-07-09"),
            ("Noah Garcia","noah.garcia@example.com",36,"Columbus","2023-07-20"),
            ("Olivia Brown","olivia.brown@example.com",23,"San Francisco","2023-07-31"),
            ("Paul Miller","paul.miller@example.com",48,"Charlotte","2023-08-11"),
            ("Quinn Robinson","quinn.robinson@example.com",32,"Indianapolis","2023-08-22"),
            ("Rachel Clark","rachel.clark@example.com",25,"Seattle","2023-09-02"),
            ("Samuel Lewis","samuel.lewis@example.com",44,"Denver","2023-09-13"),
            ("Tina Walker","tina.walker@example.com",30,"Boston","2023-09-24"),
            ("Uma Hall","uma.hall@example.com",37,"Nashville","2023-10-05"),
            ("Victor Allen","victor.allen@example.com",55,"Oklahoma City","2023-10-16"),
            ("Wendy Young","wendy.young@example.com",21,"El Paso","2023-10-27"),
            ("Xander Hernandez","xander.hernandez@example.com",40,"Washington DC","2023-11-07"),
            ("Yasmine King","yasmine.king@example.com",28,"Las Vegas","2023-11-18"),
            ("Zach Wright","zach.wright@example.com",35,"Memphis","2023-11-29"),
            ("Amber Scott","amber.scott@example.com",26,"Louisville","2023-12-10"),
            ("Brian Torres","brian.torres@example.com",43,"Portland","2023-12-21"),
            ("Chloe Nguyen","chloe.nguyen@example.com",24,"Baltimore","2024-01-01"),
            ("Derek Hill","derek.hill@example.com",39,"Milwaukee","2024-01-12"),
            ("Elena Flores","elena.flores@example.com",31,"New York","2024-01-23"),
            ("Felix Green","felix.green@example.com",47,"Los Angeles","2024-02-03"),
            ("Gina Adams","gina.adams@example.com",22,"Chicago","2024-02-14"),
            ("Hugo Nelson","hugo.nelson@example.com",58,"Houston","2024-02-25"),
            ("Iris Carter","iris.carter@example.com",27,"Phoenix","2024-03-07"),
            ("Jake Mitchell","jake.mitchell@example.com",34,"San Diego","2024-03-18"),
            ("Kylie Perez","kylie.perez@example.com",20,"Austin","2024-03-29"),
            ("Leon Roberts","leon.roberts@example.com",42,"Seattle","2024-04-09"),
            ("Maya Turner","maya.turner@example.com",29,"Denver","2024-04-20"),
            ("Nathan Phillips","nathan.phillips@example.com",36,"Boston","2024-05-01"),
            ("Opal Campbell","opal.campbell@example.com",33,"San Francisco","2024-05-12"),
            ("Pedro Parker","pedro.parker@example.com",25,"Dallas","2024-05-23"),
            ("Quinn Evans","quinn.evans@example.com",38,"Charlotte","2024-06-03"),
            ("Rosa Edwards","rosa.edwards@example.com",30,"Nashville","2024-06-14"),
            ("Steve Collins","steve.collins@example.com",51,"Indianapolis","2024-06-25"),
            ("Tara Stewart","tara.stewart@example.com",23,"Las Vegas","2024-07-06"),
            ("Ulric Sanchez","ulric.sanchez@example.com",44,"Portland","2024-07-17"),
            ("Vera Morris","vera.morris@example.com",28,"Baltimore","2024-07-28"),
            ("Walter Rogers","walter.rogers@example.com",60,"Columbus","2024-08-08"),
            ("Xena Reed","xena.reed@example.com",32,"Fort Worth","2024-08-19"),
        ]
    )

    # ── products ──────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE products (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            category TEXT    NOT NULL,
            price    REAL    NOT NULL,
            stock    INTEGER NOT NULL
        )
    """)
    cursor.executemany(
        "INSERT INTO products (name,category,price,stock) VALUES (?,?,?,?)",
        [
            ("Wireless Headphones","Electronics",79.99,120),
            ("Mechanical Keyboard","Electronics",149.99,45),
            ("4K Monitor","Electronics",399.99,30),
            ("USB-C Hub","Electronics",39.99,200),
            ("Laptop Stand","Electronics",29.99,150),
            ("Running Shoes","Sports",89.99,80),
            ("Yoga Mat","Sports",24.99,200),
            ("Dumbbell Set","Sports",59.99,60),
            ("Water Bottle","Sports",14.99,300),
            ("Resistance Bands","Sports",12.99,250),
            ("Python Programming","Books",39.99,500),
            ("SQL Mastery","Books",29.99,300),
            ("Data Science Guide","Books",44.99,200),
            ("Clean Code","Books",34.99,400),
            ("Design Patterns","Books",49.99,150),
            ("Cotton T-Shirt","Clothing",19.99,500),
            ("Denim Jeans","Clothing",49.99,200),
            ("Winter Jacket","Clothing",129.99,80),
            ("Desk Organizer","Home",22.99,180),
            ("LED Desk Lamp","Home",35.99,120),
        ]
    )

    # ── orders ────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            product_id  INTEGER NOT NULL,
            quantity    INTEGER NOT NULL,
            total_price REAL    NOT NULL,
            status      TEXT    NOT NULL,
            order_date  TEXT    NOT NULL,
            FOREIGN KEY (user_id)    REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    cursor.executemany(
        "INSERT INTO orders (user_id,product_id,quantity,total_price,status,order_date) VALUES (?,?,?,?,?,?)",
        [
            (1,1,1,79.99,"completed","2024-01-10"),
            (2,3,2,299.98,"completed","2024-01-15"),
            (3,5,1,79.99,"shipped","2024-01-20"),
            (4,2,4,39.99,"completed","2024-01-22"),
            (5,7,6,89.99,"completed","2024-02-01"),
            (6,1,11,39.99,"completed","2024-02-05"),
            (7,9,2,149.99,"pending","2024-02-10"),
            (8,4,16,19.99,"completed","2024-02-14"),
            (9,11,8,59.99,"cancelled","2024-02-18"),
            (10,6,20,35.99,"completed","2024-02-22"),
            (11,13,12,29.99,"shipped","2024-03-01"),
            (12,3,17,49.99,"completed","2024-03-05"),
            (13,15,3,399.99,"completed","2024-03-10"),
            (14,8,9,29.98,"completed","2024-03-15"),
            (15,20,14,34.99,"pending","2024-03-20"),
            (16,2,6,89.99,"completed","2024-04-01"),
            (17,5,13,44.99,"completed","2024-04-05"),
            (18,12,18,129.99,"shipped","2024-04-10"),
            (19,7,5,29.99,"completed","2024-04-15"),
            (20,17,10,12.99,"completed","2024-04-20"),
            (21,25,15,49.99,"completed","2024-05-01"),
            (22,30,1,79.99,"pending","2024-05-05"),
            (23,10,7,24.99,"completed","2024-05-10"),
            (24,35,2,149.99,"cancelled","2024-05-15"),
            (25,4,19,22.99,"completed","2024-05-20"),
            (26,40,11,39.99,"shipped","2024-06-01"),
            (27,22,4,79.98,"completed","2024-06-05"),
            (28,14,16,39.98,"completed","2024-06-10"),
            (29,8,13,44.99,"completed","2024-06-15"),
            (30,50,20,35.99,"pending","2024-06-20"),
        ]
    )

    # ── query_history ─────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE query_history (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            natural_language TEXT    NOT NULL,
            original_sql     TEXT    NOT NULL,
            safe_sql         TEXT,
            risk_level       TEXT    NOT NULL,
            risk_score       INTEGER NOT NULL,
            action           TEXT    NOT NULL,
            row_count        INTEGER DEFAULT 0,
            created_at       TEXT    DEFAULT (datetime('now','localtime'))
        )
    """)

    cursor.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


@app.route("/api/db/restore", methods=["POST"])
def api_db_restore():
    """Restore all built-in tables to their default seeded state."""
    try:
        _reseed_all()
        return jsonify({"success": True, "message": "All tables restored and reseeded."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/db/tables")
def api_db_tables():
    """List all tables: built-ins + user-uploaded."""
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        all_tables = {r[0] for r in cursor.fetchall()}

        cursor.execute("SELECT table_name, display_name, source_file, row_count, created_at FROM user_tables ORDER BY created_at")
        user_rows = cursor.fetchall()
        conn.close()

        user_tables = []
        for r in user_rows:
            tname = r[0]
            if tname in all_tables:
                user_tables.append({
                    "table_name":   tname,
                    "display_name": r[1],
                    "source_file":  r[2],
                    "row_count":    r[3],
                    "created_at":   r[4],
                })
        return jsonify({"user_tables": user_tables})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Parse a user file, let AI design the schema, then create + populate the table."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "No file selected."}), 400

    filename = f.filename

    # 1. Parse
    parsed = parse_uploaded_file(f, filename)
    if parsed["error"]:
        return jsonify({"error": parsed["error"]}), 400

    columns   = parsed["columns"]
    data_rows = parsed["rows"]

    if not columns:
        return jsonify({"error": "No columns found in the file."}), 400
    if not data_rows:
        return jsonify({"error": "The file has no data rows."}), 400
    if len(columns) > 60:
        return jsonify({"error": "Too many columns (max 60)."}), 400
    if len(data_rows) > 50000:
        return jsonify({"error": "File too large (max 50,000 rows)."}), 400

    # 2. AI schema analysis
    schema = analyze_schema_with_groq(columns, data_rows[:5], filename)

    table_name   = schema["table_name"]
    display_name = schema["display_name"]
    col_schema   = schema["columns"]
    ai_used      = not bool(schema.get("error"))

    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Make table name unique
        existing = {r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        base_name = table_name
        suffix    = 2
        while table_name in existing:
            table_name = f"{base_name}_{suffix}"
            suffix    += 1

        # 3. Deduplicate clean column names (guard against AI duplicates or clash with built-in 'id' PK)
        seen_names: set = {"id"}   # 'id' is already used by the PK
        deduped = []
        for col in col_schema:
            name = col["clean_name"]
            if name in seen_names:
                suffix = 2
                while f"{name}_{suffix}" in seen_names:
                    suffix += 1
                name = f"{name}_{suffix}"
            seen_names.add(name)
            deduped.append({**col, "clean_name": name})
        col_schema = deduped

        # 4. Build CREATE TABLE
        col_defs   = ", ".join(f'"{c["clean_name"]}" {c["type"]}' for c in col_schema)
        create_sql = f'CREATE TABLE "{table_name}" (id INTEGER PRIMARY KEY AUTOINCREMENT, {col_defs})'
        cursor.execute(create_sql)

        # 5. Insert rows
        col_names    = ", ".join(f'"{c["clean_name"]}"' for c in col_schema)
        placeholders = ", ".join("?" * len(col_schema))
        insert_sql   = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'
        coerced_rows = [
            [coerce_value(row[i], col_schema[i]["type"]) for i in range(len(col_schema))]
            for row in data_rows
        ]
        cursor.executemany(insert_sql, coerced_rows)

        # 5. Register in user_tables
        cursor.execute(
            "INSERT OR REPLACE INTO user_tables (table_name, display_name, source_file, row_count) VALUES (?,?,?,?)",
            (table_name, display_name, filename, len(data_rows))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    sample_rows = [list(r) for r in coerced_rows[:5]]
    clean_cols  = [c["clean_name"] for c in col_schema]

    return jsonify({
        "success":      True,
        "table_name":   table_name,
        "display_name": display_name,
        "source_file":  filename,
        "row_count":    len(data_rows),
        "ai_used":      ai_used,
        "columns":      col_schema,
        "sample_rows":  sample_rows,
        "create_sql":   create_sql,
    })


@app.route("/api/db/drop_uploaded/<table_name>", methods=["POST"])
def api_drop_uploaded(table_name):
    """Drop a user-uploaded table."""
    safe = sanitize_identifier(table_name)
    if safe != table_name:
        return jsonify({"error": "Invalid table name."}), 400
    if table_name in BUILTIN_TABLES:
        return jsonify({"error": "Cannot drop built-in tables."}), 400
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        cursor.execute("DELETE FROM user_tables WHERE table_name=?", (table_name,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "dropped": table_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/force_execute", methods=["POST"])
def api_force_execute():
    """Force-execute a blocked SQL after explicit user approval."""
    data  = request.get_json(force=True)
    sql   = (data.get("sql")   or "").strip()
    nl    = (data.get("nl")    or "[Force executed]").strip()
    token = data.get("override_token", "")

    if token != "OVERRIDE_CONFIRMED":
        return jsonify({"error": "Missing override confirmation token."}), 400
    if not sql:
        return jsonify({"error": "No SQL provided."}), 400

    results = execute_safe_sql(sql)
    row_count = len(results.get("rows", [])) if results else 0
    save_to_history(nl, sql, sql, "CRITICAL", 999, "FORCED", row_count)
    return jsonify({**results, "forced": True})


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
