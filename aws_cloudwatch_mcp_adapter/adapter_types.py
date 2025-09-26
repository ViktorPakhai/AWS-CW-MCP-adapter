"""
Type definitions and data structures for AWS API MCP Adapter
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional


class ErrorType(Enum):
    """Error categories for better error handling"""
    VALIDATION_ERROR = "validation_error"
    CONNECTION_ERROR = "connection_error"
    MCP_SERVER_ERROR = "mcp_server_error"
    PROCESSING_ERROR = "processing_error"


@dataclass
class MCPResponse:
    """Standardized response structure for MCP operations"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None

    @classmethod
    def success_response(cls, data: Dict[str, Any]) -> 'MCPResponse':
        """Create a successful response"""
        return cls(success=True, data=data)

    @classmethod
    def error_response(cls, error: str, error_type: ErrorType) -> 'MCPResponse':
        """Create an error response"""
        return cls(success=False, error=error, error_type=error_type)
