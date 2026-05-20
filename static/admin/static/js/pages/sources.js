/**
 * AI RADAR — Sources Page
 */

async function loadSources() {
    try {
        const sources = await api('/sources');
        renderSourcesTable(sources);
    } catch (err) {
        console.error('Sources load error:', err);
        showToast('Ошибка загрузки источников', 'error');
    }
}

function renderSourcesTable(sources) {
    const tbody = document.querySelector('#sources-table tbody');
    tbody.innerHTML = sources.map(s => `
        <tr>
            <td><code>${s.id}</code></td>
            <td><strong>${s.name}</strong></td>
            <td>${s.code}</td>
            <td><a href="${s.api_base_url}" target="_blank" class="link">${s.api_base_url?.slice(0, 30) || '—'}...</a></td>
            <td>${s.auth_type || '—'}</td>
            <td>${s.rate_limit ? JSON.stringify(s.rate_limit) : '—'}</td>
            <td>${s.is_active ? '<span class="badge status-completed">Активен</span>' : '<span class="badge status-idle">Выключен</span>'}</td>
            <td>
                <button class="btn btn-sm ${s.is_active ? 'btn-danger' : 'btn-primary'}" onclick="toggleSource('${s.code}')">
                    ${s.is_active ? 'Выключить' : 'Включить'}
                </button>
            </td>
        </tr>
    `).join('');
}

async function toggleSource(code) {
    try {
        await api(`/sources/${code}/toggle`, { method: 'POST' });
        showToast('Статус источника изменён', 'success');
        loadSources();
    } catch (err) {
        showToast('Ошибка', 'error');
    }
}
