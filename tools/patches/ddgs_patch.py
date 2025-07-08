import functools
from ddgs import DDGS
import logging

def apply_ddgs_patch():
    """
    Applies a monkey patch to the DDGS class to redirect bing.com searches
    to cn.bing.com, which can be more reliable in certain regions.
    """
    logging.info("--- Applying DDGS patch to redirect to cn.bing.com ---")

    # Keep a reference to the original _get_url method
    original_get_url = DDGS._get_url

    # Use functools.wraps to preserve the original function's metadata
    @functools.wraps(original_get_url)
    def patched_get_url(self, method, url, **kwargs):
        # The core of our patch: check and replace the domain
        if "bing.com" in url:
            original_url = url
            url = url.replace("www.bing.com", "cn.bing.com")
            logging.info(f"DDGS patch active: Redirecting '{original_url}' to '{url}'")
        
        # Call the original method with the (potentially modified) URL
        return original_get_url(self, method, url, **kwargs)

    # Replace the original method on the class with our patched version
    DDGS._get_url = patched_get_url
    logging.info("--- DDGS patch applied successfully. ---") 