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
