"""
Factory for creating configured AWS API MCP Adapter
Dependency Inversion: Handles all dependency injection and wiring
"""

import logging
from typing import Optional

from .adapter import AWSApiMCPAdapter
from .config import AWSApiMCPAdapterConfig, ConfigurationError
from .mcp_client import MCPClient
from .parameter_processor import BedrockParameterProcessor
from .response_formatter import BedrockResponseFormatter
from .route_handlers import RouteRegistry

logger = logging.getLogger(__name__)


class AWSApiMCPAdapterFactory:
    """Factory for creating fully configured AWS API MCP adapter instances"""

    @staticmethod
    def create_adapter() -> AWSApiMCPAdapter:
        """Create fully configured AWS API MCP adapter with all dependencies"""
        try:
            # Create configuration
            config = AWSApiMCPAdapterConfig.from_environment()
            logger.info(f"Loaded configuration: {config.mcp_server_url}")

            # Create components
            parameter_processor = BedrockParameterProcessor()
            mcp_client = MCPClient(config)
            route_registry = RouteRegistry()
            response_formatter = BedrockResponseFormatter()

            # Create main adapter
            adapter = AWSApiMCPAdapter(
                config=config,
                parameter_processor=parameter_processor,
                mcp_client=mcp_client,
                route_registry=route_registry,
                response_formatter=response_formatter
            )

            logger.info("AWS API MCP Adapter factory created adapter successfully")
            return adapter

        except ConfigurationError as e:
            logger.error(f"Configuration error during factory creation: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during factory creation: {str(e)}")
            raise

    @staticmethod
    def create_test_adapter(mcp_server_url: str = None) -> AWSApiMCPAdapter:
        """Create adapter for testing with optional server URL override"""
        import os

        if mcp_server_url:
            os.environ['MCP_SERVER_URL'] = mcp_server_url

        return AWSApiMCPAdapterFactory.create_adapter()

    @staticmethod
    def create_custom_adapter(
            config: AWSApiMCPAdapterConfig,
            parameter_processor: BedrockParameterProcessor = None,
            mcp_client: MCPClient = None,
            route_registry: RouteRegistry = None,
            response_formatter: BedrockResponseFormatter = None
    ) -> AWSApiMCPAdapter:
        """Create adapter with custom components (for advanced usage)"""

        # Use provided components or create defaults
        parameter_processor = parameter_processor or BedrockParameterProcessor()
        mcp_client = mcp_client or MCPClient(config)
        route_registry = route_registry or RouteRegistry()
        response_formatter = response_formatter or BedrockResponseFormatter()

        return AWSApiMCPAdapter(
            config=config,
            parameter_processor=parameter_processor,
            mcp_client=mcp_client,
            route_registry=route_registry,
            response_formatter=response_formatter
        )


# Singleton pattern for Lambda efficiency
class SingletonAdapterManager:
    """Manages singleton adapter instance for Lambda efficiency"""

    _instance: Optional[AWSApiMCPAdapter] = None

    @classmethod
    def get_adapter(cls) -> AWSApiMCPAdapter:
        """Get or create adapter instance"""
        if cls._instance is None:
            cls._instance = AWSApiMCPAdapterFactory.create_adapter()
            logger.info("Created singleton AWS API MCP Adapter instance")
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (useful for testing)"""
        cls._instance = None
        logger.debug("Reset singleton AWS API MCP Adapter instance")

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if singleton instance exists"""
        return cls._instance is not None


# Convenience function for backward compatibility
def create_aws_api_mcp_adapter() -> AWSApiMCPAdapter:
    """Create AWS API MCP adapter - convenience function"""
    return AWSApiMCPAdapterFactory.create_adapter()
