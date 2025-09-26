"""
Configuration management for AWS API MCP Adapter
Single Responsibility: Handles all configuration loading and validation
"""

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid"""
    pass


@dataclass
class AWSApiMCPAdapterConfig:
    """Configuration container for AWS API MCP Adapter"""
    mcp_server_url: str
    connection_timeout: int
    tool_timeout: int
    max_retries: int
    log_level: str

    @classmethod
    def from_environment(cls) -> 'AWSApiMCPAdapterConfig':
        """Create configuration from environment variables"""
        config = cls(
            mcp_server_url=cls._get_required_env("MCP_SERVER_URL"),
            connection_timeout=int(os.getenv("MCP_CONNECTION_TIMEOUT", "10")),
            tool_timeout=int(os.getenv("MCP_TOOL_TIMEOUT", "30")),
            max_retries=int(os.getenv("MCP_MAX_RETRIES", "3")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper()
        )

        # Validate configuration
        config._validate()

        # Set log level
        logger.setLevel(getattr(logging, config.log_level))

        return config

    def _validate(self):
        """Validate configuration values"""
        if not self.mcp_server_url.startswith(('http://', 'https://')):
            raise ConfigurationError("MCP_SERVER_URL must be a valid HTTP/HTTPS URL")

        if self.connection_timeout <= 0:
            raise ConfigurationError("MCP_CONNECTION_TIMEOUT must be positive")

        if self.tool_timeout <= 0:
            raise ConfigurationError("MCP_TOOL_TIMEOUT must be positive")

        if self.log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ConfigurationError(f"LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL")

    @staticmethod
    def _get_required_env(key: str) -> str:
        """Get required environment variable or raise error"""
        value = os.getenv(key)
        if not value:
            raise ConfigurationError(f"Required environment variable {key} not set")
        return value
