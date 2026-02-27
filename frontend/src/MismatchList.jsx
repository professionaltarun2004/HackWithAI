import React, { useState, useEffect } from 'react';
import { getReconcileInvoices, getInvoiceAudit } from './api';

export default function MismatchList() {
    const [mismatches, setMismatches] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedInvoice, setSelectedInvoice] = useState(null);
    const [audit, setAudit] = useState(null);
    const [auditLoading, setAuditLoading] = useState(false);

    useEffect(() => {
        getReconcileInvoices()
            .then(data => { setMismatches(data); setLoading(false); })
            .catch(err => { setError(err.message); setLoading(false); });
    }, []);

    const handleSelect = (invoiceId) => {
        setSelectedInvoice(invoiceId);
        setAuditLoading(true);
        setAudit(null);
        getInvoiceAudit(invoiceId)
            .then(data => { setAudit(data); setAuditLoading(false); })
            .catch(() => { setAuditLoading(false); });
    };

    const getRiskBadgeClass = (level) => {
        if (level === 'low') return 'badge badge-low';
        if (level === 'medium') return 'badge badge-medium';
        if (level === 'high' || level === 'critical') return 'badge badge-high';
        return 'badge';
    };

    return (
        <div className="container" style={{ flexDirection: 'column' }}>
            <div className="panel" style={{ flex: 'none' }}>
                <h2>🔍 Invoice Reconciliation — Mismatches</h2>
                {loading && <p>Loading...</p>}
                {error && <p className="error">{error}</p>}
                {!loading && !error && (
                    <div className="table-responsive">
                        <table>
                            <thead>
                                <tr>
                                    <th>Invoice</th>
                                    <th>Seller</th>
                                    <th>Buyer</th>
                                    <th>Tax (₹)</th>
                                    <th>Mismatch Type</th>
                                    <th>Risk</th>
                                    <th>Score</th>
                                </tr>
                            </thead>
                            <tbody>
                                {mismatches.map(m => (
                                    <tr key={m.invoice_id}
                                        onClick={() => handleSelect(m.invoice_id)}
                                        className={selectedInvoice === m.invoice_id ? 'selected-row' : ''}
                                        style={{ cursor: 'pointer' }}>
                                        <td>{m.invoice_id}</td>
                                        <td style={{ fontSize: '0.75rem' }}>{m.seller_gstin}</td>
                                        <td style={{ fontSize: '0.75rem' }}>{m.buyer_gstin}</td>
                                        <td>{Number(m.tax).toLocaleString()}</td>
                                        <td style={{ fontSize: '0.8rem' }}>{m.mismatch_type}</td>
                                        <td><span className={getRiskBadgeClass(m.risk_level)}>{m.risk_level}</span></td>
                                        <td>{m.risk_score}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Audit trail panel */}
            {selectedInvoice && (
                <div className="panel" style={{ marginTop: '1rem' }}>
                    <h3>📋 Audit Trail — {selectedInvoice}</h3>
                    {auditLoading && <p>Loading audit trail...</p>}
                    {audit && (
                        <div>
                            <div className="stats-grid" style={{ marginBottom: '1rem' }}>
                                <div className="stat-box">
                                    <span className="stat-label">Amount</span>
                                    <span className="stat-value">₹{Number(audit.amount).toLocaleString()}</span>
                                </div>
                                <div className="stat-box">
                                    <span className="stat-label">Tax</span>
                                    <span className="stat-value">₹{Number(audit.tax).toLocaleString()}</span>
                                </div>
                                <div className="stat-box">
                                    <span className="stat-label">Risk Score</span>
                                    <span className="stat-value">{audit.risk_score}</span>
                                </div>
                                <div className="stat-box">
                                    <span className="stat-label">Risk Level</span>
                                    <span className={getRiskBadgeClass(audit.risk_level)} style={{ fontSize: '1rem' }}>{audit.risk_level}</span>
                                </div>
                            </div>

                            <h4>Traversal Steps</h4>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                {audit.trail.map(step => (
                                    <div key={step.step} style={{
                                        padding: '0.75rem 1rem',
                                        borderRadius: '0.5rem',
                                        background: step.status === 'error' ? '#fef2f2'
                                            : step.status === 'warning' ? '#fffbeb'
                                                : '#f0fdf4',
                                        border: `1px solid ${step.status === 'error' ? '#fecaca'
                                            : step.status === 'warning' ? '#fde68a'
                                                : '#bbf7d0'}`,
                                        fontSize: '0.875rem'
                                    }}>
                                        <strong>Step {step.step}:</strong> {step.description}
                                    </div>
                                ))}
                            </div>

                            <div style={{
                                marginTop: '1.5rem', padding: '1rem',
                                background: '#f8fafc', borderRadius: '0.5rem',
                                border: '1px solid #e2e8f0', lineHeight: '1.6'
                            }}>
                                <h4 style={{ marginTop: 0 }}>💡 Explanation</h4>
                                <p style={{ color: '#334155' }}>{audit.explanation}</p>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
