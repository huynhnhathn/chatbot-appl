from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from typing import Dict, Any
import time
import psutil
import threading
from datetime import datetime, timedelta
from app.logger import get_logger
from config import settings

logger = get_logger(__name__)


class MetricsCollector:
    """Collects and manages application metrics."""
    
    def __init__(self):
        # Request metrics
        self.request_counter = Counter(
            'chatbot_requests_total',
            'Total number of requests',
            ['method', 'endpoint', 'status']
        )
        
        self.request_duration = Histogram(
            'chatbot_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint']
        )
        
        # Chat metrics
        self.chat_requests = Counter(
            'chatbot_chat_requests_total',
            'Total number of chat requests'
        )
        
        self.chat_responses = Counter(
            'chatbot_chat_responses_total',
            'Total number of chat responses'
        )
        
        self.tokens_used = Counter(
            'chatbot_tokens_used_total',
            'Total number of tokens used'
        )
        
        self.api_cost = Counter(
            'chatbot_api_cost_total',
            'Total API cost in USD'
        )
        
        # System metrics
        self.active_sessions = Gauge(
            'chatbot_active_sessions',
            'Number of active sessions'
        )
        
        self.memory_usage = Gauge(
            'chatbot_memory_usage_bytes',
            'Memory usage in bytes'
        )
        
        self.cpu_usage = Gauge(
            'chatbot_cpu_usage_percent',
            'CPU usage percentage'
        )
        
        # Error metrics
        self.error_counter = Counter(
            'chatbot_errors_total',
            'Total number of errors',
            ['error_type']
        )
        
        # Initialize metrics
        self.start_time = datetime.utcnow()
        self._start_system_metrics_collection()
    
    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record request metrics."""
        self.request_counter.labels(method=method, endpoint=endpoint, status=status).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    def record_chat_request(self):
        """Record chat request."""
        self.chat_requests.inc()
    
    def record_chat_response(self, tokens: int, cost: float, response_time: float):
        """Record chat response metrics."""
        self.chat_responses.inc()
        self.tokens_used.inc(tokens)
        self.api_cost.inc(cost)
    
    def record_error(self, error_type: str):
        """Record error metrics."""
        self.error_counter.labels(error_type=error_type).inc()
    
    def set_active_sessions(self, count: int):
        """Set active sessions count."""
        self.active_sessions.set(count)
    
    def _start_system_metrics_collection(self):
        """Start background system metrics collection."""
        def collect_system_metrics():
            while True:
                try:
                    # Memory usage
                    memory = psutil.virtual_memory()
                    self.memory_usage.set(memory.used)
                    
                    # CPU usage
                    cpu_percent = psutil.cpu_percent(interval=1)
                    self.cpu_usage.set(cpu_percent)
                    
                    time.sleep(30)  # Collect every 30 seconds
                    
                except Exception as e:
                    logger.error("Error collecting system metrics", error=str(e))
                    time.sleep(60)  # Wait longer on error
        
        thread = threading.Thread(target=collect_system_metrics, daemon=True)
        thread.start()
        logger.info("System metrics collection started")


class HealthChecker:
    """Performs health checks for various components."""
    
    def __init__(self, db_manager, chatbot_engine):
        self.db_manager = db_manager
        self.chatbot_engine = chatbot_engine
        self.start_time = datetime.utcnow()
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "version": settings.app_version,
            "uptime": (datetime.utcnow() - self.start_time).total_seconds(),
            "components": {}
        }
        
        # Database health check
        try:
            db_healthy = self.db_manager.health_check()
            health_status["components"]["database"] = {
                "status": "healthy" if db_healthy else "unhealthy",
                "details": "Qdrant vector database connection"
            }
            if not db_healthy:
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "details": f"Database error: {str(e)}"
            }
            health_status["status"] = "unhealthy"
        
        # OpenAI health check
        try:
            # Simple test to check OpenAI connectivity
            test_response = await self.chatbot_engine.generate_response("test")
            openai_healthy = "error" not in test_response
            health_status["components"]["openai"] = {
                "status": "healthy" if openai_healthy else "unhealthy",
                "details": "OpenAI API connectivity"
            }
            if not openai_healthy:
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["openai"] = {
                "status": "unhealthy",
                "details": f"OpenAI error: {str(e)}"
            }
            health_status["status"] = "unhealthy"
        
        # System health check
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            
            system_healthy = memory.percent < 90 and cpu_percent < 90
            health_status["components"]["system"] = {
                "status": "healthy" if system_healthy else "degraded",
                "details": {
                    "memory_usage_percent": memory.percent,
                    "cpu_usage_percent": cpu_percent
                }
            }
            if not system_healthy:
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["system"] = {
                "status": "unhealthy",
                "details": f"System error: {str(e)}"
            }
            health_status["status"] = "unhealthy"
        
        return health_status


# Global instances
metrics_collector = MetricsCollector()


async def metrics_endpoint(request: Request) -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


def get_metrics_summary() -> Dict[str, Any]:
    """Get a summary of current metrics."""
    return {
        "uptime_seconds": (datetime.utcnow() - metrics_collector.start_time).total_seconds(),
        "start_time": metrics_collector.start_time.isoformat(),
        "system": {
            "memory_usage_percent": psutil.virtual_memory().percent,
            "cpu_usage_percent": psutil.cpu_percent(),
            "disk_usage_percent": psutil.disk_usage('/').percent
        }
    }