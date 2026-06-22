/**
 * AutoDBGuard – Dashboard JS
 */

const RISK_COLORS   = { LOW:'#3fb950', MEDIUM:'#d29922', HIGH:'#e3702a', CRITICAL:'#f85149' };
const ACTION_COLORS = { EXECUTE:'#3fb950', REVISED:'#d29922', BLOCKED:'#f85149', WARNING:'#e3702a' };

document.addEventListener('DOMContentLoaded', loadStats);

async function loadStats() {
  try {
    const res  = await fetch('/api/stats');
    const data = await res.json();
    if (data.error) { console.error(data.error); return; }

    renderTopStats(data.queries, data.db);
    renderBarChart('riskChart',       data.queries.risk_dist,   RISK_COLORS,   'queries');
    renderBarChart('actionChart',     data.queries.action_dist, ACTION_COLORS, 'queries');
    renderBarChart('orderStatusChart',data.db.order_status,     {completed:'#3fb950',shipped:'#58a6ff',pending:'#d29922',cancelled:'#f85149'}, 'orders');
    renderBarChart('productCatChart', data.db.product_cats,     {Electronics:'#58a6ff',Sports:'#3fb950',Books:'#d29922',Clothing:'#e3702a','Home':'#a371f7'}, 'products');
    renderDbTableStats(data.db);
    renderRecentHistory(data.queries.recent);
  } catch (err) {
    console.error('Dashboard load error:', err);
  }
}

function renderTopStats(q, db) {
  setText('dTotalQueries', q.total);
  setText('dExecuted',     q.action_dist['EXECUTE'] || 0);
  setText('dBlocked',      q.action_dist['BLOCKED'] || 0);
  setText('dAvgScore',     q.avg_score);
  setText('dRevenue',      '$' + db.total_revenue.toLocaleString('en-US', {minimumFractionDigits:2}));
}

function renderBarChart(containerId, data, colorMap, unit) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!data || Object.keys(data).length === 0) {
    el.innerHTML = '<div class="chart-empty">No data yet — run some queries first.</div>';
    return;
  }
  const total = Object.values(data).reduce((a,b) => a+b, 0);
  el.innerHTML = Object.entries(data)
    .sort((a,b) => b[1]-a[1])
    .map(([key, val]) => {
      const pct   = total > 0 ? Math.round(val / total * 100) : 0;
      const color = colorMap[key] || '#8b949e';
      return `
        <div class="chart-row">
          <div class="chart-label">${escHtml(key)}</div>
          <div class="chart-bar-wrap">
            <div class="chart-bar" style="width:${pct}%;background:${color};"></div>
          </div>
          <div class="chart-val">${val} <span class="chart-pct">(${pct}%)</span></div>
        </div>
      `;
    }).join('');
}

function renderDbTableStats(db) {
  const el = document.getElementById('dbTableStats');
  const items = [
    { label:'Users',    val: db.users,    icon:'&#128100;', color:'#58a6ff' },
    { label:'Products', val: db.products, icon:'&#128230;', color:'#3fb950' },
    { label:'Orders',   val: db.orders,   icon:'&#128666;', color:'#d29922' },
    { label:'DB Size',  val: formatBytes(db.size_bytes), icon:'&#128190;', color:'#a371f7' },
  ];
  el.innerHTML = items.map(i => `
    <div class="db-tbl-stat">
      <div class="db-tbl-stat-icon" style="color:${i.color};">${i.icon}</div>
      <div>
        <div class="db-tbl-stat-val">${i.val}</div>
        <div class="db-tbl-stat-lbl">${i.label}</div>
      </div>
    </div>
  `).join('');
}

function renderRecentHistory(recent) {
  const tbody = document.getElementById('recentBody');
  if (!recent || recent.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="color:var(--text-muted);text-align:center;padding:2rem;">No queries yet — head to the App page to run some.</td></tr>';
    return;
  }
  tbody.innerHTML = recent.map(r => `
    <tr>
      <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escHtml(r.nl)}</td>
      <td><span class="risk-level-badge level-${r.risk_level}" style="font-size:.7rem;padding:.2rem .7rem;">${r.risk_level}</span></td>
      <td style="font-family:var(--font-mono);">${r.risk_score}</td>
      <td><span class="action-badge action-${r.action}">${r.action}</span></td>
      <td style="color:var(--text-muted);font-size:.8rem;">${r.created_at}</td>
    </tr>
  `).join('');
}

function setText(id, val) { const el = document.getElementById(id); if(el) el.textContent = val; }

function formatBytes(b) {
  if (!b) return '0 B';
  if (b < 1024) return b + ' B';
  if (b < 1024*1024) return (b/1024).toFixed(1) + ' KB';
  return (b/(1024*1024)).toFixed(2) + ' MB';
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
