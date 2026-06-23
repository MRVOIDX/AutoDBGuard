# 🛡️ AutoDBGuard

<div align="center">

### AI-Powered Risk-Aware SQL Security Platform

Generate SQL from natural language, analyze database risk in real time, automatically detect dangerous operations, and safely manage structured data imports.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-black)
![SQLite](https://img.shields.io/badge/SQLite-Database-blue)
![Groq](https://img.shields.io/badge/Groq-LLM-orange)
![Llama](https://img.shields.io/badge/Llama%203-AI-green)
![Status](https://img.shields.io/badge/Status-Active-success)

</div>

---

## 🚀 Overview

AutoDBGuard is an intelligent database protection system that combines Large Language Models, risk analysis, execution-plan inspection, and policy enforcement into a single platform.

Instead of directly executing AI-generated SQL, AutoDBGuard evaluates every query through a multi-agent security pipeline before allowing access to the database.

This dramatically reduces the risk of:

- Accidental data deletion
- Unsafe UPDATE statements
- Full-table modifications
- Destructive schema changes
- Poorly optimized queries
- AI hallucinated SQL

---

# ✨ Core Features

## 🤖 Natural Language → SQL

Describe what you want in plain English.

Example:

```text
Show all users older than 30 living in Chicago
```

AutoDBGuard generates SQL automatically.

---

## 🛡️ 5-Agent Security Pipeline

### Agent 1 — Orchestrator

Coordinates the entire workflow.

### Agent 2 — SQL Generator

Uses Groq + Llama 3 to generate SQL.

### Agent 3 — Structure Analyzer

Checks for:

- DROP TABLE
- ALTER TABLE
- DELETE statements
- Missing WHERE clauses
- Dangerous patterns

### Agent 4 — Execution Planner

Runs:

```sql
EXPLAIN QUERY PLAN
```

and evaluates database impact.

### Agent 5 — Risk Scoring Agent

Assigns:

- 🟢 LOW
- 🟡 MEDIUM
- 🟠 HIGH
- 🔴 CRITICAL

risk levels.

---

## 🔒 Policy Enforcement

Queries can be:

- Executed
- Revised
- Blocked

based on risk level.

---

## 🔧 AI Query Revision

Unsafe queries can be automatically revised and improved before execution.

---

## 📜 Audit Logging

Every action is recorded.

Track:

- Generated SQL
- Risk score
- Execution status
- Query history
- Overrides

---

# 📂 Smart Data Import System

AutoDBGuard includes an AI-assisted schema generator capable of importing multiple file formats.

## Supported Formats

| Format | Supported |
|----------|------------|
| CSV | ✅ |
| TSV | ✅ |
| JSON | ✅ |
| JSONL | ✅ |
| NDJSON | ✅ |
| Excel XLSX | ✅ |
| Excel XLS | ✅ |
| XML | ✅ |
| YAML | ✅ |
| YML | ✅ |
| SQL Datasets | ✅ |

---

## 🧠 AI Schema Generation

When a file is uploaded:

1. Data is parsed
2. Sample rows are analyzed
3. Groq AI generates:
   - Table name
   - Display name
   - Clean column names
   - SQLite data types
4. Table is created automatically
5. Data is inserted

No manual schema design required.

---

# 🗄️ Database Management

Built-in database browser allows:

- View tables
- Search records
- Edit records
- Inspect uploaded tables
- Delete uploaded tables
- Restore demo dataset

---

# 📊 Dashboard & Analytics

Visualize:

- Query activity
- Risk distribution
- Security metrics
- Historical execution data

---

# 🎮 Risk Simulator

Test SQL statements without affecting production data.

Perfect for:

- Education
- Training
- Demonstrations
- Security testing

---

# 🏗️ Architecture

```text
User Input
     │
     ▼
Natural Language
     │
     ▼
┌─────────────────────┐
│ Orchestrator Agent  │
└─────────────────────┘
            │
            ▼
┌─────────────────────┐
│ SQL Generation AI   │
└─────────────────────┘
            │
            ▼
┌─────────────────────┐
│ Structure Analysis  │
└─────────────────────┘
            │
            ▼
┌─────────────────────┐
│ Query Plan Review   │
└─────────────────────┘
            │
            ▼
┌─────────────────────┐
│ Risk Scoring Agent  │
└─────────────────────┘
            │
            ▼
┌─────────────────────┐
│ Policy Enforcement  │
└─────────────────────┘
      │          │
      ▼          ▼
 Execute      Block
```

---

# ⚙️ Installation

## Clone Repository

```bash
git clone https://github.com/mrvoidx/AutoDBGuard.git
cd AutoDBGuard
```

## Create Virtual Environment

```bash
python -m venv venv
```

### Linux / macOS

```bash
source venv/bin/activate
```

### Windows

```bash
venv\Scripts\activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Configure Environment

Create:

```env
GROQ_API_KEY=your_key_here
```

Get a free API key from:

https://console.groq.com

---

# ▶️ Run

```bash
python app.py
```

Open:

```text
http://localhost:5000
```

---

# 🌐 Application Pages

| Route | Description |
|---------|-------------|
| / | Home |
| /app | AI SQL Interface |
| /database | Database Browser |
| /dashboard | Analytics Dashboard |
| /simulator | Risk Simulator |
| /upload | Smart Data Import |
| /wiki | Documentation |
| /about | Architecture |

---

# 🔐 Security Philosophy

AutoDBGuard follows a simple principle:

> AI should help manage databases, not accidentally destroy them.

Every generated query must pass through multiple layers of validation before execution.

---

# 📁 Project Structure

```text
AutoDBGuard/
│
├── app.py
├── database.db
├── requirements.txt
├── start.bat
│
├── static/
│   ├── style.css
│   ├── script.js
│   ├── dashboard.js
│   ├── database.js
│   ├── simulator.js
│   └── upload.js
│
└── templates/
    ├── index.html
    ├── app.html
    ├── database.html
    ├── dashboard.html
    ├── simulator.html
    ├── upload.html
    ├── wiki.html
    ├── about.html
    └── base.html
```

---

# 👨‍💻 Author

### Oussama Lakhtiri

GitHub: https://github.com/mrvoidx

---

# ⭐ Support

If you find this project useful:

⭐ Star the repository

🍴 Fork it

🛠️ Contribute improvements

📢 Share it with others

---

## License

MIT License
