"""
AWS Lambda entry point for AWS API MCP Adapter
Clean, focused Lambda handler with modular architecture
"""

import asyncio
import logging
from typing import Dict, Any

# Import all components from our modular architecture
from aws_cloudwatch_mcp_adapter.config import ConfigurationError
from aws_cloudwatch_mcp_adapter.factory import SingletonAdapterManager
from aws_cloudwatch_mcp_adapter.response_formatter import BedrockResponseFormatter

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for Bedrock Agent action group

    This is the main entry point that:
    1. Gets/creates the singleton adapter instance
    2. Delegates request handling to the adapter
    3. Handles any configuration or unexpected errors
    """
    try:
        logger.info(f"Lambda handler started with event: {event.get('actionGroup', '')}/{event.get('apiPath', '')}")
        
        # Get singleton adapter instance (efficient for Lambda)
        adapter = SingletonAdapterManager.get_adapter()

        # Delegate to adapter with fast timeout for Lambda -> MCP timeout issues
        response = asyncio.run(asyncio.wait_for(
            adapter.handle_request(event, context),
            timeout=20.0  # Fast global timeout for Lambda function
        ))
        logger.info(f"Lambda handler completed successfully")
        return response

    except ConfigurationError as e:
        logger.error(f"Configuration error: {str(e)}")
        return _create_configuration_error_response(event, str(e))

    except asyncio.TimeoutError as e:
        logger.error(f"Lambda timeout waiting for adapter response: {str(e)}")
        return _create_fatal_error_response(event, "Function timeout reaching MCP server")

    except Exception as e:
        logger.error(f"Fatal error in lambda_handler: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return _create_fatal_error_response(event, str(e))


def _create_configuration_error_response(event: Dict[str, Any], error_message: str) -> Dict[str, Any]:
    """Create response for configuration errors"""
    action_group = event.get('actionGroup', '')
    api_path = event.get('apiPath', '')
    http_method = event.get('httpMethod', '')

    return BedrockResponseFormatter.format_error_response(
        action_group, api_path, http_method,
        "Service configuration error", 500
    )


def _create_fatal_error_response(event: Dict[str, Any], error_message: str) -> Dict[str, Any]:
    """Create response for fatal errors"""
    action_group = event.get('actionGroup', '')
    api_path = event.get('apiPath', '')
    http_method = event.get('httpMethod', '')

    return BedrockResponseFormatter.format_error_response(
        action_group, api_path, http_method,
        "Internal server error", 500
    )


# Health check endpoint (if needed for monitoring)
async def health_check() -> Dict[str, Any]:
    """Standalone health check function"""
    try:
        adapter = SingletonAdapterManager.get_adapter()
        return await adapter.health_check()
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}