# Production-Ready Chatbot Application

A production-ready chatbot application built with LangChain-OpenAI and Qdrant vector database. This application provides a modern, scalable solution for AI-powered conversations with knowledge base integration.

## Features

- 🤖 **AI-Powered Chat**: Powered by OpenAI GPT models with LangChain integration
- 🧠 **Vector Database**: Qdrant vector database for semantic search and knowledge retrieval
- 💬 **Conversation Memory**: Maintains context across conversation sessions
- 🔍 **Knowledge Base**: Add and search custom knowledge content
- 📊 **Monitoring**: Comprehensive metrics and health monitoring
- 🚀 **Production Ready**: Rate limiting, logging, security headers, and error handling
- 🎨 **Modern UI**: Responsive web interface with real-time chat
- 📈 **Prometheus Metrics**: Built-in monitoring and observability
- 🐳 **Docker Support**: Easy deployment with Docker Compose

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │   FastAPI App   │    │   Qdrant DB     │
│   (HTML/JS)     │◄──►│   (Python)      │◄──►│   (Vector DB)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   OpenAI API    │
                       │   (GPT Models)  │
                       └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- OpenAI API key

### 1. Clone and Setup

```bash
git clone <repository-url>
cd chatbot-app
```

### 2. Environment Configuration

```bash
cp .env.example .env
```

Edit `.env` file with your configuration:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL_NAME=gpt-4
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=1000

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=chatbot_knowledge
QDRANT_VECTOR_SIZE=1536

# Application Configuration
APP_NAME=Production Chatbot
APP_VERSION=1.0.0
DEBUG=False
LOG_LEVEL=INFO

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Security
SECRET_KEY=your_secret_key_here_change_in_production
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start Services

#### Option A: Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# Start with monitoring
docker-compose --profile monitoring up -d

# Start production setup with nginx
docker-compose --profile production up -d
```

#### Option B: Local Development

```bash
# Start Qdrant (in separate terminal)
docker run -p 6333:6333 qdrant/qdrant:latest

# Start Redis (in separate terminal)
docker run -p 6379:6379 redis:7-alpine

# Start the application
python main.py
```

### 5. Access the Application

- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health
- **Metrics**: http://localhost:8000/metrics

## API Endpoints

### Chat Endpoints

- `POST /api/chat` - Send a message and get AI response
- `POST /api/chat/clear` - Clear conversation memory

### Knowledge Base Endpoints

- `POST /api/knowledge-base` - Add content to knowledge base
- `POST /api/search` - Search knowledge base
- `DELETE /api/knowledge-base` - Clear all knowledge base content

### System Endpoints

- `GET /api/health` - Health check
- `GET /api/metrics` - Application metrics
- `GET /api/info` - Application information
- `GET /metrics` - Prometheus metrics

## Usage Examples

### Chat API

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is machine learning?",
    "user_id": "user123"
  }'
```

### Add to Knowledge Base

```bash
curl -X POST "http://localhost:8000/api/knowledge-base" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Machine learning is a subset of artificial intelligence that enables computers to learn and make decisions without being explicitly programmed.",
    "source": "documentation",
    "metadata": {"category": "AI", "difficulty": "beginner"}
  }'
```

### Search Knowledge Base

```bash
curl -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "limit": 5,
    "score_threshold": 0.7
  }'
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `OPENAI_MODEL_NAME` | OpenAI model to use | `gpt-4` |
| `OPENAI_TEMPERATURE` | Model temperature | `0.7` |
| `OPENAI_MAX_TOKENS` | Maximum tokens per response | `1000` |
| `QDRANT_HOST` | Qdrant host | `localhost` |
| `QDRANT_PORT` | Qdrant port | `6333` |
| `QDRANT_COLLECTION_NAME` | Vector collection name | `chatbot_knowledge` |
| `QDRANT_VECTOR_SIZE` | Vector dimensions | `384` |
| `DEBUG` | Debug mode | `False` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `WORKERS` | Number of workers | `4` |
| `SECRET_KEY` | Application secret key | Required |
| `RATE_LIMIT_PER_MINUTE` | Rate limit per minute | `60` |
| `RATE_LIMIT_PER_HOUR` | Rate limit per hour | `1000` |

## Monitoring and Observability

### Health Checks

The application provides comprehensive health checks:

```bash
curl http://localhost:8000/api/health
```

### Metrics

Prometheus metrics are available at `/metrics`:

```bash
curl http://localhost:8000/metrics
```

### Logging

Structured logging with JSON format for production:

```bash
# View logs
docker-compose logs -f chatbot
```

## Production Deployment

### Docker Compose Production

```bash
# Start production stack
docker-compose --profile production up -d

# Start with monitoring
docker-compose --profile production --profile monitoring up -d
```

### Kubernetes Deployment

See `k8s/` directory for Kubernetes manifests.

### Environment Variables for Production

```env
DEBUG=False
LOG_LEVEL=INFO
SECRET_KEY=your_secure_secret_key_here
CORS_ORIGINS=["https://yourdomain.com"]
ENABLE_METRICS=True
```

## Development

### Local Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Start services
docker-compose up -d qdrant redis

# Run application in debug mode
DEBUG=True python main.py
```

### Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=app tests/
```

### Code Quality

```bash
# Format code
black app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

## Troubleshooting

### Common Issues

1. **Qdrant Connection Error**
   - Ensure Qdrant is running: `docker-compose ps qdrant`
   - Check Qdrant logs: `docker-compose logs qdrant`

2. **Vector Dimension Error**
   - **Error**: `"Vector dimension error: expected dim: 1536, got 384"`
   - **Solution**: The application automatically detects and uses the correct vector size (384 for all-MiniLM-L6-v2)
   - **Fix**: Update your `.env` file to use `QDRANT_VECTOR_SIZE=384`
   - **Alternative**: Clear the collection to recreate it with correct dimensions:
     ```bash
     curl -X DELETE http://localhost:8000/api/knowledge-base
     ```

3. **OpenAI API Error**
   - Verify API key in `.env` file
   - Check API key permissions and quota

4. **Memory Issues**
   - Increase Docker memory limits
   - Monitor system resources

5. **Rate Limiting**
   - Adjust rate limits in configuration
   - Check client usage patterns

### Logs

```bash
# Application logs
docker-compose logs -f chatbot

# Qdrant logs
docker-compose logs -f qdrant

# Redis logs
docker-compose logs -f redis
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Create an issue in the repository
- Check the documentation
- Review the API docs at `/docs`

## Roadmap

- [ ] WebSocket support for real-time chat
- [ ] Multi-language support
- [ ] Advanced conversation analytics
- [ ] Integration with external knowledge sources
- [ ] Advanced authentication and authorization
- [ ] Plugin system for custom integrations