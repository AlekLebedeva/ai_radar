/**
 * AI RADAR — Modal Logic
 */

function initModals() {
    const modal = document.getElementById('modal-new-task');
    const btnNew = document.getElementById('btn-new-task');
    const btnClose = modal.querySelector('.modal-close');
    const btnCancel = modal.querySelector('.modal-cancel');
    const btnSubmit = document.getElementById('btn-submit-task');

    btnNew.addEventListener('click', () => {
        const now = new Date();
        const weekAgo = new Date(now - 7 * 24 * 60 * 60 * 1000);
        document.getElementById('task-date-from').value = weekAgo.toISOString().slice(0, 16);
        document.getElementById('task-date-to').value = now.toISOString().slice(0, 16);
        modal.classList.add('active');
    });

    [btnClose, btnCancel].forEach(btn => {
        btn.addEventListener('click', () => modal.classList.remove('active'));
    });

    btnSubmit.addEventListener('click', submitNewTask);
    modal.querySelector('.modal-overlay').addEventListener('click', () => modal.classList.remove('active'));
}

async function submitNewTask() {
    const parser = document.getElementById('task-parser').value;
    const dateFrom = document.getElementById('task-date-from').value;
    const dateTo = document.getElementById('task-date-to').value;
    const maxItems = document.getElementById('task-max-items').value;
    const filtersStr = document.getElementById('task-filters').value;

    if (!parser || !dateFrom || !dateTo) {
        showToast('Заполните обязательные поля', 'error');
        return;
    }

    const payload = {
        date_from: new Date(dateFrom).toISOString(),
        date_to: new Date(dateTo).toISOString(),
        max_items: parseInt(maxItems) || 1000,
    };

    if (filtersStr) {
        try {
            payload.filters = JSON.parse(filtersStr);
        } catch {
            showToast('Неверный JSON в фильтрах', 'error');
            return;
        }
    }

    try {
        await api(`/tasks/${parser}/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        showToast('Задача создана и запущена', 'success');
        document.getElementById('modal-new-task').classList.remove('active');
        loadTasks();
    } catch (err) {
        showToast('Ошибка создания задачи', 'error');
    }
}
