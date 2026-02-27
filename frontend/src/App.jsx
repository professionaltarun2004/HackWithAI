import React, { useState, useEffect } from 'react';
import GraphVisualization from './GraphVisualization';
import './index.css';

function App() {
    const [activeTab, setActiveTab] = useState('table'); // 'table' or 'graph'

    const [vendors, setVendors] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const [selectedGstin, setSelectedGstin] = useState(null);
    const [vendorDetail, setVendorDetail] = useState(null);
    const [detailLoading, setDetailLoading] = useState(false);
    const [detailError, setDetailError] = useState(null);

    // New states for AI explanation
    const [aiExplanation, setAiExplanation] = useState(null);
    const [aiLoading, setAiLoading] = useState(false);
    const [aiError, setAiError] = useState(null);

    useEffect(() => {
        fetch('http://localhost:8000/vendors')
            .then(res => {
                if (!res.ok) throw new Error('Failed to fetch vendors');
                return res.json();
            })
            .then(data => {
                setVendors(data);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, []);

    useEffect(() => {
        if (!selectedGstin) return;
        setDetailLoading(true);
        setDetailError(null);
        setAiExplanation(null);
        setAiLoading(false);
        setAiError(null);

        fetch(`http://localhost:8000/vendors/${selectedGstin}`)
            .then(res => {
                if (!res.ok) throw new Error('Failed to fetch vendor details');
                return res.json();
            })
            .then(data => {
                setVendorDetail(data);
                setDetailLoading(false);
            })
            .catch(err => {
                setDetailError(err.message);
                setDetailLoading(false);
            });
    }, [selectedGstin]);

    const handleGenerateAi = () => {
        if (!selectedGstin) return;

        setAiLoading(true);
        setAiError(null);
        setAiExplanation(null);

        fetch(`http://localhost:8000/vendors/${selectedGstin}/ai-explanation`)
            .then(res => {
                if (!res.ok) throw new Error('Failed to fetch AI explanation');
                return res.json();
            })
            .then(data => {
                setAiExplanation(data.explanation);
                setAiLoading(false);
            })
            .catch(err => {
                setAiError("Failed to generate explanation");
                setAiLoading(false);
            });
    };

    const getRiskBadgeClass = (level) => {
        if (level === 'low') return 'badge badge-low';
        if (level === 'medium') return 'badge badge-medium';
        if (level === 'high') return 'badge badge-high';
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
                        className={`tab-btn ${activeTab === 'graph' ? 'tab-active' : ''}`}
                        onClick={() => setActiveTab('graph')}
                    >
                        🔗 Transaction Graph
                    </button>
                </div>
            </nav>

            {/* Graph Tab */}
            {activeTab === 'graph' && (
                <div className="graph-page">
                    <GraphVisualization onSelectVendor={handleSelectVendorFromGraph} />
                </div>
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
