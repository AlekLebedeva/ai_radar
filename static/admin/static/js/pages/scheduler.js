/**
 * AI RADAR — Scheduler Control
 */

let schedulerConfig = null;

async function loadScheduler() {
    try {
        const data = await api('/scheduler');
        schedulerConfig = data;
        renderScheduler(data);
    } catch (err) {
        console.error('Scheduler load error:', err);
    }
}

function renderScheduler(config) {
    const indicator = document.getElementById('scheduler-indicator');
    const statusText = document.getElementById('scheduler-status-text');

    if (config.enabled) {
        indicator.className = 'scheduler-indicator running';
        indicator.style.color = '#10b981';
        statusText.textContent = 'Шедулер активен';
        statusText.style.color = '#10b981';
    } else {
        indicator.className = 'scheduler-indicator idle';
        indicator.style.color = '#64748b';
        statusText.textContent = 'Шедулер выключен';
        statusText.style.color = '#64748b';
    }

    document.getElementById('scheduler-interval').textContent = config.interval_hours || 48;
    document.getElementById('scheduler-last-run').textContent = config.last_run
        ? new Date(config.last_run).toLocaleString('ru-RU')
        : '-';
    document.getElementById('scheduler-next-run').textContent = config.next_run
        ? new Date(config.next_run).toLocaleString('ru-RU')
        : '-';

    document.getElementById('scheduler-interval-input').value = config.interval_hours || 48;

    if (config.start_date) {
        const d = new Date(config.start_date);
        document.getElementById('scheduler-start-date').value = d.toISOString().slice(0, 16);
    }

    const checkboxes = document.querySelectorAll('#scheduler-parsers-list input[type="checkbox"]');
    const activeParsers = config.parsers || ['github', 'reddit', 'huggingface', 'arxiv'];
    checkboxes.forEach(cb => {
        cb.checked = activeParsers.includes(cb.value);
    });

    document.getElementById('scheduler-parsers').textContent = (config.parsers || []).join(', ');

    updateButtonStates(config.enabled);
}

function updateButtonStates(enabled) {
    document.getElementById('btn-scheduler-enable').style.display = enabled ? 'none' : 'inline-block';
    document.getElementById('btn-scheduler-disable').style.display = enabled ? 'inline-block' : 'none';
}

function initSchedulerControls() {
    document.getElementById('btn-scheduler-enable')?.addEventListener('click', async () => {
        try {
            const data = await api('/scheduler/enable', { method: 'POST' });
            schedulerConfig = data;
            renderScheduler(data);
            showToast('Шедулер включен', 'success');
        } catch (err) {
            showToast('Ошибка включения шедулера', 'error');
        }
    });

    document.getElementById('btn-scheduler-disable')?.addEventListener('click', async () => {
        try {
            const data = await api('/scheduler/disable', { method: 'POST' });
            schedulerConfig = data;
            renderScheduler(data);
            showToast('Шедулер выключен', 'info');
        } catch (err) {
            showToast('Ошибка выключения шедулера', 'error');
        }
    });

    document.getElementById('btn-scheduler-trigger')?.addEventListener('click', async () => {
        try {
            const result = await api('/scheduler/trigger', { method: 'POST' });
            showToast(`Запущено задач: ${result.tasks.length}`, 'success');
            loadScheduler();
        } catch (err) {
            showToast('Ошибка запуска: ' + (err.message || ''), 'error');
        }
    });

    document.getElementById('btn-scheduler-save')?.addEventListener('click', async () => {
        const interval = parseInt(document.getElementById('scheduler-interval-input').value, 10) || 48;
        const startDate = document.getElementById('scheduler-start-date').value;

        const parserCheckboxes = document.querySelectorAll('#scheduler-parsers-list input[type="checkbox"]:checked');
        const parsers = Array.from(parserCheckboxes).map(cb => cb.value);

        const payload = { interval_hours: interval };
        if (startDate) {
            payload.start_date = new Date(startDate).toISOString();
        }
        if (parsers.length > 0) {
            payload.parsers = parsers;
        }

        try {
            const data = await api('/scheduler', {
                method: 'PATCH',
                body: JSON.stringify(payload),
                headers: { 'Content-Type': 'application/json' },
            });
            schedulerConfig = data;
            renderScheduler(data);
            showToast('Настройки сохранены', 'success');
        } catch (err) {
            showToast('Ошибка сохранения настроек', 'error');
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    initSchedulerControls();
});
