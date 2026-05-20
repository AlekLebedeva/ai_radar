/**
 * AI RADAR — Logs Page
 */

async function loadLogs() {
    try {
        const logs = await api('/logs?limit=100');
        renderLogsTable(logs);
    } catch (err) {
        console.error('Logs load error:', err);
        showToast('Ошибка загрузки логов', 'error');
    }
}

function renderLogsTable(logs) {
    const tbody = document.querySelector('#logs-table tbody');
    tbody.innerHTML = logs.map(l => `
        <tr>
            <td>${formatDate(l.run_at)}</td>
            <td><strong>${l.parser_name}</strong></td>
            <td>${renderStatus(l.status)}</td>
            <td>${l.items_count}</td>
            <td>${l.errors_count}</td>
            <td>${l.duration_sec ? l.duration_sec + 's' : '—'}</td>
            <td>
                ${l.details ? 
                    `<button class="btn btn-sm btn-secondary" onclick='showLogDetails(${JSON.stringify(l.details)})'>📋</button>` : 
                    '—'}
            </td>
        </tr>
    `).join('');
}

function showLogDetails(details) {
    alert(JSON.stringify(details, null, 2));
}
