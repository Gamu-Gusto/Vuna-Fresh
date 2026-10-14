"""
Custom DRF exception handler — returns a consistent JSON shape for all errors:
  {
    "error": {
      "code": "validation_error",
      "message": "...",
      "detail": { ... }   # field-level errors when present
    }
  }
"""
from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError, AuthenticationFailed, NotAuthenticated
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled exception", exc_info=exc)
        return Response(
            {"error": {"code": "server_error", "message": "An unexpected error occurred."}},
            status=500,
        )

    if isinstance(exc, ValidationError):
        return Response(
            {
                "error": {
                    "code": "validation_error",
                    "message": "Invalid input.",
                    "detail": response.data,
                }
            },
            status=response.status_code,
        )

    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        return Response(
            {"error": {"code": "authentication_error", "message": str(exc.detail)}},
            status=response.status_code,
        )

    # Generic fallback for other DRF exceptions
    return Response(
        {
            "error": {
                "code": "error",
                "message": response.data.get("detail", str(response.data))
                if isinstance(response.data, dict)
                else str(response.data),
            }
        },
        status=response.status_code,
    )
