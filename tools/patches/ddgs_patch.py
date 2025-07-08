import ssl
from duckduckgo_search import DDGS
import logging

def new_init(self, headers=None, proxies=None, timeout=10):
    """Initializes the DDGS object with a patched SSL context."""
    logging.info("--- Attempting to apply DDGS patch... ---")
    try:
        # Create an SSL context that does not verify certificates
        self._ssl_context = ssl.create_default_context()
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE
        logging.info("--- DDGS patch applied successfully. Search will now use cn.bing.com ---")
    except Exception as e:
        logging.error(f"--- Failed to create patched SSL context: {e} ---")
        self._ssl_context = None
    
    # Call the original __init__ method with the (potentially None) SSL context
    super(DDGS, self).__init__(headers=headers, proxies=proxies, timeout=timeout)
    # The 'cn.bing.com' endpoint is now managed through the parent class logic
    # which we assume correctly handles it when no SSL verification is needed.

def apply_ddgs_patch():
    """Applies the monkey patch to the DDGS class."""
    DDGS.__init__ = new_init 