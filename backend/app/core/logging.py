import logging
import sys

def setup_logging():
    """
    Configures standard structured logging for the application,
    setting appropriate levels and formatting.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Silence verbose dependency libraries
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("pinecone").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
