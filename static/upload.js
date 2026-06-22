/**
 * AutoDBGuard – Data Import (upload.js)
 */

let selectedFile = null;

// ── Drag & Drop ────────────────────────────────────────────────
function onDragOver(e) {
  e.preventDefault();
  document.getElementById('dropZone').classList.add('drag-over');
}
function onDragLeave(e) {
  document.getElementById('dropZone').classList.remove('drag-over');
}
function onDrop(e) {
  e.preventDefault();
  document.getElementById('dropZone').classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) acceptFile(file);
}
function onFileSelected(e) {
  const file = e.target.files[0];
  if (file) acceptFile(file);
}

const SUPPORTED_EXTS = ['csv','tsv','json','jsonl','ndjson','xlsx','xls','yaml','yml','xml','sql'];

function acceptFile(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (!SUPPORTED_EXTS.includes(ext)) {
    showError(`Unsupported file type ".${ext}". Supported: CSV, TSV, JSON, JSONL, Excel (.xlsx/.xls), YAML, XML, SQL.`);
    return;
  }
  hideError();
  selectedFile = file;

  document.getElementById('previewName').textContent = file.name;
  document.getElementById('previewSize').textContent = formatBytes(file.size) + ' · .' + ext.toUpperCase();
  document.getElementById('filePreview').classList.remove('hidden');
  document.getElementById('importBtn').disabled = false;
}

function clearFile() {
  selectedFile = null;
  document.getElementById('filePreview').classList.add('hidden');
  document.getElementById('importBtn').disabled = true;
  document.getElementById('fileInput').value = '';
  hideError();
}

// ── Import Flow ────────────────────────────────────────────────
async function startImport() {
  if (!selectedFile) return;

  setStep(2);
  showPanel('processingPanel');
  hidePanel('zonePanel');
  document.getElementById('uploadTips').style.display = 'none';

  animateProcessingSteps();

  const form = new FormData();
  form.append('file', selectedFile);

  try {
    const res  = await fetch('/api/upload', { method: 'POST', body: form });
    const data = await res.json();

    if (data.error) {
      showError(data.error);
      setStep(1);
      showPanel('zonePanel');
      hidePanel('processingPanel');
      document.getElementById('uploadTips').style.display = '';
      return;
    }

    renderResults(data);
    setStep(3);
    showPanel('resultPanel');
    hidePanel('processingPanel');

  } catch (err) {
    showError('Upload failed: ' + err.message);
    setStep(1);
    showPanel('zonePanel');
    hidePanel('processingPanel');
    document.getElementById('uploadTips').style.display = '';
  }
}

function animateProcessingSteps() {
  const steps = ['proc1','proc2','proc3'];
  steps.forEach((id, i) => {
    setTimeout(() => {
      document.getElementById(id)?.classList.add('proc-step-active');
    }, i * 1200);
  });
}

// ── Results ────────────────────────────────────────────────────
function renderResults(data) {
  document.getElementById('resultTitle').textContent =
    `"${data.display_name}" imported successfully`;
  document.getElementById('resultSub').textContent =
    `${data.row_count.toLocaleString()} rows · ${data.columns.length} columns · from ${data.source_file}`;

  document.getElementById('schemaTableName').textContent = data.table_name;
  document.getElementById('aiBadge').textContent = data.ai_used ? '✦ AI organized' : 'auto-detected';

  // Column mapping table
  const tbody = document.getElementById('schemaColBody');
  tbody.innerHTML = data.columns.map(col => `
    <tr>
      <td class="col-original">${escHtml(col.original)}</td>
      <td><code class="col-clean">${escHtml(col.clean_name)}</code></td>
      <td><span class="type-badge type-${col.type}">${col.type}</span></td>
    </tr>
  `).join('');

  // Data preview
  const cleanCols = data.columns.map(c => c.clean_name);
  document.getElementById('dataPreviewHead').innerHTML =
    ['#', ...cleanCols].map(c => `<th>${escHtml(c)}</th>`).join('');

  const previewRows = data.sample_rows || [];
  document.getElementById('dataPreviewBody').innerHTML = previewRows.map((row, i) => `
    <tr>
      <td class="preview-row-num">${i + 1}</td>
      ${row.map(cell => `<td>${escHtml(cell == null ? '' : String(cell))}</td>`).join('')}
    </tr>
  `).join('');

  const showing = Math.min(previewRows.length, 5);
  document.getElementById('previewCountLabel').textContent =
    `(first ${showing} of ${data.row_count.toLocaleString()} rows)`;
}

function resetUpload() {
  selectedFile = null;
  document.getElementById('filePreview').classList.add('hidden');
  document.getElementById('importBtn').disabled = true;
  document.getElementById('fileInput').value = '';
  hideError();
  setStep(1);
  showPanel('zonePanel');
  hidePanel('processingPanel');
  hidePanel('resultPanel');
  document.getElementById('uploadTips').style.display = '';

  // reset proc steps
  ['proc1','proc2','proc3'].forEach(id =>
    document.getElementById(id)?.classList.remove('proc-step-active')
  );
}

// ── Step indicator ─────────────────────────────────────────────
function setStep(n) {
  [1,2,3].forEach(i => {
    const el = document.getElementById('step' + i);
    el.classList.toggle('active',    i === n);
    el.classList.toggle('completed', i < n);
  });
}

// ── Panel helpers ──────────────────────────────────────────────
function showPanel(id) { document.getElementById(id).classList.remove('hidden'); }
function hidePanel(id) { document.getElementById(id).classList.add('hidden'); }

function showError(msg) {
  const el = document.getElementById('uploadError');
  el.textContent = msg;
  el.classList.remove('hidden');
}
function hideError() { document.getElementById('uploadError').classList.add('hidden'); }

// ── Utils ──────────────────────────────────────────────────────
function formatBytes(b) {
  if (b < 1024)     return b + ' B';
  if (b < 1048576)  return (b/1024).toFixed(1) + ' KB';
  return (b/1048576).toFixed(2) + ' MB';
}
function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
