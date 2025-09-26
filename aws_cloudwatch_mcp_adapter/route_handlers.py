"""
Route handlers for AWS API MCP endpoints
Single Responsibility: Each handler manages one specific route type
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from .mcp_client import MCPClient
from .adapter_types import MCPResponse

logger = logging.getLogger(__name__)


class RouteHandler(ABC):
    """Abstract base class for route handlers"""

    @abstractmethod
    async def handle(self, mcp_client: MCPClient, parameters: Dict[str, Any]) -> MCPResponse:
        """Handle the route request"""
        pass


class ListToolsHandler(RouteHandler):
    """Handler for listing available MCP tools"""

    async def handle(self, mcp_client: MCPClient, parameters: Dict[str, Any]) -> MCPResponse:
        """List all available tools from MCP server"""
        logger.info("Handling list tools request")
        return await mcp_client.connect_and_execute("list_tools")


class ToolCallHandler(RouteHandler):
    """Handler for calling specific MCP tools"""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name

    async def handle(self, mcp_client: MCPClient, parameters: Dict[str, Any]) -> MCPResponse:
        """Call specific MCP tool with provided parameters"""
        logger.info(f"Handling tool call for '{self.tool_name}'")
        try:
            return await mcp_client.connect_and_execute("call_tool", {
                "tool_name": self.tool_name,
                "arguments": parameters
            })
        except Exception as e:
            logger.error(f"ToolCallHandler error for {self.tool_name}: {str(e)}")
            from .adapter_types import MCPResponse, ErrorType
            return MCPResponse.error_response(f"Tool execution failed: {str(e)}", ErrorType.PROCESSING_ERROR)


class HealthCheckHandler(RouteHandler):
    """Handler for health checks"""

    async def handle(self, mcp_client: MCPClient, parameters: Dict[str, Any]) -> MCPResponse:
        """Perform health check on MCP server"""
        logger.info("Handling health check request")
        is_healthy = await mcp_client.health_check()

        if is_healthy:
            return MCPResponse.success_response({"status": "healthy", "timestamp": parameters.get("timestamp")})
        else:
            return MCPResponse.error_response("MCP server unhealthy", "HEALTH_CHECK_FAILED")


# Open/Closed: Easy to add new route handlers without modifying existing code
class RouteRegistry:
    """Registry for API routes and their handlers"""

    def __init__(self):
        self._routes: Dict[str, RouteHandler] = {
            "/describe-log-groups": ToolCallHandler("describe_log_groups"),
            "/analyze-log-group": ToolCallHandler("analyze_log_group"),
            "/get-metric-data": ToolCallHandler("get_metric_data"),
            "/get-metric-metadata": ToolCallHandler("get_metric_metadata"),
            "/get-recommended-metric-alarms": ToolCallHandler("get_recommended_metric_alarms"),
            "/get-active-alarms": ToolCallHandler("get_active_alarms"),
            "/get-alarm-history": ToolCallHandler("get_alarm_history"),
            "/list-tools": ListToolsHandler(),
            "/health": ListToolsHandler(),
        }

        logger.info(f"Initialized route registry with {len(self._routes)} routes")

    def get_handler(self, api_path: str) -> Optional[RouteHandler]:
        """Get handler for API path"""
        # Normalize path - remove actionGroup prefix and handle both formats
        normalized_path = api_path.replace("CloudWatchMCP//", "").replace("CloudWatchMCP/", "").lstrip("/")
        if not normalized_path.startswith("/"):
            normalized_path = "/" + normalized_path
            
        handler = self._routes.get(api_path) or self._routes.get(normalized_path)
        if handler:
            logger.debug(f"Found handler for {api_path}/{normalized_path}: {type(handler).__name__}")
        else:
            logger.warning(f"No handler found for {api_path} or {normalized_path}")
            logger.debug(f"Available routes: {list(self._routes.keys())}")
        return handler

    def add_route(self, api_path: str, handler: RouteHandler):
        """Add new route (for future extensibility)"""
        self._routes[api_path] = handler
        logger.info(f"Added new route: {api_path} -> {type(handler).__name__}")

    def list_routes(self) -> Dict[str, str]:
        """List all registered routes"""
        return {path: type(handler).__name__ for path, handler in self._routes.items()}

    def remove_route(self, api_path: str) -> bool:
        """Remove a route"""
        if api_path in self._routes:
            del self._routes[api_path]
            logger.info(f"Removed route: {api_path}")
            return True
        return False
