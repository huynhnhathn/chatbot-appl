#!/bin/bash

# Production Chatbot Setup Script
# This script sets up the chatbot application for production deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to setup environment
setup_environment() {
    print_status "Setting up environment..."
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            print_warning "Created .env file from .env.example"
            print_warning "Please edit .env file with your configuration before continuing"
        else
            print_error ".env.example file not found"
            exit 1
        fi
    else
        print_status ".env file already exists"
    fi
    
    # Create necessary directories
    mkdir -p logs
    mkdir -p ssl
    mkdir -p data
    
    print_success "Environment setup completed"
}

# Function to generate SSL certificates (self-signed for development)
generate_ssl_certificates() {
    print_status "Generating SSL certificates..."
    
    if [ ! -f ssl/cert.pem ] || [ ! -f ssl/key.pem ]; then
        mkdir -p ssl
        
        # Generate self-signed certificate
        openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        
        print_success "SSL certificates generated"
        print_warning "Using self-signed certificates. For production, use proper SSL certificates."
    else
        print_status "SSL certificates already exist"
    fi
}

# Function to build and start services
start_services() {
    print_status "Building and starting services..."
    
    # Build and start core services
    docker-compose up -d qdrant redis
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Build and start chatbot
    docker-compose up -d chatbot
    
    print_success "Services started successfully"
}

# Function to check service health
check_health() {
    print_status "Checking service health..."
    
    # Wait for chatbot to be ready
    sleep 15
    
    # Check chatbot health
    if curl -f http://localhost:8000/api/health >/dev/null 2>&1; then
        print_success "Chatbot is healthy"
    else
        print_warning "Chatbot health check failed. Check logs with: docker-compose logs chatbot"
    fi
    
    # Check Qdrant
    if curl -f http://localhost:6333/collections >/dev/null 2>&1; then
        print_success "Qdrant is healthy"
    else
        print_warning "Qdrant health check failed"
    fi
    
    # Check Redis
    if docker-compose exec redis redis-cli ping >/dev/null 2>&1; then
        print_success "Redis is healthy"
    else
        print_warning "Redis health check failed"
    fi
}

# Function to display access information
display_access_info() {
    print_success "Setup completed successfully!"
    echo
    echo "Access Information:"
    echo "=================="
    echo "Web Interface:     http://localhost:8000"
    echo "API Documentation: http://localhost:8000/docs"
    echo "Health Check:      http://localhost:8000/api/health"
    echo "Metrics:           http://localhost:8000/metrics"
    echo
    echo "Docker Commands:"
    echo "==============="
    echo "View logs:         docker-compose logs -f"
    echo "Stop services:     docker-compose down"
    echo "Restart services:  docker-compose restart"
    echo "Update services:   docker-compose pull && docker-compose up -d"
    echo
    echo "Production Commands:"
    echo "==================="
    echo "Start with nginx:  docker-compose --profile production up -d"
    echo "Start monitoring:  docker-compose --profile monitoring up -d"
    echo
}

# Function to setup monitoring (optional)
setup_monitoring() {
    print_status "Setting up monitoring..."
    
    # Start Prometheus and Grafana
    docker-compose --profile monitoring up -d prometheus grafana
    
    print_success "Monitoring setup completed"
    echo
    echo "Monitoring Access:"
    echo "=================="
    echo "Prometheus:        http://localhost:9090"
    echo "Grafana:           http://localhost:3000 (admin/admin)"
    echo
}

# Function to setup production (optional)
setup_production() {
    print_status "Setting up production configuration..."
    
    # Start with nginx
    docker-compose --profile production up -d
    
    print_success "Production setup completed"
    echo
    echo "Production Access:"
    echo "=================="
    echo "HTTPS:             https://localhost"
    echo "HTTP (redirect):   http://localhost"
    echo
}

# Main script
main() {
    echo "Production Chatbot Setup Script"
    echo "==============================="
    echo
    
    # Check prerequisites
    check_prerequisites
    
    # Setup environment
    setup_environment
    
    # Generate SSL certificates
    generate_ssl_certificates
    
    # Start services
    start_services
    
    # Check health
    check_health
    
    # Display access information
    display_access_info
    
    # Ask about additional setup
    echo "Additional Setup Options:"
    echo "========================"
    echo "1. Setup monitoring (Prometheus + Grafana)"
    echo "2. Setup production configuration (with nginx)"
    echo "3. Skip additional setup"
    echo
    
    read -p "Choose an option (1-3): " choice
    
    case $choice in
        1)
            setup_monitoring
            ;;
        2)
            setup_production
            ;;
        3)
            print_status "Skipping additional setup"
            ;;
        *)
            print_warning "Invalid choice, skipping additional setup"
            ;;
    esac
    
    echo
    print_success "Setup completed! Enjoy your chatbot application!"
}

# Run main function
main "$@"