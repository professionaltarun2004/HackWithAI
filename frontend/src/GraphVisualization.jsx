import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';

const RISK_COLORS = {
    high: '#ef4444',
    medium: '#f59e0b',
    low: '#22c55e',
};

const RISK_BG = {
    high: 'rgba(239,68,68,0.12)',
    medium: 'rgba(245,158,11,0.12)',
    low: 'rgba(34,197,94,0.12)',
};

export default function GraphVisualization({ onSelectVendor }) {
    const svgRef = useRef(null);
    const containerRef = useRef(null);
    const simulationRef = useRef(null);
    const [graphData, setGraphData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [tooltip, setTooltip] = useState({ visible: false, x: 0, y: 0, node: null });
    const [selectedNode, setSelectedNode] = useState(null);
    const [filter, setFilter] = useState('all'); // all, vendors, suspicious

    useEffect(() => {
        fetch('http://localhost:8000/graph')
            .then(res => {
                if (!res.ok) throw new Error('Failed to fetch graph data');
                return res.json();
            })
            .then(data => {
                setGraphData(data);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, []);

    const getFilteredData = useCallback(() => {
        if (!graphData) return null;
        if (filter === 'all') return graphData;

        let filteredNodes = [...graphData.nodes];
        if (filter === 'suspicious') {
            // Show only vendors and suspicious invoices (and their edges)
            const suspiciousIds = new Set(
                graphData.nodes.filter(n => n.type === 'invoice' && n.is_suspicious).map(n => n.id)
            );
            const vendorIds = new Set(graphData.nodes.filter(n => n.type === 'vendor').map(n => n.id));
            const relevantIds = new Set([...suspiciousIds, ...vendorIds]);
            filteredNodes = graphData.nodes.filter(n => relevantIds.has(n.id));
            const filteredEdges = graphData.edges.filter(
                e => relevantIds.has(e.source) && relevantIds.has(e.target)
            );
            return { nodes: filteredNodes, edges: filteredEdges };
        }
        if (filter === 'vendors') {
            filteredNodes = graphData.nodes.filter(n => n.type === 'vendor');
            return { nodes: filteredNodes, edges: [] };
        }
        return graphData;
    }, [graphData, filter]);

    useEffect(() => {
        const data = getFilteredData();
        if (!data || !svgRef.current) return;

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const container = containerRef.current;
        const width = container ? container.clientWidth : 1000;
        const height = 600;

        svg.attr('viewBox', `0 0 ${width} ${height}`)
           .attr('width', '100%')
           .attr('height', height);

        // Arrow marker
        const defs = svg.append('defs');
        defs.append('marker')
            .attr('id', 'arrowhead')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 22)
            .attr('refY', 0)
            .attr('markerWidth', 7)
            .attr('markerHeight', 7)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#64748b');

        defs.append('marker')
            .attr('id', 'arrowhead-suspicious')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 16)
            .attr('refY', 0)
            .attr('markerWidth', 7)
            .attr('markerHeight', 7)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#f87171');

        // Drop shadow filter
        const dropShadow = defs.append('filter')
            .attr('id', 'drop-shadow')
            .attr('x', '-30%').attr('y', '-30%')
            .attr('width', '160%').attr('height', '160%');
        dropShadow.append('feGaussianBlur')
            .attr('in', 'SourceAlpha').attr('stdDeviation', 3);
        dropShadow.append('feOffset').attr('dx', 0).attr('dy', 2);
        dropShadow.append('feComponentTransfer')
            .append('feFuncA').attr('type', 'linear').attr('slope', 0.3);
        const merge = dropShadow.append('feMerge');
        merge.append('feMergeNode');
        merge.append('feMergeNode').attr('in', 'SourceGraphic');

        // Glow filter for suspicious
        const glow = defs.append('filter').attr('id', 'glow');
        glow.append('feGaussianBlur').attr('stdDeviation', 4).attr('result', 'coloredBlur');
        const glowMerge = glow.append('feMerge');
        glowMerge.append('feMergeNode').attr('in', 'coloredBlur');
        glowMerge.append('feMergeNode').attr('in', 'SourceGraphic');

        const g = svg.append('g');

        // Zoom
        const zoom = d3.zoom()
            .scaleExtent([0.15, 5])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });
        svg.call(zoom);

        const nodes = data.nodes.map(d => ({ ...d }));
        const links = data.edges.map(d => ({ ...d }));

        // Build lookup for suspicious edges
        const nodeMap = {};
        nodes.forEach(n => { nodeMap[n.id] = n; });

        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(d => {
                // Longer distance for vendor-to-vendor paths
                return 120;
            }))
            .force('charge', d3.forceManyBody().strength(-400))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(d => d.type === 'vendor' ? 40 : 20))
            .force('x', d3.forceX(width / 2).strength(0.05))
            .force('y', d3.forceY(height / 2).strength(0.05));

        simulationRef.current = simulation;

        // Draw edges
        const link = g.selectAll('.link')
            .data(links)
            .join('line')
            .attr('class', 'link')
            .attr('stroke', d => {
                const sourceNode = typeof d.source === 'object' ? d.source : nodeMap[d.source];
                const targetNode = typeof d.target === 'object' ? d.target : nodeMap[d.target];
                if (sourceNode && sourceNode.is_suspicious) return '#f87171';
                if (targetNode && targetNode.is_suspicious) return '#f87171';
                return '#475569';
            })
            .attr('stroke-width', d => {
                const sourceNode = typeof d.source === 'object' ? d.source : nodeMap[d.source];
                const targetNode = typeof d.target === 'object' ? d.target : nodeMap[d.target];
                if ((sourceNode && sourceNode.is_suspicious) || (targetNode && targetNode.is_suspicious)) return 2;
                return 1.2;
            })
            .attr('stroke-opacity', 0.6)
            .attr('marker-end', d => {
                const sourceNode = typeof d.source === 'object' ? d.source : nodeMap[d.source];
                const targetNode = typeof d.target === 'object' ? d.target : nodeMap[d.target];
                if ((sourceNode && sourceNode.is_suspicious) || (targetNode && targetNode.is_suspicious))
                    return 'url(#arrowhead-suspicious)';
                return 'url(#arrowhead)';
            });

        // Draw nodes
        const node = g.selectAll('.node')
            .data(nodes)
            .join('g')
            .attr('class', 'node')
            .style('cursor', 'pointer')
            .call(d3.drag()
                .on('start', (event, d) => {
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                })
                .on('drag', (event, d) => {
                    d.fx = event.x;
                    d.fy = event.y;
                })
                .on('end', (event, d) => {
                    if (!event.active) simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                })
            );

        // Vendor nodes (rounded rectangles)
        node.filter(d => d.type === 'vendor')
            .append('rect')
            .attr('x', -24)
            .attr('y', -24)
            .attr('width', 48)
            .attr('height', 48)
            .attr('rx', 10)
            .attr('ry', 10)
            .attr('fill', d => RISK_COLORS[d.risk_level] || '#94a3b8')
            .attr('stroke', '#fff')
            .attr('stroke-width', 2.5)
            .attr('filter', 'url(#drop-shadow)');

        // Vendor icon (building emoji as text)
        node.filter(d => d.type === 'vendor')
            .append('text')
            .text('🏢')
            .attr('text-anchor', 'middle')
            .attr('dy', 6)
            .attr('font-size', 18)
            .attr('pointer-events', 'none');

        // Invoice nodes (circles)
        node.filter(d => d.type === 'invoice')
            .append('circle')
            .attr('r', d => d.is_suspicious ? 12 : 8)
            .attr('fill', d => d.is_suspicious ? '#fca5a5' : '#93c5fd')
            .attr('stroke', d => d.is_suspicious ? '#ef4444' : '#60a5fa')
            .attr('stroke-width', d => d.is_suspicious ? 2.5 : 1.5)
            .attr('filter', d => d.is_suspicious ? 'url(#glow)' : null);

        // Suspicious indicator
        node.filter(d => d.type === 'invoice' && d.is_suspicious)
            .append('text')
            .text('⚠')
            .attr('text-anchor', 'middle')
            .attr('dy', 4)
            .attr('font-size', 10)
            .attr('pointer-events', 'none');

        // Vendor name labels
        node.filter(d => d.type === 'vendor')
            .append('text')
            .text(d => d.name || d.id)
            .attr('text-anchor', 'middle')
            .attr('dy', -32)
            .attr('font-size', 11)
            .attr('font-weight', '600')
            .attr('fill', '#1e293b')
            .attr('pointer-events', 'none')
            .attr('paint-order', 'stroke')
            .attr('stroke', '#fff')
            .attr('stroke-width', 3);

        // Invoice ID labels (smaller, only on hover via CSS)
        node.filter(d => d.type === 'invoice')
            .append('text')
            .attr('class', 'invoice-label')
            .text(d => d.id)
            .attr('text-anchor', 'middle')
            .attr('dy', -16)
            .attr('font-size', 8)
            .attr('fill', '#64748b')
            .attr('pointer-events', 'none')
            .attr('opacity', 0);

        // Hover effects
        node.on('mouseenter', function (event, d) {
            d3.select(this).select('rect, circle')
                .transition().duration(200)
                .attr('stroke-width', 4);

            // Show invoice label
            d3.select(this).select('.invoice-label')
                .transition().duration(200)
                .attr('opacity', 1);

            // Highlight connected edges
            link.attr('stroke-opacity', l => {
                const sId = typeof l.source === 'object' ? l.source.id : l.source;
                const tId = typeof l.target === 'object' ? l.target.id : l.target;
                return (sId === d.id || tId === d.id) ? 1 : 0.15;
            }).attr('stroke-width', l => {
                const sId = typeof l.source === 'object' ? l.source.id : l.source;
                const tId = typeof l.target === 'object' ? l.target.id : l.target;
                return (sId === d.id || tId === d.id) ? 3 : 1;
            });

            // Dim other nodes
            node.attr('opacity', n => {
                if (n.id === d.id) return 1;
                // Check if connected
                const connected = links.some(l => {
                    const sId = typeof l.source === 'object' ? l.source.id : l.source;
                    const tId = typeof l.target === 'object' ? l.target.id : l.target;
                    return (sId === d.id && tId === n.id) || (tId === d.id && sId === n.id);
                });
                return connected ? 1 : 0.25;
            });

            // Tooltip
            const rect = svgRef.current.getBoundingClientRect();
            setTooltip({
                visible: true,
                x: event.clientX - rect.left + 15,
                y: event.clientY - rect.top - 10,
                node: d,
            });
        })
        .on('mousemove', function (event) {
            const rect = svgRef.current.getBoundingClientRect();
            setTooltip(prev => ({
                ...prev,
                x: event.clientX - rect.left + 15,
                y: event.clientY - rect.top - 10,
            }));
        })
        .on('mouseleave', function () {
            d3.select(this).select('rect, circle')
                .transition().duration(200)
                .attr('stroke-width', d => d.type === 'vendor' ? 2.5 : (d.is_suspicious ? 2.5 : 1.5));

            d3.select(this).select('.invoice-label')
                .transition().duration(200)
                .attr('opacity', 0);

            link.attr('stroke-opacity', 0.6)
                .attr('stroke-width', d => {
                    const sourceNode = typeof d.source === 'object' ? d.source : nodeMap[d.source];
                    const targetNode = typeof d.target === 'object' ? d.target : nodeMap[d.target];
                    if ((sourceNode && sourceNode.is_suspicious) || (targetNode && targetNode.is_suspicious)) return 2;
                    return 1.2;
                });

            node.attr('opacity', 1);

            setTooltip({ visible: false, x: 0, y: 0, node: null });
        })
        .on('click', function (event, d) {
            setSelectedNode(d);
            if (d.type === 'vendor' && onSelectVendor) {
                onSelectVendor(d.id);
            }
        });

        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node.attr('transform', d => `translate(${d.x},${d.y})`);
        });

        // Zoom to fit after simulation settles
        simulation.on('end', () => {
            const bounds = g.node().getBBox();
            const fullWidth = width;
            const fullHeight = height;
            const bWidth = bounds.width;
            const bHeight = bounds.height;
            const scale = 0.85 / Math.max(bWidth / fullWidth, bHeight / fullHeight);
            const tx = fullWidth / 2 - scale * (bounds.x + bWidth / 2);
            const ty = fullHeight / 2 - scale * (bounds.y + bHeight / 2);

            svg.transition().duration(750).call(
                zoom.transform,
                d3.zoomIdentity.translate(tx, ty).scale(scale)
            );
        });

        return () => {
            simulation.stop();
        };
    }, [getFilteredData]);

    const renderTooltipContent = () => {
        if (!tooltip.node) return null;
        const d = tooltip.node;

        if (d.type === 'vendor') {
            return (
                <div className="graph-tooltip-inner">
                    <div className="graph-tooltip-title">🏢 {d.name}</div>
                    <div className="graph-tooltip-row"><span>GSTIN:</span> <span>{d.id}</span></div>
                    <div className="graph-tooltip-row">
                        <span>Risk:</span>
                        <span className={`badge badge-${d.risk_level}`}>{d.risk_level}</span>
                    </div>
                    <div className="graph-tooltip-row"><span>Score:</span> <span className="tooltip-score">{d.risk_score}</span></div>
                    <div className="graph-tooltip-row"><span>Missed Filings:</span> <span>{d.missed_filings}</span></div>
                    <div className="graph-tooltip-row"><span>Suspicious Invoices:</span> <span style={{ color: d.suspicious_count > 0 ? '#ef4444' : '#22c55e' }}>{d.suspicious_count}</span></div>
                    <div className="graph-tooltip-hint">Click to view details</div>
                </div>
            );
        }

        return (
            <div className="graph-tooltip-inner">
                <div className="graph-tooltip-title">
                    {d.is_suspicious ? '⚠️' : '📄'} Invoice {d.id}
                </div>
                <div className="graph-tooltip-row"><span>Amount:</span> <span>₹{d.amount?.toLocaleString()}</span></div>
                <div className="graph-tooltip-row"><span>Tax:</span> <span>₹{d.tax?.toLocaleString()}</span></div>
                <div className="graph-tooltip-row"><span>Seller:</span> <span>{d.seller_gstin}</span></div>
                <div className="graph-tooltip-row"><span>Buyer:</span> <span>{d.buyer_gstin}</span></div>
                <div className="graph-tooltip-row">
                    <span>Reported by Seller:</span>
                    <span style={{ color: d.reported_by_seller ? '#22c55e' : '#ef4444' }}>
                        {d.reported_by_seller ? '✅ Yes' : '❌ No'}
                    </span>
                </div>
                <div className="graph-tooltip-row">
                    <span>Claimed by Buyer:</span>
                    <span style={{ color: d.claimed_by_buyer ? '#f59e0b' : '#64748b' }}>
                        {d.claimed_by_buyer ? '⚡ Yes' : '— No'}
                    </span>
                </div>
                {d.is_suspicious && (
                    <div className="graph-tooltip-warning">
                        ⚠️ SUSPICIOUS — Claimed by buyer but NOT reported by seller
                    </div>
                )}
            </div>
        );
    };

    // Stats summary
    const stats = graphData ? {
        vendors: graphData.nodes.filter(n => n.type === 'vendor').length,
        invoices: graphData.nodes.filter(n => n.type === 'invoice').length,
        suspicious: graphData.nodes.filter(n => n.type === 'invoice' && n.is_suspicious).length,
        highRisk: graphData.nodes.filter(n => n.type === 'vendor' && n.risk_level === 'high').length,
    } : null;

    return (
        <div className="graph-container">
            <div className="graph-header">
                <h2>🔗 Vendor–Invoice Transaction Graph</h2>
                <p className="graph-subtitle">Interactive visualization of all transactions. Hover nodes for details, drag to rearrange, scroll to zoom.</p>
            </div>

            {/* Stats Bar */}
            {stats && (
                <div className="graph-stats-bar">
                    <div className="graph-stat">
                        <span className="graph-stat-num">{stats.vendors}</span>
                        <span className="graph-stat-label">Vendors</span>
                    </div>
                    <div className="graph-stat">
                        <span className="graph-stat-num">{stats.invoices}</span>
                        <span className="graph-stat-label">Invoices</span>
                    </div>
                    <div className="graph-stat graph-stat-warning">
                        <span className="graph-stat-num">{stats.suspicious}</span>
                        <span className="graph-stat-label">Suspicious</span>
                    </div>
                    <div className="graph-stat graph-stat-danger">
                        <span className="graph-stat-num">{stats.highRisk}</span>
                        <span className="graph-stat-label">High Risk</span>
                    </div>
                </div>
            )}

            {/* Filter buttons */}
            <div className="graph-filters">
                <button className={`graph-filter-btn ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>
                    All Nodes
                </button>
                <button className={`graph-filter-btn ${filter === 'suspicious' ? 'active' : ''}`} onClick={() => setFilter('suspicious')}>
                    ⚠ Suspicious Only
                </button>
                <button className={`graph-filter-btn ${filter === 'vendors' ? 'active' : ''}`} onClick={() => setFilter('vendors')}>
                    🏢 Vendors Only
                </button>
            </div>

            {loading && <p className="graph-loading">Loading graph data...</p>}
            {error && <p className="error">{error}</p>}

            {!loading && !error && (
                <div className="graph-svg-wrapper" ref={containerRef}>
                    <svg ref={svgRef} />

                    {tooltip.visible && tooltip.node && (
                        <div
                            className="graph-tooltip"
                            style={{
                                left: tooltip.x,
                                top: tooltip.y,
                            }}
                        >
                            {renderTooltipContent()}
                        </div>
                    )}
                </div>
            )}

            {/* Legend */}
            <div className="graph-legend">
                <span className="graph-legend-title">Legend:</span>
                <div className="graph-legend-item">
                    <span className="graph-legend-icon" style={{ background: '#22c55e', borderRadius: 4 }} />
                    Low Risk
                </div>
                <div className="graph-legend-item">
                    <span className="graph-legend-icon" style={{ background: '#f59e0b', borderRadius: 4 }} />
                    Medium Risk
                </div>
                <div className="graph-legend-item">
                    <span className="graph-legend-icon" style={{ background: '#ef4444', borderRadius: 4 }} />
                    High Risk
                </div>
                <div className="graph-legend-item">
                    <span className="graph-legend-icon" style={{ background: '#93c5fd', borderRadius: '50%' }} />
                    Normal Invoice
                </div>
                <div className="graph-legend-item">
                    <span className="graph-legend-icon" style={{ background: '#fca5a5', borderRadius: '50%', border: '2px solid #ef4444' }} />
                    Suspicious Invoice
                </div>
            </div>

            {/* Selected node detail panel */}
            {selectedNode && (
                <div className="graph-selected-panel">
                    <div className="graph-selected-header">
                        <h4>{selectedNode.type === 'vendor' ? '🏢' : '📄'} {selectedNode.name || selectedNode.id}</h4>
                        <button className="graph-close-btn" onClick={() => setSelectedNode(null)}>✕</button>
                    </div>
                    {selectedNode.type === 'vendor' ? (
                        <div className="graph-selected-body">
                            <div className="graph-detail-row"><span>GSTIN</span><span>{selectedNode.id}</span></div>
                            <div className="graph-detail-row"><span>Risk Level</span><span className={`badge badge-${selectedNode.risk_level}`}>{selectedNode.risk_level}</span></div>
                            <div className="graph-detail-row"><span>Risk Score</span><span>{selectedNode.risk_score}</span></div>
                            <div className="graph-detail-row"><span>Missed Filings</span><span>{selectedNode.missed_filings}</span></div>
                            <div className="graph-detail-row"><span>Suspicious Invoices</span><span>{selectedNode.suspicious_count}</span></div>
                            {onSelectVendor && (
                                <button className="graph-detail-link" onClick={() => onSelectVendor(selectedNode.id)}>
                                    View Full Details →
                                </button>
                            )}
                        </div>
                    ) : (
                        <div className="graph-selected-body">
                            <div className="graph-detail-row"><span>Invoice ID</span><span>{selectedNode.id}</span></div>
                            <div className="graph-detail-row"><span>Amount</span><span>₹{selectedNode.amount?.toLocaleString()}</span></div>
                            <div className="graph-detail-row"><span>Tax</span><span>₹{selectedNode.tax?.toLocaleString()}</span></div>
                            <div className="graph-detail-row"><span>Seller</span><span>{selectedNode.seller_gstin}</span></div>
                            <div className="graph-detail-row"><span>Buyer</span><span>{selectedNode.buyer_gstin}</span></div>
                            <div className="graph-detail-row">
                                <span>Reported by Seller</span>
                                <span style={{ color: selectedNode.reported_by_seller ? '#22c55e' : '#ef4444' }}>
                                    {selectedNode.reported_by_seller ? 'Yes' : 'No'}
                                </span>
                            </div>
                            <div className="graph-detail-row">
                                <span>Claimed by Buyer</span>
                                <span style={{ color: selectedNode.claimed_by_buyer ? '#f59e0b' : '#64748b' }}>
                                    {selectedNode.claimed_by_buyer ? 'Yes' : 'No'}
                                </span>
                            </div>
                            {selectedNode.is_suspicious && (
                                <div className="graph-suspicious-alert">
                                    ⚠️ This invoice was claimed by the buyer but NOT reported by the seller — potential ITC fraud
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
