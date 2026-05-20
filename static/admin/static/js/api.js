/**
 * AI RADAR — API Client
 */

const API_BASE = '/api/v1/admin';

async function fetchJSON(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${response.status}`);
    }
    return response.json();
}

function api(path, options = {}) {
    return fetchJSON(`${API_BASE}${path}`, options);
}
