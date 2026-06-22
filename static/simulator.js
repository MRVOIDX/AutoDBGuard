/**
 * AutoDBGuard – Risk Simulator JS
 * Mirrors the Python risk engine entirely in the browser — no API calls needed.
 */

const ATTACKS = [
  {
    label: "Drop the entire table",
    sql:   "DROP TABLE users;",
    desc:  "Permanently destroys the entire users table and all its data. Irreversible.",
  },
  {
    label: "Delete all users (no WHERE)",
    sql:   "DELETE FROM users;",
    desc:  "Removes every single row in the users table. No WHERE clause = full wipe.",
  },
  {
    label: "Update all emails (no WHERE)",
    sql:   "UPDATE users SET email = 'hacked@evil.com';",
    desc:  "Overwrites every user's email at once. Classic mass-update attack.",
  },
  {
    label: "Schema modification",
    sql:   "ALTER TABLE users ADD COLUMN admin INTEGER DEFAULT 1;",
    desc:  "Adds an 'admin' column to the table — a privilege escalation technique.",
  },
  {
    label: "Unbounded full table dump",
    sql:   "SELECT * FROM users;",
    desc:  "Dumps the entire table with no LIMIT. On large databases this can be catastrophic.",
  },
  {
    label: "Safe filtered query",
    sql:   "SELECT id, name FROM users WHERE city = 'New York' LIMIT 10;",
    desc:  "A well-formed, safe query: specific columns, WHERE clause, and LIMIT. Should score LOW.",
  },
  {
    label: "DROP + inject after comment",
    sql:   "SELECT * FROM users WHERE id = 1; -- DROP TABLE users;",
    desc:  "Comment-based injection attempt. The scanner detects DROP even in comments.",
  },
  {
    label: "Stacked query injection",
    sql:   "SELECT name FROM users WHERE id=1; DELETE FROM users WHERE 1=1;",
    desc:  "Two statements in one — SELECT followed by a mass DELETE.",
  },
];

// ── Init ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  renderAttackList();
  simUpdate(); // render empty state
});

function renderAttackList() {
  const el = document.getElementById('attackList');
  el.innerHTML = ATTACKS.map((a, i) => `
    <div class="attack-item" onclick="loadAttack(${i})">
      <div class="attack-item-label">${escHtml(a.label)}</div>
      <div class="attack-item-desc">${escHtml(a.desc)}</div>
    </div>
  `).join('');
}

function loadAttack(i) {
  document.getElementById('simInput').value = ATTACKS[i].sql;
  simUpdate();
}

function simClear() {
  document.getElementById('simInput').value = '';
  simUpdate();
}

// ── Live Scoring Engine (mirrors Python) ──────────────────────
function simUpdate() {
  const sql = document.getElementById('simInput').value.trim();
  if (!sql) {
    renderScore(0, 'LOW', [], emptyStructure(), null);
    return;
  }
  const structure  = analyzeStructure(sql);
  const risk       = calculateRisk(structure);
  const decision   = enforcePolicy(sql, structure, risk);
  renderScore(risk.score, risk.level, risk.breakdown, structure, decision);
}

function analyzeStructure(sql) {
  const up = sql.toUpperCase();
  const starts = s => up.trimStart().startsWith(s);

  let stmt = 'UNKNOWN';
  for (const s of ['SELECT','INSERT','UPDATE','DELETE','DROP','ALTER','CREATE']) {
    if (starts(s)) { stmt = s; break; }
  }

  return {
    statement_type: stmt,
    has_where: /\bWHERE\b/i.test(sql),
    has_limit: /\bLIMIT\b/i.test(sql),
    has_drop:  /\bDROP\b/i.test(sql),
    has_alter: /\bALTER\b/i.test(sql),
  };
}

function emptyStructure() {
  return { statement_type:'—', has_where:false, has_limit:false, has_drop:false, has_alter:false };
}

function calculateRisk(s) {
  let score = 0;
  const breakdown = [];

  if (s.has_drop || s.has_alter) {
    score += 100; breakdown.push({ label:'+100  DROP or ALTER detected',  color:'var(--red)' });
  }
  if (s.statement_type === 'DELETE' && !s.has_where) {
    score += 80;  breakdown.push({ label:'+80   DELETE without WHERE',     color:'var(--red)' });
  }
  if (s.statement_type === 'UPDATE' && !s.has_where) {
    score += 70;  breakdown.push({ label:'+70   UPDATE without WHERE',     color:'var(--orange)' });
  }
  if (s.statement_type === 'SELECT' && !s.has_limit) {
    score += 30;  breakdown.push({ label:'+30   SELECT without LIMIT',     color:'var(--yellow)' });
  }

  const level = score <= 20 ? 'LOW' : score <= 50 ? 'MEDIUM' : score <= 80 ? 'HIGH' : 'CRITICAL';
  return { score, level, breakdown };
}

function enforcePolicy(sql, structure, risk) {
  if (structure.has_drop || structure.has_alter)
    return { action:'BLOCKED', msg:'DROP and ALTER are permanently blocked.', color:'var(--red)' };
  if (structure.statement_type === 'DELETE' && !structure.has_where)
    return { action:'BLOCKED', msg:'DELETE without WHERE is blocked to prevent full data loss.', color:'var(--red)' };
  if (structure.statement_type === 'UPDATE' && !structure.has_where)
    return { action:'BLOCKED', msg:'UPDATE without WHERE is blocked to prevent mass modification.', color:'var(--red)' };
  if (risk.level === 'HIGH')
    return { action:'REVISED', msg:'Query would be rewritten with safety guardrails (LIMIT added) before execution.', color:'var(--orange)' };
  if (risk.level === 'CRITICAL')
    return { action:'BLOCKED', msg:'CRITICAL risk — query blocked.', color:'var(--red)' };
  return { action:'EXECUTE', msg:`Query is ${risk.level} risk — safe to execute${structure.statement_type === 'SELECT' && !structure.has_limit ? ' (LIMIT 50 auto-appended)' : ''}.`, color:'var(--green)' };
}

// ── Render ─────────────────────────────────────────────────────
const LEVEL_COLORS = { LOW:'#3fb950', MEDIUM:'#d29922', HIGH:'#e3702a', CRITICAL:'#f85149' };

function renderScore(score, level, breakdown, structure, decision) {
  const color = LEVEL_COLORS[level] || '#8b949e';

  // Score number + badge
  const scoreEl = document.getElementById('simScore');
  const levelEl = document.getElementById('simLevel');
  const barEl   = document.getElementById('simScoreBar');

  scoreEl.textContent = score;
  scoreEl.style.color = color;
  levelEl.textContent = level;
  levelEl.className   = 'sim-level-badge level-' + level;

  const pct = Math.min(score, 200) / 200 * 100;
  barEl.style.width      = pct + '%';
  barEl.style.background = color;

  // Breakdown
  const breakdownEl = document.getElementById('simBreakdown');
  if (!breakdown || breakdown.length === 0) {
    breakdownEl.innerHTML = '<div class="sim-factor-none">&#9989; No risk factors detected.</div>';
  } else {
    breakdownEl.innerHTML = breakdown.map(b => `
      <div class="sim-factor" style="border-left:3px solid ${b.color};">
        <span style="font-family:var(--font-mono);font-size:.82rem;color:${b.color};">${escHtml(b.label)}</span>
      </div>
    `).join('');
  }

  // Structure
  const yesNo = v => v
    ? '<span class="analysis-value val-yes">Yes</span>'
    : '<span class="analysis-value val-no">No</span>';

  document.getElementById('simStructure').innerHTML = `
    <div class="analysis-item"><div class="analysis-label">Statement Type</div><div class="analysis-value">${escHtml(structure.statement_type)}</div></div>
    <div class="analysis-item"><div class="analysis-label">Has WHERE</div>${yesNo(structure.has_where)}</div>
    <div class="analysis-item"><div class="analysis-label">Has LIMIT</div>${yesNo(structure.has_limit)}</div>
    <div class="analysis-item"><div class="analysis-label">DROP Found</div>${yesNo(structure.has_drop)}</div>
    <div class="analysis-item"><div class="analysis-label">ALTER Found</div>${yesNo(structure.has_alter)}</div>
  `;

  // Decision
  if (decision) {
    const icons = { EXECUTE:'&#9989;', BLOCKED:'&#128683;', REVISED:'&#9999;' };
    document.getElementById('simDecision').innerHTML = `
      <div class="decision-box decision-${decision.action}">
        <div style="font-size:1.4rem;line-height:1;">${icons[decision.action]||'&#8505;'}</div>
        <div>
          <div class="decision-label">${escHtml(decision.action)}</div>
          <div class="decision-msg">${escHtml(decision.msg)}</div>
        </div>
      </div>
    `;
  } else {
    document.getElementById('simDecision').innerHTML = '<div style="color:var(--text-muted);font-size:.88rem;">Enter a SQL query above to see the decision.</div>';
  }
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
