/**
 * AI RADAR — Utilities
 */

function renderStatus(status) {
    const map = {
        pending: ['⏳', 'Ожидание', 'status-pending'],
        running: ['▶️', 'В работе', 'status-running'],
        completed: ['✅', 'Завершено', 'status-completed'],
        failed: ['❌', 'Ошибка', 'status-failed'],
        idle: ['⏸️', 'Ожидание', 'status-idle'],
    };
    const [icon, label, cls] = map[status] || ['❓', status, 'status-idle'];
    return `<span class="badge ${cls}">${icon} ${label}</span>`;
}

function formatDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

function formatNumber(n) {
    if (n === undefined || n === null) return '—';
    return n.toLocaleString('ru-RU');
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
