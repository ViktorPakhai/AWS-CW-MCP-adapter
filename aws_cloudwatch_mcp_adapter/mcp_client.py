"""
MCP client module for AWS API MCP Server communication
Single Responsibility: Handles all MCP server communication
"""

import asyncio
import logging
import aiohttp
import uuid
from typing import Dict, Any, Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .config import AWSApiMCPAdapterConfig
from .adapter_types import MCPResponse, ErrorType

logger = logging.getLogger(__name__)


class MCPClient:
    """Handles AWS API MCP server communication with proper JSON-RPC support"""

    def __init__(self, config: AWSApiMCPAdapterConfig):
        self.config = config

    async def connect_and_execute(self, tool_name: str, parameters: Optional[Dict[str, Any]] = None) -> MCPResponse:
        """
        Execute tool call using HTTP/JSON-RPC endpoint
        """
        endpoint_map = {
            "describe_log_groups": "/describe-log-groups",
            "analyze_log_group": "/analyze-log-group",
            "get_metric_data": "/get-metric-data",
            "get_metric_metadata": "/get-metric-metadata",
            "get_recommended_metric_alarms": "/get-recommended-metric-alarms",
            "get_active_alarms": "/get-active-alarms",
            "get_alarm_history": "/get-alarm-history"
        }
        
        path = endpoint_map.get(tool_name)
        if path:
            return await self.call_jsonrpc_http_endpoint(tool_name, parameters)
        else:
            # Fallback for list_tools or unknown operations
            logger.info(f"Tool '{tool_name}' not in endpoint map, using legacy protocol")
            return await self._connect_and_execute_legacy(tool_name, parameters)

    async def get_session_id(self, session_url, headers, timeout):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(session_url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("session_id")
                    else:
                        logger.error(f"Failed to get session ID: {await resp.text()}")
                        return None
        except Exception as e:
            logger.error(f"Exception in get_session_id: {str(e)}")
            return None        

    async def call_jsonrpc_http_endpoint(self, tool_name: str, parameters: Optional[Dict[str, Any]] = None) -> MCPResponse:
        """Call the HTTP/JSON-RPC endpoint for REST-style tools with required initialize handshake."""
        endpoint_map = {
            "describe_log_groups": "/describe-log-groups",
            "analyze_log_group": "/analyze-log-group",
            "get_metric_data": "/get-metric-data",
            "get_metric_metadata": "/get-metric-metadata",
            "get_recommended_metric_alarms": "/get-recommended-metric-alarms",
            "get_active_alarms": "/get-active-alarms",
            "get_alarm_history": "/get-alarm-history",
        }
        path = endpoint_map.get(tool_name)
        if not path:
            logger.error(f"Tool '{tool_name}' is not mapped to an endpoint")
            return MCPResponse.error_response(
                f"Unknown tool: {tool_name}",
                ErrorType.VALIDATION_ERROR
            )
        url = self.config.mcp_server_url.rstrip("/") + path
        session_url = self.config.mcp_server_url.rstrip("/") + "/session"
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json"
        }
        timeout = aiohttp.ClientTimeout(total=self.config.connection_timeout)

        # Step 1: Get a valid session id
        session_id = await self.get_session_id(session_url, headers, timeout)
        if not session_id:
            logger.error("Could not obtain valid session id from MCP /session endpoint.")
            return MCPResponse.error_response(
                "Could not obtain valid session id from MCP /session endpoint.",
                ErrorType.CONNECTION_ERROR
            )

        # Step 2: Initialize handshake
        initialize_body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2.0",
                "capabilities": {},
                "clientInfo": {"name": "aws-cloudwatch-mcp-adapter", "version": "1.0"}
            }
        }
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url, json=initialize_body, headers={**headers, "mcp-session-id": session_id}
                ) as init_resp:
                    try:
                        init_data = await init_resp.json()
                    except Exception:
                        init_data = await init_resp.text()
                    if init_resp.status != 200:
                        logger.error(f"Failed MCP initialize: {init_data}")
                        return MCPResponse.error_response(
                            "Failed MCP initialize",
                            ErrorType.MCP_SERVER_ERROR
                        )
                    logger.info("MCP session initialized successfully")

                # Step 3: Actual tool call
                tool_body = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": parameters or {}
                    }
                }
                async with session.post(
                    url, json=tool_body, headers={**headers, "mcp-session-id": session_id}
                ) as resp:
                    try:
                        data = await resp.json()
                    except Exception:
                        data = await resp.text()
                    if resp.status == 200:
                        logger.info(f"Received success response from MCP server for {tool_name}")
                        return MCPResponse.success_response(data)
                    else:
                        logger.error(f"MCP server returned error: {data}")
                        return MCPResponse.error_response(
                            data.get("error", "Unknown error") if isinstance(data, dict) else str(data),
                            ErrorType.MCP_SERVER_ERROR
                        )
        except Exception as e:
            logger.error(f"Error connecting to MCP server: {str(e)}")
            return MCPResponse.error_response(
                f"Connection error: {str(e)}",
                ErrorType.CONNECTION_ERROR
            )

    async def _connect_and_execute_legacy(self, action: str, parameters: Optional[Dict[str, Any]] = None) -> MCPResponse:
        """
        Legacy MCP protocol support for list_tools and generic call_tool
        Uses the streamable HTTP client from MCP SDK
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Using legacy MCP protocol for action: {action}")
        mcp_url = self.config.mcp_server_url
        
        try:
            async with streamablehttp_client(
                    mcp_url,
                    headers=headers,
                    timeout=self.config.connection_timeout
            ) as (read, write, _):
                logger.info("Legacy protocol client connected successfully")
                
                async with ClientSession(read, write) as session:
                    try:
                        logger.info("Initializing legacy protocol session")
                        await asyncio.wait_for(session.initialize(), timeout=5.0)
                        logger.info("Legacy protocol session initialized")
                        
                        if action == "list_tools":
                            return await self._list_tools(session)
                        elif action == "call_tool":
                            return await self._call_tool(session, parameters)
                        else:
                            logger.error(f"Unknown legacy action: {action}")
                            return MCPResponse.error_response(
                                f"Unknown action: {action}",
                                ErrorType.VALIDATION_ERROR
                            )
                    
                    except asyncio.TimeoutError:
                        logger.error("Legacy protocol session initialization timed out")
                        return MCPResponse.error_response(
                            "Session initialization timeout",
                            ErrorType.CONNECTION_ERROR
                        )
        
        except Exception as e:
            logger.error(f"Error in legacy protocol: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return MCPResponse.error_response(
                f"Legacy protocol error: {str(e)}",
                ErrorType.CONNECTION_ERROR
            )

    async def _list_tools(self, session: ClientSession) -> MCPResponse:
        """List available tools from MCP server"""
        try:
            logger.info("Calling session.list_tools()")
            response = await session.list_tools()
            logger.info(f"Received {len(response.tools)} tools from MCP server")
            
            tools_data = {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description or "No description",
                        "input_schema": tool.inputSchema
                    }
                    for tool in response.tools
                ]
            }
            
            logger.info(f"Successfully listed {len(tools_data['tools'])} tools")
            return MCPResponse.success_response(tools_data)
        
        except Exception as e:
            logger.error(f"Error listing tools: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return MCPResponse.error_response(
                "Failed to list tools from MCP server",
                ErrorType.MCP_SERVER_ERROR
            )

    async def _call_tool(self, session: ClientSession, parameters: Optional[Dict[str, Any]]) -> MCPResponse:
        """Call a tool using legacy MCP protocol"""
        try:
            logger.info(f"Legacy _call_tool called with parameters: {parameters}")
            
            if not parameters or "tool_name" not in parameters:
                logger.error("Tool name missing from parameters")
                return MCPResponse.error_response(
                    "Tool name is required",
                    ErrorType.VALIDATION_ERROR
                )

            tool_name = parameters["tool_name"]
            tool_args = parameters.get("arguments", {})

            logger.info(f"Calling legacy protocol tool '{tool_name}' with args: {tool_args}")
            result = await session.call_tool(tool_name, arguments=tool_args)
            logger.info(f"Legacy tool call completed. Result type: {type(result)}")
            
            if result and result.content:
                response_data = {
                    "content": [{"text": content.text} for content in result.content]
                }
                logger.info(f"Legacy tool response has {len(result.content)} content items")
            else:
                response_data = {"content": []}
                logger.warning("Legacy tool response has no content")

            return MCPResponse.success_response(response_data)
        
        except Exception as e:
            logger.error(f"Error calling legacy tool: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return MCPResponse.error_response(
                "Tool execution failed on MCP server",
                ErrorType.MCP_SERVER_ERROR
            )

    async def health_check(self) -> bool:
        """
        Perform health check on the MCP server
        Uses describe_log_groups as a simple health check
        """
        try:
            logger.info("Starting health check")
            result = await self.connect_and_execute("describe_log_groups", {
                "ctx": {
                    "request_id": "health-check",
                    "source": "health"
                },
                "region": "us-east-1",
                "max_items": 1
            })
            
            is_healthy = result.success
            logger.info(f"Health check completed: {'healthy' if is_healthy else 'unhealthy'}")
            return is_healthy
        
        except Exception as e:
            logger.error(f"Health check failed with exception: {str(e)}")
            return False