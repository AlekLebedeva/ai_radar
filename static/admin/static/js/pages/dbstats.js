/**
 * AI RADAR — DB Stats Page
 */

async function loadDbStats() {
    try {
        const stats = await api('/stats');

        const grid = document.getElementById('db-stats-grid');
        grid.innerHTML = stats.tables.map(t => `
            <div class="stat-card">
                <div class="stat-icon" style="font-size: 20px;">🗄️</div>
                <div class="stat-value">${formatNumber(t.row_count)}</div>
                <div class="stat-label">${t.table_name}</div>
            </div>
        `).join('');

        const tbody = document.querySelector('#db-tables-table tbody');
        tbody.innerHTML = stats.tables.map(t => `
            <tr>
                <td><strong>${t.table_name}</strong></td>
                <td>${formatNumber(t.row_count)}</td>
                <td>${formatDate(t.last_updated)}</td>
            </tr>
        `).join('');

    } catch (err) {
        console.error('DB stats load error:', err);
        showToast('Ошибка загрузки статистики БД', 'error');
    }
}
