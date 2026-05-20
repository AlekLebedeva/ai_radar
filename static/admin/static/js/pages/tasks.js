/**
 * AI RADAR — Tasks Page
 */

async function loadTasks() {
    try {
        const tasks = await api('/tasks?limit=100');
        renderTasksTable(tasks);
    } catch (err) {
        console.error('Tasks load error:', err);
        showToast('Ошибка загрузки задач', 'error');
    }
}

function renderTasksTable(tasks) {
    const tbody = document.querySelector('#tasks-table tbody');
    tbody.innerHTML = tasks.map(t => `
        <tr>
            <td><code>${t.id.slice(0, 8)}</code></td>
            <td><strong>${t.parser_name}</strong></td>
            <td>${renderStatus(t.status)}</td>
            <td>${formatDate(t.date_from)} — ${formatDate(t.date_to)}</td>
            <td>${t.items_collected}</td>
            <td>${t.items_new}</td>
            <td>${formatDate(t.started_at)}</td>
            <td>
                ${t.status === 'failed' || t.status === 'pending' ? 
                    `<button class="btn btn-sm btn-primary" onclick="retryTask('${t.id}')">🔄 Retry</button>` : 
                    '<span class="text-muted">—</span>'}
            </td>
        </tr>
    `).join('');
}

async function retryTask(taskId) {
    try {
        await api(`/tasks/${taskId}/retry`, { method: 'POST' });
        showToast('Задача поставлена в очередь на повторный запуск', 'success');
        loadTasks();
    } catch (err) {
        showToast('Ошибка при перезапуске задачи', 'error');
    }
}
