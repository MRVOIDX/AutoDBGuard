/**
 * AutoDBGuard – Database Manager (multi-table)
 */

// ── State ──────────────────────────────────────────────────────
let allRows      = [];
let allColumns   = [];
let currentTable = 'users';
let sortKey      = 'id';
let sortDir      = 'asc';
let deleteTarget = null;
let editTarget   = null;

// Table metadata
const TABLE_META = {
  users: {
    label: 'Users', icon: '👤', editable: true,
    badge: 'users',
    searchPlaceholder: 'Search name, email, city…',
  },
  products: {
    label: 'Products', icon: '📦', editable: false,
    badge: 'products',
    searchPlaceholder: 'Search name or category…',
  },
  orders: {
    label: 'Orders', icon: '🛒', editable: false,
    badge: 'orders',
    searchPlaceholder: 'Search user, product, status…',
  },
  query_history: {
    label: 'Query History', icon: '📜', editable: false,
    badge: 'query_history',
    searchPlaceholder: 'Search queries…',
  },
};

// ── Init ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadUserTables().then(() => {
    switchTable('users');
    loadTabCounts();
  });

  ['newName','newEmail'].forEach(id =>
    document.getElementById(id)?.addEventListener('keydown', e => { if(e.key==='Enter') submitAdd(); })
  );
  ['editName','editEmail'].forEach(id =>
    document.getElementById(id)?.addEventListener('keydown', e => { if(e.key==='Enter') submitEdit(); })
  );
});

// ── Table Switching ────────────────────────────────────────────
function switchTable(name) {
  currentTable = name;
  sortKey = 'id'; sortDir = 'asc';
  document.getElementById('searchInput').value = '';

  // Update active tab
  document.querySelectorAll('.db-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + name)?.classList.add('active');

  // Update badge & search placeholder
  const meta = TABLE_META[name] || { label: name, editable: false, searchPlaceholder: 'Search…', userUploaded: false };
  document.getElementById('tableBadge').textContent       = name;
  document.getElementById('searchInput').placeholder      = meta.searchPlaceholder;

  // Show/hide Add button and readonly pill
  document.getElementById('addBtn').style.display         = meta.editable ? '' : 'none';
  document.getElementById('readonlyPill').classList.toggle('hidden', meta.editable);

  loadCurrentTable();
}

async function loadCurrentTable() {
  showTableLoading(true);
  hideDroppedState();
  const endpoint = `/api/db/table/${currentTable}`;
  try {
    const res  = await fetch(endpoint);
    const data = await res.json();
    if (data.error) {
      showTableLoading(false);
      if (data.error.toLowerCase().includes('no such table')) {
        showDroppedState(currentTable);
        logEntry('error', `Table "${currentTable}" has been dropped — no data available.`);
      } else {
        logEntry('error', data.error);
      }
      return;
    }

    allRows    = data.rows;
    allColumns = data.columns;

    renderStats(data.stats);
    renderSchema(data.create_sql, data.schema);
    renderTableHead();
    renderTable();

    logEntry('info', `Loaded ${data.stats.total_rows} rows from "${currentTable}"`);
  } catch (err) {
    logEntry('error', 'Load failed: ' + err.message);
  } finally {
    showTableLoading(false);
  }
}

function showDroppedState(tableName) {
  allRows    = [];
  allColumns = [];
  document.getElementById('droppedTableName').textContent = tableName;
  document.getElementById('droppedState').classList.remove('hidden');
  document.getElementById('dbTable').style.display = 'none';
  document.getElementById('emptyState').classList.add('hidden');
  document.getElementById('tableHead').innerHTML   = '';
  document.getElementById('dbTableBody').innerHTML = '';
  document.getElementById('visibleCount').textContent = '0 rows';
  setText('statRows', '—');
  document.getElementById('schemaSql').textContent = '-- Table does not exist';
  document.getElementById('columnsList').innerHTML = '<div style="color:var(--red);font-size:.85rem;padding:.5rem 0;">No schema available</div>';
}

function hideDroppedState() {
  document.getElementById('droppedState').classList.add('hidden');
}

async function restoreDatabase() {
  const btn = document.getElementById('restoreBtn');
  btn.disabled    = true;
  btn.textContent = 'Restoring…';
  try {
    const res  = await fetch('/api/db/restore', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      logEntry('info', 'All tables restored and reseeded successfully.');
      hideDroppedState();
      // Refresh counts on every built-in tab
      await loadTabCounts();
      // Reload whichever table the user is currently viewing;
      // if it was a dropped table, switch to users as a safe default.
      const safeTable = TABLE_META[currentTable] && !TABLE_META[currentTable].userUploaded
        ? currentTable
        : 'users';
      switchTable(safeTable);
    } else {
      logEntry('error', data.error || 'Restore failed.');
      btn.disabled    = false;
      btn.textContent = '↺ Restore All Tables';
    }
  } catch (err) {
    logEntry('error', 'Restore failed: ' + err.message);
    btn.disabled    = false;
    btn.textContent = '↺ Restore All Tables';
  }
}

// Keep the old loadSnapshot for legacy calls
function loadSnapshot() { loadCurrentTable(); }

// ── User-Uploaded Tables ───────────────────────────────────────
async function loadUserTables() {
  try {
    const res  = await fetch('/api/db/tables');
    const data = await res.json();
    if (data.error || !data.user_tables?.length) return;

    const separator = document.getElementById('tabSeparator');
    separator.classList.remove('hidden');

    const importLink = document.querySelector('.db-tab-import');

    data.user_tables.forEach(t => {
      if (document.getElementById('tab-' + t.table_name)) return;

      TABLE_META[t.table_name] = {
        label:             t.display_name,
        icon:              '📋',
        editable:          false,
        badge:             t.table_name,
        searchPlaceholder: `Search ${t.display_name}…`,
        userUploaded:      true,
        sourceFile:        t.source_file,
      };

      const btn = document.createElement('button');
      btn.className   = 'db-tab db-tab-user';
      btn.id          = 'tab-' + t.table_name;
      btn.title       = `Source: ${t.source_file}`;
      btn.innerHTML   = `
        <span class="db-tab-icon">&#128196;</span>
        <span class="db-tab-user-label">${escHtml(t.display_name)}</span>
        <span class="db-tab-count" id="count-${t.table_name}">${t.row_count}</span>
        <span class="db-tab-drop" onclick="dropUserTable('${escJs(t.table_name)}',event)" title="Drop table">&#10005;</span>
      `;
      btn.addEventListener('click', (e) => {
        if (!e.target.classList.contains('db-tab-drop')) switchTable(t.table_name);
      });

      document.getElementById('tabBar').insertBefore(btn, importLink);
    });
  } catch (err) {
    console.warn('loadUserTables error:', err);
  }
}

async function dropUserTable(tableName, e) {
  e.stopPropagation();
  if (!confirm(`Drop the "${tableName}" table? All imported data will be lost.`)) return;

  try {
    const res  = await fetch(`/api/db/drop_uploaded/${tableName}`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      document.getElementById('tab-' + tableName)?.remove();
      delete TABLE_META[tableName];
      if (currentTable === tableName) switchTable('users');
      const hasUser = document.querySelectorAll('.db-tab-user').length > 0;
      document.getElementById('tabSeparator').classList.toggle('hidden', !hasUser);
      logEntry('info', `Table "${tableName}" dropped.`);
    } else {
      logEntry('error', data.error || 'Drop failed.');
    }
  } catch (err) {
    logEntry('error', 'Drop failed: ' + err.message);
  }
}

async function loadTabCounts() {
  for (const t of Object.keys(TABLE_META)) {
    try {
      const res  = await fetch(`/api/db/table/${t}`);
      const data = await res.json();
      if (!data.error) {
        const el = document.getElementById('count-' + t);
        if (el) el.textContent = data.stats.total_rows;
      }
    } catch(_) {}
  }
}

// ── Stats ──────────────────────────────────────────────────────
function renderStats(stats) {
  setText('statRows',    stats.total_rows);
  setText('statSize',    formatBytes(stats.db_size_bytes));
  setText('statTables',  stats.table_count);
  setText('statUpdated', formatTime(new Date()));
}

// ── Schema ─────────────────────────────────────────────────────
function renderSchema(createSql, schema) {
  document.getElementById('schemaSql').textContent = formatSql(createSql || '');
  document.getElementById('columnsList').innerHTML = schema.map(col => `
    <div class="db-col-row">
      <span class="db-col-name">${escHtml(col.name)}</span>
      <span class="db-col-type">${escHtml(col.type)}</span>
      <div class="db-col-flags">
        ${col.pk      ? '<span class="db-flag db-flag-pk">PK</span>'       : ''}
        ${col.notnull ? '<span class="db-flag db-flag-nn">NOT NULL</span>' : ''}
      </div>
    </div>
  `).join('');
}

// ── Table Head ─────────────────────────────────────────────────
function renderTableHead() {
  const tr  = document.getElementById('tableHead');
  const editable = TABLE_META[currentTable]?.editable;

  tr.innerHTML = allColumns.map(col => `
    <th class="${col==='id'?'col-id':''}" onclick="sortTable('${col}')">
      ${escHtml(col)}
      <span class="sort-icon" id="sort-${col}">⇅</span>
    </th>
  `).join('') + (editable ? '<th class="col-actions">actions</th>' : '');
}

// ── Table Body ─────────────────────────────────────────────────
function renderTable() {
  const query = (document.getElementById('searchInput').value || '').toLowerCase();

  // Sort
  const colIdx = allColumns.indexOf(sortKey);
  const sorted = [...allRows].sort((a, b) => {
    const av = String(a[colIdx] ?? '').toLowerCase();
    const bv = String(b[colIdx] ?? '').toLowerCase();
    const cmp = sortKey === 'id' || sortKey === 'price' || sortKey === 'stock'
      ? Number(a[colIdx]) - Number(b[colIdx])
      : av.localeCompare(bv);
    return sortDir === 'asc' ? cmp : -cmp;
  });

  // Filter
  const filtered = query
    ? sorted.filter(r => r.some(c => String(c ?? '').toLowerCase().includes(query)))
    : sorted;

  // Count label
  document.getElementById('visibleCount').textContent =
    query ? `${filtered.length} of ${allRows.length} rows` : `${allRows.length} rows`;

  const tbody  = document.getElementById('dbTableBody');
  const table  = document.getElementById('dbTable');
  const empty  = document.getElementById('emptyState');

  if (filtered.length === 0) {
    table.style.display = 'none';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');
  table.style.display = '';

  const editable = TABLE_META[currentTable]?.editable;
  tbody.innerHTML = filtered.map(row => renderRow(row, editable)).join('');

  // Update sort icons
  allColumns.forEach(col => {
    const el = document.getElementById('sort-' + col);
    if (!el) return;
    el.textContent = col === sortKey ? (sortDir === 'asc' ? '↑' : '↓') : '⇅';
  });
}

function renderRow(row, editable) {
  const cells = row.map((cell, i) => {
    const col = allColumns[i];
    return `<td>${renderCell(col, cell, currentTable)}</td>`;
  }).join('');

  const id = row[0];
  const actions = editable
    ? `<td class="col-actions">
        <button class="db-action-btn db-edit-btn"   onclick="openEditModal(${id},'${escJs(row[1])}','${escJs(row[2])}')" title="Edit">&#9998; Edit</button>
        <button class="db-action-btn db-delete-btn" onclick="openDeleteModal(${id},'${escJs(row[1])}')" title="Delete">&#128465;</button>
       </td>`
    : '';

  return `<tr class="db-row" data-id="${id}">${cells}${actions}</tr>`;
}

function renderCell(col, val, table) {
  if (val === null || val === undefined) return '<span style="color:var(--text-muted);font-style:italic;">null</span>';

  // Users: name column → avatar + name
  if (table === 'users' && col === 'name') {
    const initials = String(val).split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase();
    const hue = Math.abs(hashCode(String(val))) % 360;
    return `<div class="db-name-cell">
      <div class="db-avatar" style="background:hsl(${hue},55%,30%);color:hsl(${hue},70%,80%);">${initials}</div>
      <span>${escHtml(val)}</span>
    </div>`;
  }

  // Email
  if (col === 'email') return `<span class="db-email">${escHtml(val)}</span>`;

  // ID badge
  if (col === 'id') return `<span class="db-id-badge">#${val}</span>`;

  // Orders: status badge
  if (col === 'status') {
    const cls = { completed:'status-completed', shipped:'status-shipped', pending:'status-pending', cancelled:'status-cancelled' }[val] || '';
    return `<span class="db-status-badge ${cls}">${escHtml(val)}</span>`;
  }

  // Products: category badge
  if (col === 'category') {
    return `<span class="db-cat-badge">${escHtml(val)}</span>`;
  }

  // Price
  if (col === 'price' || col === 'total_price') {
    return `<span style="font-family:var(--font-mono);color:var(--green);">$${Number(val).toFixed(2)}</span>`;
  }

  // History: risk_level badge
  if (col === 'risk_level') {
    return `<span class="risk-level-badge level-${val}" style="font-size:.68rem;padding:.15rem .55rem;">${escHtml(val)}</span>`;
  }

  // History: action badge
  if (col === 'action') {
    return `<span class="action-badge action-${val}">${escHtml(val)}</span>`;
  }

  // History: risk_score
  if (col === 'risk_score') {
    const color = val >= 100 ? 'var(--red)' : val >= 50 ? 'var(--orange)' : val >= 20 ? 'var(--yellow)' : 'var(--green)';
    return `<span style="font-family:var(--font-mono);font-weight:700;color:${color};">${val}</span>`;
  }

  // Stock with low-stock indicator
  if (col === 'stock') {
    const color = val < 30 ? 'var(--red)' : val < 60 ? 'var(--yellow)' : 'var(--green)';
    return `<span style="font-family:var(--font-mono);color:${color};">${val}${val < 30 ? ' ⚠' : ''}</span>`;
  }

  // Natural language query: truncate
  if (col === 'natural_language' || col === 'original_sql') {
    const s = String(val);
    return `<span title="${escHtml(s)}" style="display:block;max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escHtml(s)}</span>`;
  }

  return escHtml(String(val));
}

// ── Search / Sort ──────────────────────────────────────────────
function filterTable() { renderTable(); }

function sortTable(key) {
  sortKey === key ? (sortDir = sortDir==='asc'?'desc':'asc') : (sortKey = key, sortDir = 'asc');
  renderTable();
}

// ── Add User ───────────────────────────────────────────────────
function openAddModal() {
  document.getElementById('newName').value  = '';
  document.getElementById('newEmail').value = '';
  hideModalError('addError');
  showModal('addModal');
  setTimeout(() => document.getElementById('newName').focus(), 150);
}
function closeAddModal() { hideModal('addModal'); }

async function submitAdd() {
  const name  = document.getElementById('newName').value.trim();
  const email = document.getElementById('newEmail').value.trim();
  if (!name || !email) { showModalError('addError', 'Please fill in both fields.'); return; }

  const btn = document.getElementById('addSubmitBtn');
  btn.disabled = true; btn.textContent = 'Adding…';

  try {
    const res  = await fetch('/api/db/users', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ name, email }),
    });
    const data = await res.json();
    if (data.error) { showModalError('addError', data.error); return; }

    allRows.push([data.id, data.name, data.email]);
    renderTable();
    updateStatRow(allRows.length);
    closeAddModal();
    flashRow(data.id, 'added');
    logEntry('add', `Added user #${data.id}: ${data.name}`);
    loadTabCounts();
  } catch (err) {
    showModalError('addError', 'Request failed: ' + err.message);
  } finally {
    btn.disabled = false; btn.textContent = 'Add User';
  }
}

// ── Edit User ──────────────────────────────────────────────────
function openEditModal(id, name, email) {
  editTarget = id;
  document.getElementById('editUserId').textContent = '#' + id;
  document.getElementById('editName').value  = name;
  document.getElementById('editEmail').value = email;
  hideModalError('editError');
  showModal('editModal');
  setTimeout(() => document.getElementById('editName').focus(), 150);
}
function closeEditModal() { hideModal('editModal'); editTarget = null; }

async function submitEdit() {
  if (!editTarget) return;
  const name  = document.getElementById('editName').value.trim();
  const email = document.getElementById('editEmail').value.trim();
  if (!name || !email) { showModalError('editError', 'Please fill in both fields.'); return; }

  const btn = document.getElementById('editBtn');
  btn.disabled = true; btn.textContent = 'Saving…';

  try {
    const res  = await fetch(`/api/db/users/${editTarget}`, {
      method: 'PUT', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ name, email }),
    });
    const data = await res.json();
    if (data.error) { showModalError('editError', data.error); return; }

    const idx = allRows.findIndex(r => r[0] === editTarget);
    if (idx !== -1) allRows[idx][1] = data.name, allRows[idx][2] = data.email;
    renderTable();
    closeEditModal();
    flashRow(editTarget, 'edited');
    logEntry('edit', `Edited user #${editTarget}: ${data.name}`);
  } catch (err) {
    showModalError('editError', 'Request failed: ' + err.message);
  } finally {
    btn.disabled = false; btn.textContent = 'Save Changes';
  }
}

// ── Delete User ────────────────────────────────────────────────
function openDeleteModal(id, name) {
  deleteTarget = id;
  document.getElementById('deleteUserName').textContent = `${name} (#${id})`;
  showModal('deleteModal');
}
function closeDeleteModal() { hideModal('deleteModal'); deleteTarget = null; }

async function confirmDelete() {
  if (!deleteTarget) return;
  const btn = document.getElementById('deleteConfirmBtn');
  btn.disabled = true; btn.textContent = 'Deleting…';

  try {
    const res  = await fetch(`/api/db/users/${deleteTarget}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.error) { logEntry('error', data.error); closeDeleteModal(); return; }

    const row = allRows.find(r => r[0] === data.deleted_id);
    const name = row ? row[1] : '#' + data.deleted_id;
    allRows = allRows.filter(r => r[0] !== data.deleted_id);
    renderTable();
    updateStatRow(allRows.length);
    closeDeleteModal();
    logEntry('delete', `Deleted user #${data.deleted_id}: ${name}`);
    loadTabCounts();
  } catch (err) {
    logEntry('error', 'Delete failed: ' + err.message);
    closeDeleteModal();
  } finally {
    btn.disabled = false; btn.textContent = '🗑 Delete';
  }
}

// ── Activity Log ───────────────────────────────────────────────
function logEntry(type, message) {
  const log   = document.getElementById('activityLog');
  const entry = document.createElement('div');
  entry.className = `db-log-entry db-log-${type}`;
  entry.innerHTML = `<span class="log-time">${formatTime(new Date())}</span> ${escHtml(message)}`;
  log.insertBefore(entry, log.firstChild);
  while (log.children.length > 25) log.removeChild(log.lastChild);
}
function clearLog() {
  document.getElementById('activityLog').innerHTML = '<div class="db-log-entry db-log-info">Log cleared</div>';
}

// ── UI Helpers ─────────────────────────────────────────────────
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
function closeModalOutside(e, id, fn) { if (e.target.id === id) fn(); }
function showModalError(id, msg) { const el = document.getElementById(id); el.textContent = msg; el.classList.remove('hidden'); }
function hideModalError(id)      { document.getElementById(id).classList.add('hidden'); }

function showTableLoading(show) {
  document.getElementById('tableLoading').style.display = show ? 'flex' : 'none';
  document.getElementById('dbTable').style.display      = show ? 'none'  : '';
}
function flashRow(id, type) {
  setTimeout(() => {
    const row = document.querySelector(`tr[data-id="${id}"]`);
    if (!row) return;
    row.classList.add('row-flash-' + type);
    setTimeout(() => row.classList.remove('row-flash-' + type), 1500);
  }, 50);
}
function updateStatRow(count) { setText('statRows', count); }
function setText(id, val) { const el = document.getElementById(id); if(el) el.textContent = val; }

// ── Formatting ─────────────────────────────────────────────────
function formatBytes(b) {
  if (!b) return '0 B';
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b/1024).toFixed(1) + ' KB';
  return (b/1048576).toFixed(2) + ' MB';
}
function formatTime(d) {
  return d.toLocaleTimeString('en-US', { hour:'2-digit', minute:'2-digit', second:'2-digit' });
}
function formatSql(sql) {
  return sql.replace(/\(\s*/, '(\n  ').replace(/,\s*/g, ',\n  ').replace(/\s*\)\s*$/, '\n)').trim();
}
function hashCode(str) {
  let h = 0;
  for (let i=0;i<str.length;i++) h = Math.imul(31,h)+str.charCodeAt(i)|0;
  return h;
}
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function escJs(s) {
  return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'").replace(/"/g,'\\"');
}
