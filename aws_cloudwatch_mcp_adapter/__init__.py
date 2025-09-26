"""
AWS API MCP Adapter Package
SOLID-compliant AWS Bedrock Agent to AWS API MCP Server adapter
"""

from .adapter import AWSApiMCPAdapter
from .config import AWSApiMCPAdapterConfig, ConfigurationError
from .factory import AWSApiMCPAdapterFactory, SingletonAdapterManager, create_aws_api_mcp_adapter
from .mcp_client import MCPClient
from .parameter_processor import BedrockParameterProcessor
from .response_formatter import BedrockResponseFormatter
from .route_handlers import RouteHandler, RouteRegistry, ListToolsHandler, ToolCallHandler
from .adapter_types import MCPResponse, ErrorType

__version__ = "1.0.0"
__author__ = "AWS API MCP Adapter Team"
__description__ = "SOLID-compliant AWS API MCP adapter for AWS Bedrock Agent"

# Main exports for easy importing
__all__ = [
    # Core classes
    'AWSApiMCPAdapter',
    'AWSApiMCPAdapterConfig',
    'MCPResponse',
    'ErrorType',

    # Components
    'BedrockParameterProcessor',
    'MCPClient',
    'RouteHandler',
    'RouteRegistry',
    'BedrockResponseFormatter',

    # Handlers
    'ListToolsHandler',
    'ToolCallHandler',

    # Factory and utilities
    'AWSApiMCPAdapterFactory',
    'SingletonAdapterManager',
    'create_aws_api_mcp_adapter',

    # Exceptions
    'ConfigurationError',
]

# Package-level configuration
import logging

# Set up package logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())  # Prevent "No handlers found" message
