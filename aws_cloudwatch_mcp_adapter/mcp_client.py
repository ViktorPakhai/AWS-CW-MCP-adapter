"""
MCP client module for AWS API MCP Server communication
Single Responsibility: Handles all MCP server communication
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .config import AWSApiMCPAdapterConfig
from .adapter_types import MCPResponse, ErrorType

logger = logging.getLogger(__name__)


class MCPClient:
    """Handles AWS API MCP server communication"""

    def __init__(self, config: AWSApiMCPAdapterConfig):
        self.config = config

    async def connect_and_execute(self, action: str, parameters: Optional[Dict[str, Any]] = None) -> MCPResponse:
        """Execute MCP action with proper error handling and timeout"""
        logger.info(f"Starting MCP connect_and_execute with action '{action}' and parameters {parameters}")
        try:
            # Apply timeout wrapper for safety
            return await asyncio.wait_for(
                self._connect_and_execute_inner(action, parameters),
                timeout=self.config.connection_timeout + 5  # Add small buffer
            )
        except asyncio.TimeoutError:
            logger.error(f"MCP operation timed out after {self.config.connection_timeout + 5} seconds")
            return MCPResponse.error_response(
                "MCP session timeout",
                ErrorType.CONNECTION_ERROR
            )
        except Exception as e:
            logger.error(f"MCP Client error in connect_and_execute: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return MCPResponse.error_response(
                "Failed to communicate with AWS API MCP server",
                ErrorType.CONNECTION_ERROR
            )

    async def _connect_and_execute_inner(self, action: str, parameters: Optional[Dict[str, Any]] = None) -> MCPResponse:
        """Inner connection execution with detailed logging"""
        # Add minimal headers required for MCP protocol
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        logger.info(f"Connecting to MCP server: {self.config.mcp_server_url}")
        logger.info(f"Using headers for protocol negotiation: {headers}")

        # Try to handle URL correctly - if it ends with /mcp/, streamablehttp_client should add it
        mcp_url = self.config.mcp_server_url
        if mcp_url.endswith("/mcp/"):
            logger.info(f"URL ends with /mcp/, this might cause double path issue")
        
        async with streamablehttp_client(
                mcp_url,
                headers=headers,
                timeout=self.config.connection_timeout
        ) as (read, write, _):
            logger.info("HTTP client connected successfully")
            logger.info(f"Starting ClientSession with read/write streams")
            async with ClientSession(read, write) as session:
                try:
                    logger.info(f"Starting MCP session initialization with {self.config.mcp_server_url}")
                    # Add explicit timeout for session initialization
                    await asyncio.wait_for(
                        session.initialize(), 
                        timeout=5.0  # Very short timeout for init
                    )
                    logger.info("MCP session initialized successfully")

                    if action == "list_tools":
                        logger.info("Executing list_tools action")
                        result = await self._list_tools(session)
                        logger.info(f"List tools action completed with success: {result.success}")
                        return result
                    elif action == "call_tool":
                        logger.info("Executing call_tool action")
                        result = await self._call_tool(session, parameters)
                        logger.info(f"Call tool action completed with success: {result.success}")
                        return result
                    else:
                        logger.error(f"Unknown action requested: {action}")
                        return MCPResponse.error_response(
                            f"Unknown action: {action}",
                            ErrorType.VALIDATION_ERROR
                        )
                except asyncio.TimeoutError:
                    logger.error("MCP session initialization timed out - trying faster fallback")
                    return MCPResponse.error_response(
                        "Session initialization timeout - server may be slow",
                        ErrorType.CONNECTION_ERROR
                    )

    async def _list_tools(self, session: ClientSession) -> MCPResponse:
        """List available tools from AWS API MCP server"""
        try:
            response = await session.list_tools()
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
            return MCPResponse.success_response(tools_data)

        except Exception as e:
            logger.error(f"Error listing tools: {str(e)}")
            return MCPResponse.error_response(
                "Failed to list tools from AWS API MCP server",
                ErrorType.MCP_SERVER_ERROR
            )

    async def _call_tool(self, session: ClientSession, parameters: Optional[Dict[str, Any]]) -> MCPResponse:
        """Call a specific tool on the AWS API MCP server"""
        try:
            logger.info(f"_call_tool method called with parameters: {parameters}")
            
            if not parameters or "tool_name" not in parameters:
                logger.error("Tool name missing from parameters")
                return MCPResponse.error_response(
                    "Tool name is required",
                    ErrorType.VALIDATION_ERROR
                )

            tool_name = parameters["tool_name"]
            tool_args = parameters.get("arguments", {})

            logger.info(f"Preparing to call AWS API MCP tool '{tool_name}' with arguments: {tool_args}")
            logger.info(f"About to execute session.call_tool for '{tool_name}'")

            result = await session.call_tool(tool_name, arguments=tool_args)
            logger.info(f"MCP tool call completed. Result type: {type(result)}")

            if result and result.content:
                response_data = {
                    "content": [{"text": content.text} for content in result.content]
                }
                logger.info(f"Tool response data populated with {len(result.content)} content items")
            else:
                response_data = {"content": []}
                logger.info("Tool response data empty - no content found")

            logger.info(f"AWS API MCP tool '{tool_name}' executed successfully")
            return MCPResponse.success_response(response_data)

        except Exception as e:
            logger.error(f"Error calling AWS API MCP tool: {str(e)}")
            import traceback
            logger.error(f"Tool call traceback: {traceback.format_exc()}")
            return MCPResponse.error_response(
                "Tool execution failed on AWS API MCP server",
                ErrorType.MCP_SERVER_ERROR
            )

    async def health_check(self) -> bool:
        """Perform a health check on the AWS API MCP server"""
        try:
            result = await self.connect_and_execute("list_tools")
            return result.success
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
