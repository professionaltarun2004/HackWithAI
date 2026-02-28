import React, { useState, useEffect, useCallback, useRef } from 'react';
import GraphVisualization from './GraphVisualization';
import MismatchList from './MismatchList';
import VendorRiskBoard from './VendorRiskBoard';
import { getVendors, getVendorDetail, getVendorRisk, triggerIngest, uploadCsv } from './api';
import './index.css';

// ── Toast hook ────────────────────────────────────────────
let _toastId = 0;
function useToasts() {
    const [toasts, setToasts] = useState([]);
    const addToast = useCallback((message, type = 'success') => {
        const id = ++_toastId;
        setToasts(prev => [...prev, { id, message, type }]);
        setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
    }, []);
    return { toasts, addToast };
}

// ── UploadCsvTab component ────────────────────────────────
function UploadCsvTab({ onRefresh }) {
    const [vendorsFile, setVendorsFile]     = useState(null);
    const [invoicesFile, setInvoicesFile]   = useState(null);
    const [uploadingVendors, setUploadingVendors]   = useState(false);
    const [uploadingInvoices, setUploadingInvoices] = useState(false);
    const [reingesting, setReingesting]     = useState(false);
    const [lastUploadTime, setLastUploadTime] = useState(null);
    const { toasts, addToast } = useToasts();

    const anyBusy = uploadingVendors || uploadingInvoices || reingesting;

    const handleUpload = async (type, file, setUploading) => {
        if (!file) return;
        setUploading(true);
        try {
            const content = await file.text();   // raw bytes → string, no parsing
            await uploadCsv(type, content);
            setLastUploadTime(new Date().toLocaleTimeString());
            addToast(
                `${type === 'vendors' ? 'Vendors' : 'Invoices'} CSV uploaded successfully`,
                'success'
            );
            onRefresh();
        } catch (err) {
            addToast(err.message, 'error');
        } finally {
            setUploading(false);
        }
    };

    const handleReingest = async () => {
        setReingesting(true);
        try {
            await triggerIngest();
            setLastUploadTime(new Date().toLocaleTimeString());
            addToast('Reset complete. Showing only the original default data.', 'success');
            onRefresh();
        } catch (err) {
            addToast(err.message, 'error');
        } finally {
            setReingesting(false);
        }
    };

    return (
        <div className="upload-page">
            {/* Toast container */}
            <div className="toast-container">
                {toasts.map(t => (
                    <div key={t.id} className={`toast toast-${t.type}`}>
                        {t.type === 'success' ? '✅' : '❌'} {t.message}
                    </div>
                ))}
            </div>

            <div className="upload-container">
                <div className="upload-header-row">
                    <div className="upload-title-group">
                        <h2 className="upload-heading">Upload CSVs</h2>
                        {lastUploadTime && (
                            <span className="upload-last-time">Last updated: {lastUploadTime}</span>
                        )}
                    </div>
                    <div className="upload-tooltip-wrapper">
                        <span className="upload-help-icon" tabIndex={0}>?</span>
                        <div className="upload-tooltip-box">
                            Upload new CSVs in the same column format as the default vendors.csv and
                            invoices.csv. The new rows are ADDED to the existing graph — the
                            original vendors and invoices are always kept. Press "Reset to Default
                            Data" to remove your uploads and return to the original dataset.
                        </div>
                    </div>
                </div>

                <p className="upload-subtext">
                    Upload a new <code>vendors.csv</code> or <code>invoices.csv</code>. The backend
                    persists the file and re-ingests immediately — all tabs refresh automatically.
                </p>

                <div className="upload-cards">
                    {/* ── Vendors card ── */}
                    <div className="upload-card">
                        <div className="upload-card-header">
                            <span className="upload-card-icon">🏢</span>
                            <h3>Vendors CSV</h3>
                        </div>
                        <p className="upload-card-hint">
                            Required columns: <code>gstin</code>, <code>name</code>,{' '}
                            <code>missed_filings</code>
                        </p>
                        <label className="upload-file-label">
                            <input
                                type="file"
                                accept=".csv,text/csv"
                                className="upload-file-input"
                                disabled={anyBusy}
                                onChange={e => setVendorsFile(e.target.files[0] || null)}
                            />
                            {vendorsFile
                                ? <span className="upload-file-name">📄 {vendorsFile.name}</span>
                                : <span className="upload-file-placeholder">Choose vendors.csv…</span>
                            }
                        </label>
                        {uploadingVendors && (
                            <div className="upload-progress-bar">
                                <div className="upload-progress-fill" />
                            </div>
                        )}
                        <button
                            className="upload-btn"
                            disabled={!vendorsFile || anyBusy}
                            onClick={() => handleUpload('vendors', vendorsFile, setUploadingVendors)}
                        >
                            {uploadingVendors
                                ? <><span className="upload-spinner" /> Uploading…</>
                                : 'Upload vendors.csv'
                            }
                        </button>
                    </div>

                    {/* ── Invoices card ── */}
                    <div className="upload-card">
                        <div className="upload-card-header">
                            <span className="upload-card-icon">🧾</span>
                            <h3>Invoices CSV</h3>
                        </div>
                        <p className="upload-card-hint">
                            Required columns: <code>invoice_id</code>, <code>seller_gstin</code>,{' '}
                            <code>buyer_gstin</code>, <code>amount</code>, <code>tax</code>,{' '}
                            <code>reported_by_seller</code>, <code>claimed_by_buyer</code>
                        </p>
                        <label className="upload-file-label">
                            <input
                                type="file"
                                accept=".csv,text/csv"
                                className="upload-file-input"
                                disabled={anyBusy}
                                onChange={e => setInvoicesFile(e.target.files[0] || null)}
                            />
                            {invoicesFile
                                ? <span className="upload-file-name">📄 {invoicesFile.name}</span>
                                : <span className="upload-file-placeholder">Choose invoices.csv…</span>
                            }
                        </label>
                        {uploadingInvoices && (
                            <div className="upload-progress-bar">
                                <div className="upload-progress-fill" />
                            </div>
                        )}
                        <button
                            className="upload-btn"
                            disabled={!invoicesFile || anyBusy}
                            onClick={() => handleUpload('invoices', invoicesFile, setUploadingInvoices)}
                        >
                            {uploadingInvoices
                                ? <><span className="upload-spinner" /> Uploading…</>
                                : 'Upload invoices.csv'
                            }
                        </button>
                    </div>
                </div>

                {/* ── Re-ingest strip ── */}
                <div className="upload-reingest-strip">
                    <div className="upload-reingest-text">
                        <strong>Reset to Default Data</strong>
                        <span>Removes all uploaded CSVs and restores only the original static vendors &amp; invoices.</span>
                    </div>
                    <button
                        className="upload-reingest-btn"
                        disabled={anyBusy}
                        onClick={handleReingest}
                    >
                        {reingesting
                            ? <><span className="upload-spinner upload-spinner-dark" /> Re-ingesting…</>
                            : '🔄 Reset / Re-ingest'
                        }
                    </button>
                </div>
            </div>
        </div>
    );
}

function App() {
    const [activeTab, setActiveTab] = useState('table');

    // ── Debounced refresh key — incrementing remounts child components ──
    const [refreshKey, setRefreshKey] = useState(0);
    const _debounceRef = useRef(null);
    const triggerRefresh = useCallback(() => {
        if (_debounceRef.current) clearTimeout(_debounceRef.current);
        _debounceRef.current = setTimeout(() => setRefreshKey(k => k + 1), 300);
    }, []);

    const [vendors, setVendors] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const [selectedGstin, setSelectedGstin] = useState(null);
    const [vendorDetail, setVendorDetail] = useState(null);
    const [detailLoading, setDetailLoading] = useState(false);
    const [detailError, setDetailError] = useState(null);

    // AI explanation via vendor risk endpoint
    const [aiExplanation, setAiExplanation] = useState(null);
    const [aiLoading, setAiLoading] = useState(false);
    const [aiError, setAiError] = useState(null);

    useEffect(() => {
        setLoading(true);
        setError(null);
        getVendors()
            .then(data => { setVendors(data); setLoading(false); })
            .catch(err => { setError(err.message); setLoading(false); });
    }, [refreshKey]);

    useEffect(() => {
        if (!selectedGstin) return;
        setDetailLoading(true);
        setDetailError(null);
        setAiExplanation(null);
        setAiLoading(false);
        setAiError(null);

        getVendorDetail(selectedGstin)
            .then(data => {
                setVendorDetail(data);
                setDetailLoading(false);
                // Auto-fetch AI explanation on vendor selection
                setAiLoading(true);
                getVendorRisk(selectedGstin)
                    .then(riskData => {
                        const reasons = riskData.reasons || [];
                        const explanation = `Vendor "${riskData.name}" (${riskData.gstin}) has a risk score of ${riskData.risk_score}/100 (${riskData.risk_level}). ` +
                            `Compliance score: ${riskData.compliance_score}%. ` +
                            (reasons.length > 0 ? `Risk factors: ${reasons.join('; ')}.` : 'No risk factors detected.');
                        setAiExplanation(explanation);
                        setAiLoading(false);
                    })
                    .catch(() => { setAiError("Failed to generate explanation"); setAiLoading(false); });
            })
            .catch(err => { setDetailError(err.message); setDetailLoading(false); });
    }, [selectedGstin]);

    const handleGenerateAi = () => {
        if (!selectedGstin) return;
        setAiLoading(true);
        setAiError(null);
        setAiExplanation(null);

        getVendorRisk(selectedGstin)
            .then(data => {
                const reasons = data.reasons || [];
                const explanation = `Vendor "${data.name}" (${data.gstin}) has a risk score of ${data.risk_score}/100 (${data.risk_level}). ` +
                    `Compliance score: ${data.compliance_score}%. ` +
                    (reasons.length > 0 ? `Risk factors: ${reasons.join('; ')}.` : 'No risk factors detected.');
                setAiExplanation(explanation);
                setAiLoading(false);
            })
            .catch(() => { setAiError("Failed to generate explanation"); setAiLoading(false); });
    };

    const getRiskBadgeClass = (level) => {
        if (level === 'low') return 'badge badge-low';
        if (level === 'medium') return 'badge badge-medium';
        if (level === 'high') return 'badge badge-high';
        if (level === 'critical') return 'badge badge-critical';
        return 'badge';
    };

    const handleSelectVendorFromGraph = (gstin) => {
        setSelectedGstin(gstin);
        setActiveTab('table');
    };

    return (
        <div className="app-wrapper">
            {/* Top navigation tabs */}
            <nav className="app-nav">
                <h1 className="app-title">🛡️ GST Risk Dashboard</h1>
                <div className="tab-bar">
                    <button
                        className={`tab-btn ${activeTab === 'table' ? 'tab-active' : ''}`}
                        onClick={() => setActiveTab('table')}
                    >
                        📋 Vendors &amp; Details
                    </button>
                    <button
                        className={`tab-btn ${activeTab === 'mismatches' ? 'tab-active' : ''}`}
                        onClick={() => setActiveTab('mismatches')}
                    >
                        🔍 Mismatches
                    </button>
                    <button
                        className={`tab-btn ${activeTab === 'risk' ? 'tab-active' : ''}`}
                        onClick={() => setActiveTab('risk')}
                    >
                        🏆 Vendor Risk
                    </button>
                    <button
                        className={`tab-btn ${activeTab === 'graph' ? 'tab-active' : ''}`}
                        onClick={() => setActiveTab('graph')}
                    >
                        🔗 Transaction Graph
                    </button>
                    <button
                        className={`tab-btn ${activeTab === 'upload' ? 'tab-active' : ''}`}
                        onClick={() => setActiveTab('upload')}
                    >
                        📤 Upload CSVs
                    </button>
                </div>
            </nav>

            {/* Mismatches Tab */}
            {activeTab === 'mismatches' && <MismatchList key={refreshKey} />}

            {/* Vendor Risk Tab */}
            {activeTab === 'risk' && <VendorRiskBoard key={refreshKey} />}

            {/* Graph Tab — "computing…" overlay handled by GraphVisualization itself */}
            {activeTab === 'graph' && (
                <div className="graph-page">
                    <GraphVisualization key={refreshKey} onSelectVendor={handleSelectVendorFromGraph} />
                </div>
            )}

            {/* Upload CSVs Tab */}
            {activeTab === 'upload' && (
                <UploadCsvTab onRefresh={triggerRefresh} />
            )}

            {/* Table Tab */}
            {activeTab === 'table' && (
                <div className="container">
            <div className="left-panel panel">
                <h2>Vendors List</h2>
                {loading && <p>Loading vendors...</p>}
                {error && <p className="error">{error}</p>}
                {!loading && !error && (
                    <div className="table-responsive">
                        <table>
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>GSTIN</th>
                                    <th>Risk Level</th>
                                    <th>Risk Score</th>
                                </tr>
                            </thead>
                            <tbody>
                                {vendors.map(v => (
                                    <tr
                                        key={v.gstin}
                                        onClick={() => setSelectedGstin(v.gstin)}
                                        className={selectedGstin === v.gstin ? 'selected-row' : ''}
                                    >
                                        <td>{v.name}</td>
                                        <td>{v.gstin}</td>
                                        <td>
                                            <span className={getRiskBadgeClass(v.risk_level)}>
                                                {v.risk_level}
                                            </span>
                                        </td>
                                        <td>{v.risk_score}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <div className="right-panel panel">
                <h2>Vendor Detail</h2>
                {!selectedGstin && (
                    <p className="placeholder">Select a vendor to view risk details.</p>
                )}

                {selectedGstin && detailLoading && <p>Loading details...</p>}
                {selectedGstin && detailError && <p className="error">{detailError}</p>}

                {selectedGstin && !detailLoading && !detailError && vendorDetail && (
                    <div className="detail-content">
                        <div className="detail-header">
                            <h3>{vendorDetail.name} ({vendorDetail.gstin})</h3>
                            <div className="risk-info">
                                <span className={getRiskBadgeClass(vendorDetail.risk_level)}>
                                    {vendorDetail.risk_level}
                                </span>
                                <span className="score-text">Score: {vendorDetail.risk_score}</span>
                            </div>
                        </div>

                        <div className="stats-grid">
                            <div className="stat-box">
                                <span className="stat-label">Missed Filings</span>
                                <span className="stat-value">{vendorDetail.missed_filings}</span>
                            </div>
                            <div className="stat-box">
                                <span className="stat-label">Total Incoming</span>
                                <span className="stat-value">{vendorDetail.total_incoming}</span>
                            </div>
                            <div className="stat-box">
                                <span className="stat-label">Total Outgoing</span>
                                <span className="stat-value">{vendorDetail.total_outgoing}</span>
                            </div>
                        </div>

                        <div className="graph-patterns-section" style={{ marginBottom: '2rem', padding: '1rem', background: '#eef2ff', borderRadius: '0.5rem', border: '1px solid #c7d2fe' }}>
                            <h4 style={{ marginTop: 0, color: '#3730a3' }}>Graph Patterns</h4>
                            <p style={{ color: vendorDetail.possible_circular_trading ? '#b91c1c' : '#4b5563', fontWeight: vendorDetail.possible_circular_trading ? 'bold' : 'normal', margin: '0 0 0.5rem 0' }}>
                                {vendorDetail.possible_circular_trading ? "⚠️ Possible circular trading pattern detected" : "✓ No circular trading pattern detected"}
                            </p>
                            <p style={{ color: vendorDetail.high_risk_neighbours > 0 ? '#b91c1c' : '#4b5563', fontWeight: vendorDetail.high_risk_neighbours > 0 ? 'bold' : 'normal', margin: 0 }}>
                                {vendorDetail.high_risk_neighbours > 0 ? `⚠️ High-risk neighbouring vendors: ${vendorDetail.high_risk_neighbours}` : "✓ High-risk neighbouring vendors: 0"}
                            </p>
                        </div>

                        <h4>Suspicious Invoices</h4>
                        {vendorDetail.suspicious_invoices_details && vendorDetail.suspicious_invoices_details.length > 0 ? (
                            <div className="table-responsive">
                                <table>
                                    <thead>
                                        <tr>
                                            <th>Invoice ID</th>
                                            <th>Seller GSTIN</th>
                                            <th>Buyer GSTIN</th>
                                            <th>Amount</th>
                                            <th>Tax</th>
                                            <th>Flags</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {vendorDetail.suspicious_invoices_details.map(inv => (
                                            <tr key={inv.invoice_id}>
                                                <td>{inv.invoice_id}</td>
                                                <td>{inv.seller_gstin}</td>
                                                <td>{inv.buyer_gstin}</td>
                                                <td>{inv.amount}</td>
                                                <td>{inv.tax}</td>
                                                <td>
                                                    {inv.claimed_by_buyer && !inv.reported_by_seller
                                                        ? "claimed_only"
                                                        : ""}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : (
                            <p>No suspicious invoices found.</p>
                        )}

                        {/* AI Audit Explanation Section */}
                        <div className="ai-explanation-section" style={{ marginTop: '2rem', padding: '1.5rem', background: '#f8fafc', borderRadius: '0.5rem', border: '1px solid #e2e8f0' }}>
                            <h4>AI Audit Explanation</h4>
                            <button
                                onClick={handleGenerateAi}
                                disabled={aiLoading}
                                style={{
                                    padding: '0.5rem 1rem',
                                    backgroundColor: '#3b82f6',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '0.375rem',
                                    cursor: aiLoading ? 'not-allowed' : 'pointer',
                                    fontWeight: '600',
                                    marginBottom: '1rem'
                                }}
                            >
                                {aiLoading ? 'Generating explanation...' : 'Generate AI explanation'}
                            </button>

                            {aiError && <p className="error" style={{ marginTop: '1rem' }}>{aiError}</p>}

                            {aiExplanation && !aiLoading && !aiError && (
                                <p style={{ marginTop: '1rem', lineHeight: '1.6', color: '#334155' }}>
                                    {aiExplanation}
                                </p>
                            )}
                        </div>

                    </div>
                )}
            </div>
            </div>
            )}
        </div>
    );
}

export default App;
