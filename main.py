import uvicorn
import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from app.api import app
from app.logger import get_logger
from config import settings

logger = get_logger(__name__)


def main():
    """Main application entry point."""
    try:
        logger.info("Starting chatbot application", version=settings.app_version)
        
        # Run the application
        uvicorn.run(
            "app.api:app",
            host=settings.host,
            port=settings.port,
            workers=settings.workers if not settings.debug else 1,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error("Application failed to start", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()