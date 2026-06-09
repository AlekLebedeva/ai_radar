/**
 * AI RADAR — Main Application
 * Interests loaded from DB categories (parser/LLM data).
 */

const API = {
    session: "/api/v1/user/session",
    me: "/api/v1/user/me",
    categories: "/api/v1/categories",
    interests: "/api/v1/user/interests",
    profile: "/api/v1/user/profile",
};

let availableCategories = [];
let selectedInterests = new Set();
let currentUser = null;

async function apiFetch(url, options = {}) {
    const response = await fetch(url, {
        credentials: "same-origin",
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || "API error");
    }

    if (response.status === 204) {
        return null;
    }
    return response.json();
}

async function init() {
    document.getElementById("btn-start").addEventListener("click", async () => {
        await loadCategories();
        showScreen("interests");
        renderInterests("interests-grid");
    });

    document.getElementById("btn-save-interests").addEventListener("click", saveInterests);
    document.getElementById("btn-skip-interests").addEventListener("click", async () => {
        await saveInterests(true);
    });

    document.querySelectorAll(".tile").forEach(tile => {
        tile.addEventListener("click", async () => {
            const tileName = tile.dataset.tile;
            if (tileName === "settings") {
                await openSettings();
            }
            showScreen(tileName);
        });
    });

    document.querySelectorAll("[data-back]").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            showScreen("main");
        });
    });

    document.getElementById("btn-save-settings").addEventListener("click", saveSettings);

    document.getElementById("btn-logout").addEventListener("click", async () => {
        selectedInterests = new Set();
        currentUser = null;
        document.cookie = "ai_radar_user_session=; Max-Age=0; path=/";
        showScreen("onboarding");
    });

    try {
        currentUser = await apiFetch(API.session, { method: "POST" });
        syncUserToUi();
        await loadCategories();
        hydrateSelectedInterests();
        navigateAfterAuth();
    } catch (error) {
        console.error("Session init failed:", error);
        showScreen("onboarding");
        showToast("Не удалось подключиться к API. Проверьте сервер.", "info");
    }
}

function navigateAfterAuth() {
    if (currentUser && !currentUser.profile.onboarding_completed) {
        showScreen("onboarding");
        return;
    }
    showScreen("main");
}

function syncUserToUi() {
    if (!currentUser) {
        return;
    }
    const email = currentUser.profile.email || `user-${String(currentUser.id).slice(0, 8)}@ai-radar.local`;
    document.getElementById("user-email").textContent = email;
    document.getElementById("settings-email").textContent = email;
}

function hydrateSelectedInterests() {
    selectedInterests = new Set((currentUser?.interests || []).map(i => i.category));
}

async function loadCategories() {
    availableCategories = await apiFetch(API.categories);
}

function showScreen(name) {
    document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
    document.getElementById(`screen-${name}`).classList.add("active");
    window.scrollTo(0, 0);
}

function renderInterests(containerId) {
    const container = document.getElementById(containerId);
    if (!availableCategories.length) {
        container.innerHTML = `<p class="subtitle">Категории пока не собраны парсерами. Запустите сбор в админке.</p>`;
        return;
    }

    container.innerHTML = availableCategories.map(category => `
        <div class="interest-chip ${selectedInterests.has(category.slug) ? "selected" : ""}" data-id="${category.slug}">
            <span>${category.icon}</span>
            <span>${category.label}</span>
            <span class="interest-count">${category.item_count}</span>
        </div>
    `).join("");

    container.querySelectorAll(".interest-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const id = chip.dataset.id;
            if (selectedInterests.has(id)) {
                selectedInterests.delete(id);
                chip.classList.remove("selected");
            } else {
                selectedInterests.add(id);
                chip.classList.add("selected");
            }
        });
    });
}

async function saveInterests(skip = false) {
    try {
        const categories = skip ? [] : Array.from(selectedInterests);
        currentUser = await apiFetch(API.interests, {
            method: "PUT",
            body: JSON.stringify({ categories }),
        });
        hydrateSelectedInterests();
        showScreen("main");
        if (skip) {
            showToast("Онбординг пропущен", "success");
        } else {
            showToast(`Сохранено ${categories.length} интересов`, "success");
        }
    } catch (error) {
        console.error("Save interests failed:", error);
        showToast("Не удалось сохранить интересы", "info");
    }
}

async function openSettings() {
    try {
        currentUser = await apiFetch(API.me);
        hydrateSelectedInterests();
        syncUserToUi();
        renderInterests("settings-interests-grid");
        document.getElementById("setting-email").checked = currentUser.profile.email_notifications;
        document.getElementById("setting-frequency").value = currentUser.profile.digest_frequency || "daily";
    } catch (error) {
        console.error("Settings load failed:", error);
        showToast("Не удалось загрузить настройки", "info");
    }
}

async function saveSettings() {
    try {
        const categories = Array.from(selectedInterests);
        const emailNotifications = document.getElementById("setting-email").checked;
        const digestFrequency = document.getElementById("setting-frequency").value;

        currentUser = await apiFetch(API.interests, {
            method: "PUT",
            body: JSON.stringify({ categories }),
        });
        currentUser = await apiFetch(API.profile, {
            method: "PUT",
            body: JSON.stringify({
                email_notifications: emailNotifications,
                digest_frequency: digestFrequency,
            }),
        });

        hydrateSelectedInterests();
        showToast("Настройки сохранены", "success");
        showScreen("main");
    } catch (error) {
        console.error("Save settings failed:", error);
        showToast("Не удалось сохранить настройки", "info");
    }
}

function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.style.cssText = `
        position: fixed; bottom: 24px; right: 24px; z-index: 2000;
        background: #1e293b; border: 1px solid #334155; border-radius: 8px;
        padding: 14px 20px; min-width: 280px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        display: flex; align-items: center; gap: 12px; animation: slideIn 0.3s ease;
        border-left: 3px solid ${type === "success" ? "#10b981" : "#3b82f6"};
        color: #f1f5f9; font-size: 14px;
    `;
    toast.innerHTML = `<span>${type === "success" ? "&#9989;" : "&#8505;"}</span><span>${message}</span>`;
    document.body.appendChild(toast);
    setTimeout(() => { toast.style.opacity = "0"; setTimeout(() => toast.remove(), 300); }, 3000);
}

document.addEventListener("DOMContentLoaded", init);
