/**
 * AutoDBGuard – App Page Script
 */

let lastResults      = null;
let lastRevisedSql   = null;
let pendingForceSql  = null;
let pendingForceNl   = null;

// ── Init ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadHistory();
  const ta = document.getElementById('queryInput');
  if (ta) ta.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') runQuery();
  });
});

// ── Main Runner ────────────────────────────────────────────────
async function runQuery() {
  const input = document.getElementById('queryInput').value.trim();
  if (!input) { showError('Please enter a query before running.'); return; }

  hideError();
  hide('resultsSection');
  hide('queryResultsCard');
  show('loadingIndicator');
  document.getElementById('runBtn').disabled = true;
  lastResults = null; lastRevisedSql = null; pendingForceSql = null; pendingForceNl = null;

  try {
    const res  = await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: input }),
    });
    const data = await res.json();
    hide('loadingIndicator');
    document.getElementById('runBtn').disabled = false;

    if (data.error) { showError(data.error); return; }

    renderResults(data, input);
    show('resultsSection');
    loadHistory();
  } catch (err) {
    hide('loadingIndicator');
    document.getElementById('runBtn').disabled = false;
    showError('Network error: ' + err.message);
  }
}

// ── Render All ─────────────────────────────────────────────────
function renderResults(data, nl) {
  renderExplanation(data.explanation);
  renderSql(data.original_sql, data.policy);
  renderStructure(data.structure);
  renderPlan(data.plan);
  renderRisk(data.risk);
  renderDecision(data.policy, data.original_sql, nl);

  if (data.results && !data.results.error) {
    lastResults = data.results;
    renderQueryResults(data.results);
    show('queryResultsCard');
  }
}

// ── Explanation ────────────────────────────────────────────────
function renderExplanation(text) {
  document.getElementById('explanationText').textContent = text || 'No explanation available.';
}

// ── SQL Display ────────────────────────────────────────────────
function renderSql(originalSql, policy) {
  const container = document.getElementById('sqlDisplay');
  const isSideBySide = policy?.action === 'REVISED' && policy.safe_sql && policy.safe_sql !== originalSql;

  if (isSideBySide) {
    lastRevisedSql = policy.safe_sql;
    container.innerHTML = `
      <div class="sql-side-by-side">
        <div class="sql-pane">
          <div class="sql-pane-label sql-pane-original">Original (unmodified)</div>
          <pre class="code-block code-block-warning">${escHtml(originalSql)}</pre>
        </div>
        <div class="sql-pane">
          <div class="sql-pane-label sql-pane-safe">Revised (safer version)</div>
          <pre class="code-block code-block-safe">${escHtml(policy.safe_sql)}</pre>
        </div>
      </div>`;
  } else {
    container.innerHTML = `<pre class="code-block">${escHtml(originalSql || '')}</pre>`;
  }
}

// ── Structural Analysis ────────────────────────────────────────
function renderStructure(s) {
  const yesNo = v => v
    ? '<span class="analysis-value val-yes">Yes</span>'
    : '<span class="analysis-value val-no">No</span>';

  let html = `<div class="analysis-grid">
    <div class="analysis-item"><div class="analysis-label">Statement Type</div><div class="analysis-value">${escHtml(s.statement_type)}</div></div>
    <div class="analysis-item"><div class="analysis-label">Has WHERE</div>${yesNo(s.has_where)}</div>
    <div class="analysis-item"><div class="analysis-label">Has LIMIT</div>${yesNo(s.has_limit)}</div>
    <div class="analysis-item"><div class="analysis-label">DROP Found</div>${yesNo(s.has_drop)}</div>
    <div class="analysis-item"><div class="analysis-label">ALTER Found</div>${yesNo(s.has_alter)}</div>
  </div>`;

  if (s.issues?.length > 0) {
    html += '<div class="issues-list">' +
      s.issues.map(i => `<div class="issue-item">&#9888; ${escHtml(i)}</div>`).join('') +
      '</div>';
  }
  document.getElementById('structuralAnalysis').innerHTML = html;
}

// ── Execution Plan ─────────────────────────────────────────────
function renderPlan(plan) {
  const el = document.getElementById('executionPlan');
  if (plan.error) { el.innerHTML = `<span style="color:var(--text-muted);font-size:.85rem;">${escHtml(plan.error)}</span>`; return; }
  let html = plan.plan?.length > 0
    ? plan.plan.map(l => `<div class="plan-line">${escHtml(l)}</div>`).join('')
    : '<span style="color:var(--text-muted);font-size:.85rem;">No execution plan available for this statement type.</span>';
  if (plan.full_scan) html += '<div><span class="scan-warning">&#9888; Full table scan detected</span></div>';
  el.innerHTML = html;
}

// ── Risk Assessment ────────────────────────────────────────────
function renderRisk(risk) {
  const cls = `level-${risk.level}`;
  let html = `<div class="risk-score-display">
    <div class="risk-score-num ${cls}">${risk.score}</div>
    <div class="risk-level-badge ${cls}">${escHtml(risk.level)}</div>
  </div><div class="risk-breakdown">`;
  if (risk.breakdown?.length > 0) {
    html += risk.breakdown.map(b => `<div class="breakdown-item">${escHtml(b)}</div>`).join('');
  } else {
    html += '<div class="breakdown-item" style="color:var(--green)">No risk factors detected.</div>';
  }
  html += '</div>';
  document.getElementById('riskAssessment').innerHTML = html;
}

// ── Decision Panel ─────────────────────────────────────────────
function renderDecision(policy, originalSql, nl) {
  const icons   = { EXECUTE:'&#9989;', BLOCKED:'&#128683;', REVISED:'&#9999;', WARNING:'&#9888;' };
  const icon    = icons[policy.action] || '&#8505;';

  let html = `
    <div class="decision-box decision-${policy.action}">
      <div style="font-size:1.6rem;line-height:1;">${icon}</div>
      <div>
        <div class="decision-label">${escHtml(policy.action)}</div>
        <div class="decision-msg">${escHtml(policy.message)}</div>
      </div>
    </div>`;

  if (policy.action === 'REVISED' && policy.safe_sql) {
    html += `
      <div class="execute-revised-bar">
        <span style="color:var(--text-muted);font-size:.87rem;">The revised query is safe to run.</span>
        <button class="btn btn-execute-revised" onclick="executeRevised()">
          &#9654; Execute Revised Query
        </button>
      </div>`;
  }

  if (policy.action === 'BLOCKED') {
    pendingForceSql = originalSql;
    pendingForceNl  = nl;
    html += `
      <div class="override-bar">
        <span style="color:var(--text-muted);font-size:.87rem;">
          &#128737; Query blocked by safety policy.
        </span>
        <button class="btn btn-override" onclick="openApprovalModal()">
          &#9888; Request Override
        </button>
      </div>`;
  }

  document.getElementById('decisionPanel').innerHTML = html;
}

// ── Execute Revised ────────────────────────────────────────────
async function executeRevised() {
  if (!lastRevisedSql) return;
  const btn = document.querySelector('.btn-execute-revised');
  if (btn) { btn.disabled = true; btn.textContent = 'Executing…'; }
  try {
    const res  = await fetch('/api/execute_revised', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sql: lastRevisedSql }),
    });
    const data = await res.json();
    if (data.error) { showError('Execution error: ' + data.error); }
    else {
      lastResults = data;
      renderQueryResults(data);
      show('queryResultsCard');
      const bar = document.querySelector('.execute-revised-bar');
      if (bar) bar.innerHTML = '<span style="color:var(--green);font-size:.87rem;">&#9989; Revised query executed successfully.</span>';
    }
  } catch (err) {
    showError('Request failed: ' + err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ── Approval Modal ─────────────────────────────────────────────
function openApprovalModal() {
  if (!pendingForceSql) return;
  // Populate the modal
  const reasonEl = document.getElementById('approvalReason');
  const sqlEl    = document.getElementById('approvalSql');
  const decision = document.querySelector('.decision-box .decision-msg');
  reasonEl.innerHTML = `<div class="approval-reason-text">${escHtml(decision?.textContent || 'Safety policy violation.')}</div>`;
  sqlEl.textContent  = pendingForceSql;
  // Reset password field and error
  const pwInput = document.getElementById('overridePassword');
  const pwError = document.getElementById('overridePasswordError');
  if (pwInput) { pwInput.value = ''; pwInput.classList.remove('approval-password-input--error'); }
  if (pwError) pwError.classList.add('hidden');
  showModal('approvalModal');
  setTimeout(() => pwInput && pwInput.focus(), 120);
}

function closeApprovalModal() { hideModal('approvalModal'); }

function closeApprovalOutside(e) {
  if (e.target.id === 'approvalModal') closeApprovalModal();
}

async function confirmOverride() {
  if (!pendingForceSql) return;

  // Password check
  const OVERRIDE_PASSWORD = 'test1234';
  const pwInput = document.getElementById('overridePassword');
  const pwError = document.getElementById('overridePasswordError');
  if (!pwInput || pwInput.value !== OVERRIDE_PASSWORD) {
    pwInput.classList.add('approval-password-input--error');
    pwError.classList.remove('hidden');
    pwInput.focus();
    // Shake the input
    pwInput.animate([
      { transform: 'translateX(-6px)' }, { transform: 'translateX(6px)' },
      { transform: 'translateX(-4px)' }, { transform: 'translateX(4px)' },
      { transform: 'translateX(0)' }
    ], { duration: 300, easing: 'ease-out' });
    return;
  }
  pwError.classList.add('hidden');
  pwInput.classList.remove('approval-password-input--error');

  const btn = document.getElementById('overrideConfirmBtn');
  btn.disabled = true; btn.textContent = 'Executing…';

  try {
    const res  = await fetch('/api/force_execute', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sql:            pendingForceSql,
        nl:             pendingForceNl || '[Force executed]',
        override_token: 'OVERRIDE_CONFIRMED',
      }),
    });
    const data = await res.json();
    closeApprovalModal();

    if (data.error) {
      showError('Force execution error: ' + data.error);
    } else {
      lastResults = data;
      renderQueryResults(data, true);
      show('queryResultsCard');
      // Update decision panel to show forced status
      const panel = document.getElementById('decisionPanel');
      const overrideBar = panel.querySelector('.override-bar');
      if (overrideBar) {
        overrideBar.innerHTML = '<span style="color:var(--red);font-size:.87rem;">&#9889; Override executed — this action was logged as FORCED / CRITICAL.</span>';
      }
      loadHistory();
    }
  } catch (err) {
    showError('Request failed: ' + err.message);
    closeApprovalModal();
  } finally {
    btn.disabled = false; btn.textContent = '⚡ Override & Execute';
  }
}

// ── Query Results ──────────────────────────────────────────────
function renderQueryResults(results, forced = false) {
  const el = document.getElementById('queryResults');
  el.innerHTML = '';

  if (forced) {
    el.innerHTML += `<div class="force-exec-banner">&#9889; FORCED EXECUTION — this query bypassed all safety policies and was executed directly.</div>`;
  }
  if (results.auto_fixed) {
    el.innerHTML += `<div class="auto-fix-notice">&#128295; SQL was automatically fixed by the AI and re-executed successfully.</div>`;
  }
  if (!results.columns?.length) {
    el.innerHTML += '<span style="color:var(--text-muted);font-size:.88rem;">Query returned no results.</span>'; return;
  }

  let html = '<div class="results-table-wrap"><table class="results-table"><thead><tr>';
  results.columns.forEach(c => { html += `<th>${escHtml(c)}</th>`; });
  html += '</tr></thead><tbody>';
  results.rows.forEach(row => {
    html += '<tr>' + row.map(cell => `<td>${escHtml(String(cell ?? ''))}</td>`).join('') + '</tr>';
  });
  html += `</tbody></table></div>`;
  html += `<div style="margin-top:.5rem;font-size:.78rem;color:var(--text-muted);">${results.rows.length} row(s) returned</div>`;
  el.innerHTML += html;
}

// ── Export CSV ─────────────────────────────────────────────────
function exportCSV() {
  if (!lastResults?.columns) return;
  const rows = [lastResults.columns, ...lastResults.rows];
  const csv  = rows.map(r => r.map(v => `"${String(v).replace(/"/g,'""')}"`).join(',')).join('\n');
  const a    = Object.assign(document.createElement('a'), {
    href:     URL.createObjectURL(new Blob([csv], { type:'text/csv' })),
    download: 'autodbguard_results.csv',
  });
  a.click();
}

// ── Query History ──────────────────────────────────────────────
async function loadHistory() {
  try {
    const res  = await fetch('/api/history?limit=15');
    const data = await res.json();
    if (!data.error) renderHistory(data.history);
  } catch (_) {}
}

function renderHistory(history) {
  const el = document.getElementById('historyList');
  if (!history?.length) {
    el.innerHTML = '<div class="history-empty">No queries yet.</div>'; return;
  }
  el.innerHTML = history.map(h => `
    <div class="history-item" onclick="reuseQuery('${escJs(h.natural_language)}')">
      <div class="history-item-top">
        <span class="history-badge level-${h.risk_level}">${h.risk_level}</span>
        <span class="history-action action-${h.action}">${h.action}</span>
      </div>
      <div class="history-nl">${escHtml(h.natural_language)}</div>
      <div class="history-meta">${h.row_count} rows &bull; ${h.created_at}</div>
    </div>
  `).join('');
}

function reuseQuery(nl) {
  document.getElementById('queryInput').value = nl;
  document.getElementById('queryInput').focus();
}

// ── Modal Helpers ──────────────────────────────────────────────
function showModal(id) {
  const el = document.getElementById(id);
  el.classList.remove('hidden');
  requestAnimationFrame(() => el.classList.add('modal-visible'));
}
function hideModal(id) {
  const el = document.getElementById(id);
  el.classList.remove('modal-visible');
  setTimeout(() => el.classList.add('hidden'), 180);
}

// ── Utility ───────────────────────────────────────────────────
function show(id) { document.getElementById(id)?.classList.remove('hidden'); }
function hide(id) { document.getElementById(id)?.classList.add('hidden'); }
function showError(msg) { const el = document.getElementById('errorBanner'); el.textContent = msg; el.classList.remove('hidden'); }
function hideError() { document.getElementById('errorBanner').classList.add('hidden'); }
function clearAll() {
  document.getElementById('queryInput').value = '';
  hideError(); hide('loadingIndicator'); hide('resultsSection'); hide('queryResultsCard');
  lastResults = null; lastRevisedSql = null; pendingForceSql = null; pendingForceNl = null;
}
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function escJs(s) {
  return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'").replace(/"/g,'\\"');
}
