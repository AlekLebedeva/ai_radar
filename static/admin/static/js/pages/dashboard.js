/**
 * AI RADAR — Dashboard Page
 */

async function loadDashboard() {
    try {
        const [stats, tasks] = await Promise.all([
            api('/stats'),
            api('/tasks?limit=5'),
        ]);

        document.getElementById('stat-raw').textContent = formatNumber(stats.total_raw);
        document.getElementById('stat-enriched').textContent = formatNumber(stats.total_enriched);
        document.getElementById('stat-vectors').textContent = formatNumber(stats.total_vectors);
        document.getElementById('stat-pending').textContent = formatNumber(stats.pending_tasks);
        document.getElementById('stat-failed').textContent = formatNumber(stats.failed_tasks);
        document.getElementById('stat-tasks').textContent = formatNumber(
            stats.tables.find(t => t.table_name === 'parser_tasks')?.row_count || 0
        );

        const tbody = document.querySelector('#dashboard-tasks-table tbody');
        tbody.innerHTML = tasks.map(t => `
            <tr>
                <td><strong>${t.parser_name}</strong></td>
                <td>${renderStatus(t.status)}</td>
                <td>${t.items_collected}</td>
                <td>${t.items_new}</td>
                <td>${formatDate(t.started_at)}</td>
            </tr>
        `).join('');

    } catch (err) {
        console.error('Dashboard load error:', err);
        showToast('Ошибка загрузки дашборда', 'error');
    }
}
