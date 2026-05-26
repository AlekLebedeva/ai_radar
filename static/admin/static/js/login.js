document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('loginForm');
    const errorMsg = document.getElementById('errorMsg');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorMsg.style.display = 'none';

        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;

        try {
            const response = await fetch('/api/v1/admin/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
                credentials: 'include',  // ← ВАЖНО: получаем и отправляем cookie
            });

            if (response.ok) {
                window.location.href = '/admin/';
            } else {
                const data = await response.json().catch(() => ({}));
                errorMsg.textContent = data.error || 'Неверный логин или пароль';
                errorMsg.style.display = 'block';
                document.getElementById('password').value = '';
            }
        } catch (err) {
            errorMsg.textContent = 'Ошибка соединения с сервером';
            errorMsg.style.display = 'block';
        }
    });
});