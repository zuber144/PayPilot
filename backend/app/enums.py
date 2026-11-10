"""Shared enums. Values are frozen by the contract (work-division doc section 2.2)."""

from enum import StrEnum


class GoalStatus(StrEnum):
    RUNNING = "RUNNING"
    NEEDS_INPUT = "NEEDS_INPUT"
    PLAN_READY = "PLAN_READY"
    FAILED = "FAILED"


class PlanStatus(StrEnum):
    DRAFT = "DRAFT"
    CHECKED = "CHECKED"
    USER_APPROVED = "USER_APPROVED"
    PAYING = "PAYING"
    PAID = "PAID"
    FAILED = "FAILED"


class Verdict(StrEnum):
    APPROVED = "APPROVED"
    REVIEW = "REVIEW"
    BLOCKED = "BLOCKED"


class RuleOutcome(StrEnum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class OfferStatus(StrEnum):
    OPEN = "OPEN"
    COUNTERED = "COUNTERED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SELECTED = "SELECTED"


class TraceStatus(StrEnum):
    OK = "OK"
    RETRY = "RETRY"
    FALLBACK = "FALLBACK"
    ERROR = "ERROR"


class TraceNode(StrEnum):
    ORCHESTRATOR = "orchestrator"
    GOAL = "goal"
    DISCOVERY = "discovery"
    PROVIDER = "provider"
    NEGOTIATION = "negotiation"
    PLANNING = "planning"
    PAYGUARD = "payguard"


class TxnStatus(StrEnum):
    CREATED = "CREATED"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Action(StrEnum):
    """Permitted orchestrator actions (work-division doc 3.3)."""

    DISCOVER = "discover"
    RETRY_DISCOVERY = "retry_discovery"
    CONTINUE_WITH_MINIMUM = "continue_with_minimum"
    ASK_USER = "ask_user"
    NEGOTIATE = "negotiate"
    PLAN = "plan"
    REVISE_PLAN = "revise_plan"
    PAYGUARD = "payguard"


class RuleId(StrEnum):
    BUDGET_CAP = "BUDGET_CAP"
    TXN_LIMIT = "TXN_LIMIT"
    VERIFIED_PROVIDER = "VERIFIED_PROVIDER"
    CURRENCY_MATCH = "CURRENCY_MATCH"
    NO_DUPLICATE = "NO_DUPLICATE"
    PRICE_FLOOR = "PRICE_FLOOR"
    TOTAL_INTEGRITY = "TOTAL_INTEGRITY"
    AI_RISK_HIGH = "AI_RISK_HIGH"
    AI_RISK_MEDIUM = "AI_RISK_MEDIUM"
    SINGLE_VENDOR_SHARE = "SINGLE_VENDOR_SHARE"


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    PLAN_NOT_APPROVED = "PLAN_NOT_APPROVED"
    DUPLICATE_PAYMENT = "DUPLICATE_PAYMENT"
    PAYPAL_ERROR = "PAYPAL_ERROR"
    PAYMENTS_DISABLED = "PAYMENTS_DISABLED"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class Scenario(StrEnum):
    CLEAN = "clean"
    RETRY = "retry"
    BLOCKED = "blocked"
    REVIEW = "review"
