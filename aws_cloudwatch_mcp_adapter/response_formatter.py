"""
Response formatting for AWS Bedrock Agent
Single Responsibility: Formats responses according to Bedrock Agent specification
"""

import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BedrockResponseFormatter:
    """Formats responses for Bedrock Agent consumption"""

    MESSAGE_VERSION = "1.0"

    @classmethod
    def format_success_response(
            cls,
            action_group: str,
            api_path: str,
            http_method: str,
            data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format successful response for Bedrock Agent"""
        response = {
            "messageVersion": cls.MESSAGE_VERSION,
            "response": {
                "actionGroup": action_group,
                "apiPath": api_path,
                "httpMethod": http_method,
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps(data, separators=(',', ':'))  # Compact JSON
                    }
                }
            }
        }

        logger.debug(f"Formatted success response for {api_path}")
        return response

    @classmethod
    def format_error_response(
            cls,
            action_group: str,
            api_path: str,
            http_method: str,
            error_message: str,
            status_code: int = 500
    ) -> Dict[str, Any]:
        """Format error response for Bedrock Agent"""
        response = {
            "messageVersion": cls.MESSAGE_VERSION,
            "response": {
                "actionGroup": action_group,
                "apiPath": api_path,
                "httpMethod": http_method,
                "httpStatusCode": status_code,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({"error": error_message}, separators=(',', ':'))
                    }
                }
            }
        }

        logger.debug(f"Formatted error response for {api_path} (status: {status_code})")
        return response

    @classmethod
    def format_validation_error_response(
            cls,
            action_group: str,
            api_path: str,
            http_method: str,
            validation_errors: Dict[str, str]
    ) -> Dict[str, Any]:
        """Format validation error response with field-specific errors"""
        error_data = {
            "error": "Validation failed",
            "validation_errors": validation_errors
        }

        return cls.format_error_response(
            action_group, api_path, http_method,
            json.dumps(error_data), 400
        )

    @classmethod
    def extract_request_info(cls, event: Dict[str, Any]) -> tuple[str, str, str]:
        """Extract basic request information from Bedrock event"""
        action_group = event.get('actionGroup', '')
        api_path = event.get('apiPath', '')
        http_method = event.get('httpMethod', '')

        return action_group, api_path, http_method

    @classmethod
    def add_metadata(cls, response: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Add metadata to response (for debugging/monitoring)"""
        if 'metadata' not in response['response']:
            response['response']['metadata'] = {}

        response['response']['metadata'].update(metadata)
        return response
