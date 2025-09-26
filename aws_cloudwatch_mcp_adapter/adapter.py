"""
Main AWS API MCP Adapter orchestration
Single Responsibility: High-level request orchestration and error handling
"""

import logging
import traceback
from typing import Dict, Any

from .config import AWSApiMCPAdapterConfig
from .mcp_client import MCPClient
from .parameter_processor import BedrockParameterProcessor
from .response_formatter import BedrockResponseFormatter
from .route_handlers import RouteRegistry
from .adapter_types import ErrorType

logger = logging.getLogger(__name__)


class AWSApiMCPAdapter:
    """Main adapter orchestrating all components for AWS API MCP Server"""

    def __init__(self,
                config: AWSApiMCPAdapterConfig,
                parameter_processor: BedrockParameterProcessor,
                mcp_client: MCPClient,
                route_registry: RouteRegistry,
                response_formatter: BedrockResponseFormatter):
        self.config = config
        self.parameter_processor = parameter_processor
        self.mcp_client = mcp_client
        self.route_registry = route_registry
        self.response_formatter = response_formatter

        logger.info("AWS API MCP Adapter initialized successfully")

    async def handle_request(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Handle Bedrock Agent request"""
        try:
            # Extract basic request info
            action_group, api_path, http_method = self.response_formatter.extract_request_info(event)

            logger.info(f"Processing request: {action_group}/{api_path} ({http_method})")

            # Process parameters
            logger.info("Starting parameter processing")
            parameters = await self._process_parameters(event)
            logger.info(f"Parameter processing completed")

            # Find and execute handler
            logger.info("Looking up handler in route registry")
            handler = self.route_registry.get_handler(api_path)
            if not handler:
                logger.warning(f"No handler found for {api_path}")
                return self._format_not_found_response(action_group, api_path, http_method)

            # Execute handler
            logger.info(f"Executing handler for '{api_path}'")
            result = await handler.handle(self.mcp_client, parameters)
            logger.info(f"Handler execution completed, result success: {result.success if hasattr(result, 'success') else 'No success attribute'}")

            # Format response
            if result.success:
                logger.info(f"Request {api_path} completed successfully")
                response = self.response_formatter.format_success_response(
                    action_group, api_path, http_method, result.data or {}
                )
                logger.info(f"Success response formatted")
                return response
            else:
                logger.error(f"Request {api_path} failed: {result.error}")
                response = self._format_handler_error_response(
                    action_group, api_path, http_method, result
                )
                logger.info(f"Error response formatted")
                return response

        except Exception as e:
            action_group = getattr(self, 'last_action_group', '')
            api_path = getattr(self, 'last_api_path', '')
            http_method = getattr(self, 'last_http_method', '')
            import traceback
            logger.error(f"Unexpected error in handle_request: {str(e)}")
            logger.error(f"Handle request traceback: {traceback.format_exc()}")
            return self._handle_unexpected_error(e, action_group, api_path, http_method)

    async def _process_parameters(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process request parameters with error handling"""
        try:
            return self.parameter_processor.process_parameters(event)
        except Exception as e:
            logger.error(f"Parameter processing failed: {str(e)}")
            raise

    def _format_not_found_response(self, action_group: str, api_path: str, http_method: str) -> Dict[str, Any]:
        """Format 404 response for unknown routes"""
        return self.response_formatter.format_error_response(
            action_group, api_path, http_method,
            f"Unknown API path: {api_path}", 404
        )

    def _format_handler_error_response(self, action_group: str, api_path: str, http_method: str, result) -> Dict[
        str, Any]:
        """Format error response based on error type"""
        status_code = self._get_status_code_for_error(result.error_type)

        # Return generic error message to Bedrock (security)
        generic_message = self._get_generic_error_message(result.error_type)

        return self.response_formatter.format_error_response(
            action_group, api_path, http_method, generic_message, status_code
        )

    def _get_status_code_for_error(self, error_type: ErrorType) -> int:
        """Map error types to HTTP status codes"""
        error_status_map = {
            ErrorType.VALIDATION_ERROR: 400,
            ErrorType.CONNECTION_ERROR: 502,
            ErrorType.MCP_SERVER_ERROR: 503,
            ErrorType.PROCESSING_ERROR: 500,
        }
        return error_status_map.get(error_type, 500)

    def _get_generic_error_message(self, error_type: ErrorType) -> str:
        """Get user-friendly error message (hide internal details)"""
        error_messages = {
            ErrorType.VALIDATION_ERROR: "Invalid request parameters",
            ErrorType.CONNECTION_ERROR: "Service temporarily unavailable",
            ErrorType.MCP_SERVER_ERROR: "External service error",
            ErrorType.PROCESSING_ERROR: "Request processing failed",
        }
        return error_messages.get(error_type, "Internal server error")

    def _handle_unexpected_error(self, error: Exception, action_group: str, api_path: str, http_method: str) -> Dict[
        str, Any]:
        """Handle unexpected exceptions with full logging"""
        logger.error(f"Unexpected error processing {api_path}: {str(error)}")
        logger.error(f"Error type: {type(error).__name__}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        return self.response_formatter.format_error_response(
            action_group, api_path, http_method, "Internal server error"
        )

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the adapter and MCP server"""
        try:
            # Check MCP server connectivity
            mcp_healthy = await self.mcp_client.health_check()

            health_status = {
                "status": "healthy" if mcp_healthy else "unhealthy",
                "mcp_server": "healthy" if mcp_healthy else "unhealthy",
                "config": {
                    "server_url": self.config.mcp_server_url,
                    "timeout": self.config.connection_timeout
                }
            }

            return health_status

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
