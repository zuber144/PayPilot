"""API error type. main.py renders every ApiError as the contract error envelope:
{"error": {"code": ..., "message": ...}}
"""

from app.enums import ErrorCode

_STATUS = {
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.PLAN_NOT_APPROVED: 409,
    ErrorCode.DUPLICATE_PAYMENT: 409,
    ErrorCode.CONFLICT: 409,
    ErrorCode.PAYPAL_ERROR: 502,
    ErrorCode.PAYMENTS_DISABLED: 503,
    ErrorCode.INTERNAL_ERROR: 500,
}


class ApiError(Exception):
    def __init__(self, code: ErrorCode, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code or _STATUS.get(code, 400)
