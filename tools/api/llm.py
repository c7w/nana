import requests
import json
import logging

def call_llm(llm_config: dict, messages: list, is_json: bool = False, plugins: list = None):
    """
    Calls the LLM API with the given configuration and messages.

    Args:
        llm_config (dict): A dictionary containing 'base_url', 'api_key', and 'model'.
        messages (list): A list of message objects for the chat completions API.
        is_json (bool): Whether to expect a JSON response from the model.
        plugins (list, optional): A list of plugins to use, e.g., for file parsing.

    Returns:
        A tuple containing:
        - dict: The 'message' part of the JSON response from the API.
        - dict: The 'usage' part of the JSON response.
        Returns (None, None) on failure.
    """
    url = f"{llm_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {llm_config['api_key']}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": llm_config['model'],
        "messages": messages
    }

    # Add max_tokens if specified in config
    if 'max_tokens' in llm_config and llm_config['max_tokens']:
        payload["max_tokens"] = llm_config['max_tokens']

    if is_json:
        payload["response_format"] = {"type": "json_object"}
    
    if plugins:
        payload["plugins"] = plugins

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        
        # Handle JSON decoding separately to log the problematic response text
        try:
            response_data = response.json()
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON response from LLM API. Error: {e}")
            logging.error(f"--- Raw Response Text ---\n{response.text}")
            return None, None

        content = response_data['choices'][0]['message'] if response_data.get('choices') else None
        usage = response_data.get('usage', {})
        return content, usage
    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling LLM API: {e}")
        return None, None
    except (KeyError, IndexError) as e:
        logging.error(f"Error parsing LLM response structure: {e}")
        logging.error(f"Raw response: {response.text}")
        return None, None 