"""
Bedrock parameter processing module for AWS API MCP
Single Responsibility: Converts Bedrock Agent parameters to MCP format
"""

import logging
from typing import Dict, Any, List, Callable

logger = logging.getLogger(__name__)


class BedrockParameterProcessor:
    """Processes Bedrock Agent parameters into MCP format for AWS API calls"""

    TYPE_CONVERTERS: Dict[str, Callable[[str], Any]] = {
        'max_results': int,
        'max_items': int,
        'timeout': int,
        'retries': int,
    }

    BOOLEAN_FIELDS = {
        'dry_run',
        'include_all',
        'include_linked_accounts',
        'recursive',
        'force',
        'verbose'
    }

    def process_parameters(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process Bedrock event parameters into clean dictionary with MCP context"""
        try:
            params_dict = {}

            # Process query parameters
            parameters = event.get('parameters', [])
            if parameters:
                self._process_parameter_list(parameters, params_dict)

            # Process request body (Bedrock Agent format)
            request_body = event.get('requestBody', {})
            if request_body:
                self._process_request_body(request_body, params_dict)

            # Add required MCP context if not present
            if 'ctx' not in params_dict:
                params_dict['ctx'] = self._create_default_context(event)

            logger.info(f"Processed parameters with context: {params_dict}")
            return params_dict

        except Exception as e:
            logger.error(f"Parameter processing error: {str(e)}")
            raise

    def _create_default_context(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create default MCP context object required by CloudWatch MCP server
        
        The Context schema typically includes:
        - request_id: Unique identifier for the request
        - source: Where the request came from
        - timestamp: When the request was made
        """
        import time
        
        context = {
            "request_id": event.get('requestId', event.get('messageId', f"req-{int(time.time())}")),
            "source": "bedrock-agent",
            "session_id": event.get('sessionId', 'default-session'),
            "agent_id": event.get('agent', {}).get('id', 'unknown-agent')
        }
        
        logger.info(f"Created default MCP context: {context}")
        return context

    def _process_parameter_list(self, parameters: List[Dict], params_dict: Dict[str, Any]):
        """Process list of parameter objects"""
        for param in parameters:
            if isinstance(param, dict) and 'name' in param and 'value' in param:
                self._convert_and_store_param(param['name'], param['value'], params_dict)

    def _process_request_body(self, request_body: Dict[str, Any], params_dict: Dict[str, Any]):
        """Process Bedrock request body content"""
        content = request_body.get('content', {})
        json_content = content.get('application/json')

        if not json_content:
            return

        # Handle Bedrock's nested properties format
        if isinstance(json_content, dict) and 'properties' in json_content:
            properties_list = json_content['properties']
            if isinstance(properties_list, list):
                self._process_parameter_list(properties_list, params_dict)
            else:
                logger.warning(f"Properties is not a list: {type(properties_list)}")

        # Handle direct list format
        elif isinstance(json_content, list):
            self._process_parameter_list(json_content, params_dict)

        else:
            logger.warning(f"Unexpected json_content format: {type(json_content)}")

    def _convert_and_store_param(self, name: str, value: Any, params_dict: Dict[str, Any]):
        """Convert parameter value to appropriate type and store"""
        if name in self.TYPE_CONVERTERS:
            try:
                params_dict[name] = self.TYPE_CONVERTERS[name](value)
            except (ValueError, TypeError):
                logger.warning(
                    f"Failed to convert {name}={value} to {self.TYPE_CONVERTERS[name].__name__}, keeping original")
                params_dict[name] = value
        elif name in self.BOOLEAN_FIELDS:
            params_dict[name] = self._convert_to_boolean(value)
        else:
            params_dict[name] = value

    def _convert_to_boolean(self, value: Any) -> Any:
        """Convert string boolean representations to actual booleans"""
        if isinstance(value, str):
            if value.lower() in ['true', '1', 'yes']:
                return True
            elif value.lower() in ['false', '0', 'no']:
                return False
        return value

    def add_type_converter(self, field_name: str, converter: Callable[[str], Any]):
        """Add custom type converter (for extensibility)"""
        self.TYPE_CONVERTERS[field_name] = converter

    def add_boolean_field(self, field_name: str):
        """Add field to boolean conversion list"""
        self.BOOLEAN_FIELDS.add(field_name)
