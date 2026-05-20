/**
 * AI RADAR — Main Application
 * Demo mode: always shows onboarding as first visit
 */

const INTERESTS = [
    { id: "cv", label: "Computer Vision", icon: "&#128247;" },
    { id: "nlp", label: "NLP", icon: "&#128172;" },
    { id: "audio", label: "Audio / Speech", icon: "&#127908;" },
    { id: "multimodal", label: "Multimodal", icon: "&#127912;" },
    { id: "rl", label: "Reinforcement Learning", icon: "&#127942;" },
    { id: "graph", label: "Graph Neural Networks", icon: "&#127760;" },
    { id: "geo", label: "Geospatial / GIS", icon: "&#128506;" },
    { id: "rag", label: "RAG", icon: "&#128214;" },
    { id: "tabular", label: "Tabular Data", icon: "&#128202;" },
    { id: "generative", label: "Generative AI", icon: "&#127912;" },
    { id: "llm", label: "LLM / Agents", icon: "&#129302;" },
    { id: "diffusion", label: "Diffusion Models", icon: "&#127744;" },
];

let selectedInterests = new Set();
let isDemoMode = true;

function init() {
    // Demo mode toggle
    const demoCheckbox = document.getElementById("demo-checkbox");
    demoCheckbox.checked = true;
    demoCheckbox.addEventListener("change", (e) => {
        isDemoMode = e.target.checked;
        if (isDemoMode) {
            showScreen("onboarding");
        } else {
            showScreen("main");
        }
    });

    // Onboarding
    document.getElementById("btn-start").addEventListener("click", () => {
        showScreen("interests");
        renderInterests();
    });

    // Interests
    document.getElementById("btn-save-interests").addEventListener("click", saveInterests);
    document.getElementById("btn-skip-interests").addEventListener("click", () => {
        showScreen("main");
    });

    // Tiles
    document.querySelectorAll(".tile").forEach(tile => {
        tile.addEventListener("click", () => {
            const tileName = tile.dataset.tile;
            showScreen(tileName);
        });
    });

    // Back buttons
    document.querySelectorAll("[data-back]").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            showScreen("main");
        });
    });

    // Settings
    document.getElementById("btn-save-settings").addEventListener("click", () => {
        showToast("Настройки сохранены", "success");
        showScreen("main");
    });

    // Logout
    document.getElementById("btn-logout").addEventListener("click", () => {
        showScreen("onboarding");
    });

    // Start in onboarding (demo mode)
    showScreen("onboarding");
}

function showScreen(name) {
    document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
    document.getElementById(`screen-${name}`).classList.add("active");
    window.scrollTo(0, 0);
}

function renderInterests() {
    const container = document.getElementById("interests-grid");
    container.innerHTML = INTERESTS.map(i => `
        <div class="interest-chip ${selectedInterests.has(i.id) ? 'selected' : ''}" data-id="${i.id}">
            <span>${i.icon}</span>
            <span>${i.label}</span>
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

function saveInterests() {
    const interests = Array.from(selectedInterests);
    console.log("Saved interests:", interests);
    // TODO: POST to API /api/v1/user/interests
    showScreen("main");
    showToast(`Выбрано ${interests.length} интересов`, "success");
}

function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.style.cssText = `
        position: fixed; bottom: 24px; right: 24px; z-index: 2000;
        background: #1e293b; border: 1px solid #334155; border-radius: 8px;
        padding: 14px 20px; min-width: 280px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        display: flex; align-items: center; gap: 12px; animation: slideIn 0.3s ease;
        border-left: 3px solid ${type === 'success' ? '#10b981' : '#3b82f6'};
        color: #f1f5f9; font-size: 14px;
    `;
    toast.innerHTML = `<span>${type === 'success' ? '&#9989;' : '&#8505;'}</span><span>${message}</span>`;
    document.body.appendChild(toast);
    setTimeout(() => { toast.style.opacity = "0"; setTimeout(() => toast.remove(), 300); }, 3000);
}

document.addEventListener("DOMContentLoaded", init);
