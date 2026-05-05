# ============================================================================
# FabAssetsManager - errors.py
# ============================================================================
# Description: Standardized API error contract and helper functions.
# Version: 1.1.0
# ============================================================================

from enum import Enum
from datetime import datetime
from typing import Optional

from flask import has_request_context, request


class ErrorCode(Enum):
    """Standardized error codes for internal and external API usage."""

    # 4xx Client Errors
    MISSING_PARAMETER = ("MISSING_PARAMETER", 400, "Required parameter is missing")
    INVALID_REQUEST = ("INVALID_REQUEST", 400, "Request format is invalid")
    INVALID_QUERY = ("INVALID_QUERY", 400, "Query parameters are invalid or malformed")
    UNAUTHORIZED = ("UNAUTHORIZED", 401, "Authentication is required")
    FORBIDDEN = ("FORBIDDEN", 403, "Access to this resource is denied")
    NOT_FOUND = ("NOT_FOUND", 404, "Requested resource not found")
    ASSET_NOT_FOUND = ("ASSET_NOT_FOUND", 404, "Asset with the specified UID/name/URL not found")
    NO_RESULTS = ("NO_RESULTS", 404, "No results match the search criteria")

    # 5xx Server Errors
    INTERNAL_ERROR = ("INTERNAL_ERROR", 500, "An internal server error occurred")
    SERVER_UNAVAILABLE = ("SERVER_UNAVAILABLE", 503, "Server is temporarily unavailable or overloaded")
    CONNECTION_ERROR = ("CONNECTION_ERROR", 503, "Failed to connect to external service (Fab.com API)")
    TIMEOUT = ("TIMEOUT", 504, "Request timed out while fetching data")

    # Data/Cache Errors
    CACHE_ERROR = ("CACHE_ERROR", 500, "Error accessing local cache")
    DETAIL_FETCH_FAILED = ("DETAIL_FETCH_FAILED", 503, "Failed to fetch asset details from Fab.com")
    CORRUPTED_ASSET_DATA = ("CORRUPTED_ASSET_DATA", 500, "Cached asset data is corrupted or incomplete")

    def __init__(self, code: str, http_status: int, default_message: str):
        self.code = code
        self.http_status = http_status
        self.default_message = default_message


class AppError(Exception):
    """Custom exception with standardized error response structure."""

    def __init__(self, error_code: ErrorCode, message: Optional[str] = None, details: Optional[dict] = None, context: Optional[dict] = None, ):
        """
        Initialize an AppError.

        Args:
            error_code: One of the ErrorCode enum values
            message: Override default error message (optional)
            details: Additional error details dict (optional)
            context: Internal context for logging (not sent to client) (optional)
        """
        self.error_code = error_code
        self.message = message or error_code.default_message
        self.details = details or {}
        self.context = context or {}
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        super().__init__(self.message)

    def to_dict(self, include_context: bool = False) -> dict:
        """
        Convert error to JSON response dict.

        Args:
            include_context: If True, include internal context (for logging/debugging).
                            Should NOT be sent to external clients.

        Returns:
            Dict suitable for jsonify() in Flask responses
        """
        error_dict = {
            "error": {
                "code": self.error_code.code,
                "message": self.message,
                "http_status": self.error_code.http_status,
                "timestamp": self.timestamp,
            }
        }

        try:
            if has_request_context():
                error_dict["error"]["path"] = request.path
        except Exception:
            pass

        if self.details:
            error_dict["error"]["details"] = self.details

        if include_context and self.context:
            error_dict["error"]["_context"] = self.context

        return error_dict

    def get_http_status(self) -> int:
        """Return the HTTP status code for this error."""
        return self.error_code.http_status


def create_error_response(error_code: ErrorCode,
                          message: Optional[str] = None,
                          details: Optional[dict] = None,
                          context: Optional[dict] = None) -> tuple[dict, int]:
    """
    Convenience function to create (response_dict, http_status) tuple for Flask routes.

    Usage:
        return create_error_response(
            ErrorCode.ASSET_NOT_FOUND,
            message="Asset 'abc123' not found in cache",
            details={"requested_uid": "abc123"}
        )

    Returns:
        Tuple of (response_dict, http_status_code) for Flask jsonify()
    """
    app_error = AppError(error_code, message, details, context)
    return app_error.to_dict(), app_error.get_http_status()
