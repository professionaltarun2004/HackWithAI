import React, { useState, useEffect } from 'react';
import { getVendors, getVendorRisk } from './api';

export default function VendorRiskBoard() {
    const [vendors, setVendors] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedGstin, setSelectedGstin] = useState(null);
    const [riskDetail, setRiskDetail] = useState(null);
    const [detailLoading, setDetailLoading] = useState(false);

    useEffect(() => {
        getVendors()
            .then(data => { setVendors(data); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    const handleSelect = (gstin) => {
        setSelectedGstin(gstin);
        setDetailLoading(true);
        setRiskDetail(null);
        getVendorRisk(gstin)
            .then(data => { setRiskDetail(data); setDetailLoading(false); })
            .catch(() => setDetailLoading(false));
    };

    const getRiskBadgeClass = (level) => {
        if (level === 'low') return 'badge badge-low';
        if (level === 'medium') return 'badge badge-medium';
        return 'badge badge-high';
    };

    const barStyle = (score) => ({
        height: '8px',
        width: `${score}%`,
        background: score >= 50 ? '#ef4444' : score >= 25 ? '#f59e0b' : '#22c55e',
        borderRadius: '4px',
        transition: 'width 0.3s',
    });

    return (
        <div className="container">
            <div className="left-panel panel">
                <h2>🏆 Vendor Risk Leaderboard</h2>
                {loading ? <p>Loading...</p> : (
                    <div className="table-responsive">
                        <table>
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Vendor</th>
                                    <th>Risk</th>
                                    <th>Score</th>
                                    <th style={{ minWidth: '80px' }}>Bar</th>
                                </tr>
                            </thead>
                            <tbody>
                                {vendors.map((v, i) => (
                                    <tr key={v.gstin}
                                        onClick={() => handleSelect(v.gstin)}
                                        className={selectedGstin === v.gstin ? 'selected-row' : ''}
                                        style={{ cursor: 'pointer' }}>
                                        <td>{i + 1}</td>
                                        <td>
                                            <div style={{ fontWeight: 600 }}>{v.name}</div>
                                            <div style={{ fontSize: '0.7rem', color: '#64748b' }}>{v.gstin}</div>
                                        </td>
                                        <td><span className={getRiskBadgeClass(v.risk_level)}>{v.risk_level}</span></td>
                                        <td>{v.risk_score}</td>
                                        <td>
                                            <div style={{ background: '#e2e8f0', borderRadius: '4px', height: '8px' }}>
                                                <div style={barStyle(v.risk_score)} />
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <div className="right-panel panel">
                <h2>Vendor Risk Detail</h2>
                {!selectedGstin && <p className="placeholder">Select a vendor to see risk breakdown.</p>}
                {detailLoading && <p>Loading...</p>}
                {riskDetail && !detailLoading && (
                    <div className="detail-content">
                        <div className="detail-header">
                            <h3>{riskDetail.name}</h3>
                            <span className={getRiskBadgeClass(riskDetail.risk_level)}>
                                {riskDetail.risk_level} — {riskDetail.risk_score}/100
                            </span>
                        </div>

                        <div className="stats-grid">
                            <div className="stat-box">
                                <span className="stat-label">Compliance</span>
                                <span className="stat-value">{riskDetail.compliance_score}%</span>
                            </div>
                            <div className="stat-box">
                                <span className="stat-label">Missed Filings</span>
                                <span className="stat-value">{riskDetail.missed_filings}</span>
                            </div>
                            <div className="stat-box">
                                <span className="stat-label">Suspicious</span>
                                <span className="stat-value">{riskDetail.suspicious_invoice_count}</span>
                            </div>
                            <div className="stat-box">
                                <span className="stat-label">Incoming</span>
                                <span className="stat-value">{riskDetail.total_incoming}</span>
                            </div>
                        </div>

                        <h4>Risk Factors</h4>
                        {riskDetail.reasons && riskDetail.reasons.length > 0 ? (
                            <ul style={{ paddingLeft: '1.2rem', lineHeight: '1.8' }}>
                                {riskDetail.reasons.map((r, i) => (
                                    <li key={i} style={{ color: '#334155' }}>{r}</li>
                                ))}
                            </ul>
                        ) : (
                            <p style={{ color: '#64748b' }}>No risk factors found — vendor is compliant.</p>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
