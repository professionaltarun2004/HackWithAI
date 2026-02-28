/**
 * API client — single source of truth for backend URLs.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchJSON(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, options);
    if (!res.ok) {
        const body = await res.text();
        throw new Error(`API ${path} → ${res.status}: ${body}`);
    }
    return res.json();
}

// ── Health ──────────────────────────────────────────
export const getHealth = () => fetchJSON('/health');

// ── Ingest ──────────────────────────────────────────
export const triggerIngest = () => fetchJSON('/ingest', { method: 'POST' });

// ── Graph summary ───────────────────────────────────
export const getGraphSummary = () => fetchJSON('/graph/summary');

// ── Reconciliation ──────────────────────────────────
export const getReconcileInvoices = () => fetchJSON('/reconcile/invoices');
export const getInvoiceAudit = (invoiceId) => fetchJSON(`/reconcile/invoice/${invoiceId}`);

// ── Vendors ─────────────────────────────────────────
export const getVendors = () => fetchJSON('/vendors');
export const getVendorDetail = (gstin) => fetchJSON(`/vendors/${gstin}`);
export const getVendorRisk = (gstin) => fetchJSON(`/vendors/${gstin}/risk`);

// ── Graph vis data ──────────────────────────────────
export const getGraphData = () => fetchJSON('/graph');

// ── CSV Upload ──────────────────────────────────────
/**
 * Upload a raw CSV string plus a type hint to the backend.
 * @param {"vendors"|"invoices"} type
 * @param {string} content  Raw CSV text (no client-side parsing)
 * @returns {Promise<{status: string, file_saved: string, vendors_loaded: number, invoices_loaded: number}>}
 */
export async function uploadCsv(type, content) {
    const formData = new FormData();
    formData.append('type', type);
    const blob = new Blob([content], { type: 'text/csv' });
    formData.append('file', blob, `${type}.csv`);

    const res = await fetch(`${API_BASE}/realtime/upload-csv`, {
        method: 'POST',
        body: formData,
    });
    if (!res.ok) {
        const body = await res.text();
        throw new Error(`Upload failed → ${res.status}: ${body}`);
    }
    return res.json();
}

// ── Refresh-all helper ──────────────────────────────
/**
 * Fetch graph, vendors, and mismatches in parallel.
 * Returns { vendors, mismatches, graph }.
 * Useful after a CSV upload or re-ingest to refresh all views at once.
 */
export async function refreshAllData() {
    const [vendors, mismatches, graph] = await Promise.all([
        fetchJSON('/vendors'),
        fetchJSON('/reconcile/invoices'),
        fetchJSON('/graph'),
    ]);
    return { vendors, mismatches, graph };
}
