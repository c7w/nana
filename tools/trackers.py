"""
This module provides utility functions for tracking API usage and costs.
"""

def update_usage(usage_tracker: dict, llm_config: dict, usage: dict):
    """
    Updates the usage tracker with token counts and calculated cost.
    """
    if not usage:
        return

    model_name = llm_config['model']
    if model_name not in usage_tracker:
        usage_tracker[model_name] = {'input': 0, 'output': 0, 'cost_usd': 0.0}
    
    prompt_tokens = usage.get('prompt_tokens', 0)
    completion_tokens = usage.get('completion_tokens', 0)
    
    usage_tracker[model_name]['input'] += prompt_tokens
    usage_tracker[model_name]['output'] += completion_tokens
    
    # Calculate cost from config (cost per 1M tokens)
    input_cost_per_m = llm_config.get('cost', {}).get('input', 0)
    output_cost_per_m = llm_config.get('cost', {}).get('output', 0)
    
    cost = ((prompt_tokens / 1_000_000) * input_cost_per_m) + \
           ((completion_tokens / 1_000_000) * output_cost_per_m)
    
    usage_tracker[model_name]['cost_usd'] += cost 