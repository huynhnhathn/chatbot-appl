# Deployment Guide

This guide provides step-by-step instructions for deploying the Production Chatbot Application in different environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Monitoring Setup](#monitoring-setup)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **CPU**: 2+ cores (4+ recommended for production)
- **RAM**: 4GB+ (8GB+ recommended for production)
- **Storage**: 10GB+ available space
- **OS**: Linux, macOS, or Windows with Docker support

### Software Requirements

- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.11+ (for local development)
- **OpenAI API Key**: Valid API key with sufficient credits

### Network Requirements

- **Ports**: 8000 (app), 6333 (Qdrant), 6379 (Redis), 80/443 (nginx)
- **Internet**: Required for OpenAI API access
- **Firewall**: Configure to allow required ports

## Local Development

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd chatbot-app
   ```

2. **Setup environment**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start services**
   ```bash
   # Start Qdrant and Redis
   docker-compose up -d qdrant redis
   
   # Start the application
   python main.py
   ```

5. **Access the application**
   - Web Interface: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Development Commands

```bash
# Run with debug mode
DEBUG=True python main.py

# Run tests
pytest tests/

# Format code
black app/ tests/

# Lint code
flake8 app/ tests/
```

## Docker Deployment

### Basic Docker Setup

1. **Use the setup script**
   ```bash
   ./scripts/setup.sh
   ```

2. **Manual setup**
   ```bash
   # Copy environment file
   cp .env.example .env
   
   # Edit .env with your configuration
   nano .env
   
   # Start services
   docker-compose up -d
   ```

### Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Update services
docker-compose pull
docker-compose up -d

# Scale chatbot instances
docker-compose up -d --scale chatbot=3
```

### Docker Profiles

```bash
# Development (default)
docker-compose up -d

# Production with nginx
docker-compose --profile production up -d

# With monitoring
docker-compose --profile monitoring up -d

# Full production stack
docker-compose --profile production --profile monitoring up -d
```

## Production Deployment

### Environment Configuration

1. **Production .env file**
   ```env
   # OpenAI Configuration
   OPENAI_API_KEY=your_production_api_key
   OPENAI_MODEL_NAME=gpt-4
   OPENAI_TEMPERATURE=0.7
   OPENAI_MAX_TOKENS=1000
   
   # Application Configuration
   DEBUG=False
   LOG_LEVEL=INFO
   SECRET_KEY=your_secure_secret_key_here
   
   # Server Configuration
   HOST=0.0.0.0
   PORT=8000
   WORKERS=4
   
   # Security
   CORS_ORIGINS=["https://yourdomain.com"]
   
   # Rate Limiting
   RATE_LIMIT_PER_MINUTE=60
   RATE_LIMIT_PER_HOUR=1000
   ```

2. **SSL Certificates**
   ```bash
   # Generate self-signed (development)
   openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes
   
   # Use Let's Encrypt (production)
   certbot certonly --standalone -d yourdomain.com
   ```

### Production Commands

```bash
# Start production stack
docker-compose --profile production up -d

# Start with monitoring
docker-compose --profile production --profile monitoring up -d

# Health check
curl https://yourdomain.com/api/health

# View production logs
docker-compose logs -f chatbot nginx
```

### Load Balancing

For high availability, use multiple chatbot instances:

```yaml
# docker-compose.yml
services:
  chatbot:
    # ... existing config
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

### Backup Strategy

1. **Database backup**
   ```bash
   # Backup Qdrant data
   docker-compose exec qdrant tar -czf qdrant_backup.tar.gz /qdrant/storage
   
   # Backup Redis data
   docker-compose exec redis redis-cli BGSAVE
   ```

2. **Configuration backup**
   ```bash
   tar -czf config_backup.tar.gz .env docker-compose.yml nginx.conf
   ```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured
- Helm 3.0+

### Basic Deployment

1. **Create namespace**
   ```bash
   kubectl create namespace chatbot
   ```

2. **Create ConfigMap**
   ```bash
   kubectl create configmap chatbot-config --from-file=.env -n chatbot
   ```

3. **Deploy services**
   ```bash
   kubectl apply -f k8s/ -n chatbot
   ```

### Helm Deployment

```bash
# Add Helm repository
helm repo add chatbot https://your-helm-repo.com

# Install with Helm
helm install chatbot chatbot/chatbot \
  --namespace chatbot \
  --set openai.apiKey=your_api_key \
  --set ingress.enabled=true \
  --set ingress.host=yourdomain.com
```

### Kubernetes Commands

```bash
# Check deployment status
kubectl get pods -n chatbot

# View logs
kubectl logs -f deployment/chatbot -n chatbot

# Scale deployment
kubectl scale deployment chatbot --replicas=3 -n chatbot

# Port forward for local access
kubectl port-forward svc/chatbot 8000:8000 -n chatbot
```

## Monitoring Setup

### Prometheus & Grafana

1. **Start monitoring stack**
   ```bash
   docker-compose --profile monitoring up -d
   ```

2. **Access monitoring**
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000 (admin/admin)

3. **Import Grafana dashboards**
   - Import dashboard from `grafana/dashboards/`
   - Configure Prometheus data source

### Custom Metrics

The application exposes these metrics:

- `chatbot_requests_total`: Total API requests
- `chatbot_chat_requests_total`: Chat requests
- `chatbot_tokens_used_total`: Tokens consumed
- `chatbot_api_cost_total`: API costs
- `chatbot_response_duration_seconds`: Response times

### Alerting

Configure alerts in Prometheus:

```yaml
# prometheus/alerts.yml
groups:
  - name: chatbot
    rules:
      - alert: ChatbotDown
        expr: up{job="chatbot"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Chatbot is down"
```

## Troubleshooting

### Common Issues

#### 1. Qdrant Connection Error

**Symptoms**: `Connection refused` or `Timeout` errors

**Solutions**:
```bash
# Check Qdrant status
docker-compose ps qdrant

# View Qdrant logs
docker-compose logs qdrant

# Restart Qdrant
docker-compose restart qdrant
```

#### 2. OpenAI API Errors

**Symptoms**: `401 Unauthorized` or `429 Rate Limited`

**Solutions**:
- Verify API key in `.env`
- Check API quota and billing
- Implement retry logic

#### 3. Memory Issues

**Symptoms**: Application crashes or slow performance

**Solutions**:
```bash
# Increase Docker memory limits
docker-compose down
docker system prune -a
docker-compose up -d

# Monitor memory usage
docker stats
```

#### 4. Rate Limiting

**Symptoms**: `429 Too Many Requests`

**Solutions**:
- Adjust rate limits in configuration
- Implement client-side retry logic
- Use multiple API keys

### Log Analysis

```bash
# View application logs
docker-compose logs -f chatbot

# Search for errors
docker-compose logs chatbot | grep ERROR

# Monitor real-time logs
docker-compose logs -f --tail=100 chatbot
```

### Performance Tuning

1. **Database optimization**
   ```bash
   # Increase Qdrant memory
   environment:
     QDRANT__STORAGE__MEMORY_LIMIT: 2GB
   ```

2. **Application optimization**
   ```bash
   # Increase worker processes
   WORKERS=8
   
   # Enable connection pooling
   REDIS_URL=redis://redis:6379/0?max_connections=20
   ```

3. **System optimization**
   ```bash
   # Increase file descriptors
   ulimit -n 65536
   
   # Optimize kernel parameters
   echo 'net.core.somaxconn = 65535' >> /etc/sysctl.conf
   ```

### Security Hardening

1. **Network security**
   ```bash
   # Use internal networks
   networks:
     internal:
       internal: true
   ```

2. **Container security**
   ```bash
   # Run as non-root user
   user: "1000:1000"
   
   # Read-only filesystem
   read_only: true
   ```

3. **API security**
   ```bash
   # Implement API key authentication
   # Use HTTPS only
   # Enable CORS properly
   ```

## Support

For additional support:

1. Check the [README.md](README.md) for basic setup
2. Review the [API documentation](http://localhost:8000/docs)
3. Check [GitHub Issues](https://github.com/your-repo/issues)
4. Contact the development team

## Maintenance

### Regular Tasks

1. **Weekly**
   - Check application logs
   - Monitor resource usage
   - Review error rates

2. **Monthly**
   - Update dependencies
   - Review security patches
   - Backup data

3. **Quarterly**
   - Performance review
   - Capacity planning
   - Security audit