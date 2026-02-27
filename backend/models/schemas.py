"""
Pydantic models / schemas for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# ── Enums ──────────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MismatchType(str, Enum):
    CLAIMED_NOT_REPORTED = "Claimed by buyer but not reported by seller"
    REPORTED_NOT_CLAIMED = "Reported by seller but not claimed by buyer"
    BOTH_MISSING = "Neither reported nor claimed"
    CIRCULAR_TRADE = "Circular trading pattern detected"
    VENDOR_MISSED_FILINGS = "Vendor has missed return filings"
    MATCHED = "Matched"


# ── Vendor ─────────────────────────────────────────────────

class VendorBasic(BaseModel):
    gstin: str
    name: str
    missed_filings: int = 0
    total_incoming: int = 0
    total_outgoing: int = 0


class VendorRisk(BaseModel):
    gstin: str
    name: str
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    missed_filings: int = 0
    total_incoming: int = 0
    total_outgoing: int = 0
    suspicious_invoice_count: int = 0
    compliance_score: int = Field(ge=0, le=100, default=100)
    reasons: List[str] = []


# ── Invoice ────────────────────────────────────────────────

class InvoiceBasic(BaseModel):
    invoice_id: str
    seller_gstin: str
    buyer_gstin: str
    amount: float
    tax: float
    reported_by_seller: bool
    claimed_by_buyer: bool


class InvoiceMismatch(BaseModel):
    invoice_id: str
    seller_gstin: str
    buyer_gstin: str
    amount: float
    tax: float
    reported_by_seller: bool
    claimed_by_buyer: bool
    mismatch_type: MismatchType
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel


# ── Audit Trail ────────────────────────────────────────────

class AuditTrailStep(BaseModel):
    step: int
    description: str
    status: str  # "ok", "warning", "error"


class InvoiceAuditTrail(BaseModel):
    invoice_id: str
    seller_gstin: str
    seller_name: str
    buyer_gstin: str
    buyer_name: str
    amount: float
    tax: float
    reported_by_seller: bool
    claimed_by_buyer: bool
    mismatch_type: MismatchType
    risk_score: int
    risk_level: RiskLevel
    trail: List[AuditTrailStep]
    explanation: str


# ── Graph Summary ──────────────────────────────────────────

class GraphSummary(BaseModel):
    vendor_count: int = 0
    invoice_count: int = 0
    mismatch_count: int = 0
    suspicious_count: int = 0
    circular_chains: int = 0
    top_risky_vendors: List[VendorRisk] = []


# ── API Responses ──────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    graph_backend: str
    vendor_count: int = 0
    invoice_count: int = 0


class IngestResponse(BaseModel):
    status: str
    vendors_loaded: int
    invoices_loaded: int
