# Media Service API

A FastAPI-based file storage service using MongoDB GridFS for storing and managing images and videos.

## Features

- 🎥 **Media File Storage**: Upload and store images and videos using MongoDB GridFS
- 👤 **Owner Management**: Associate files with specific owners
- 🏷️ **Tagging System**: Add tags to files for better organization
- 📝 **Metadata Management**: Store descriptions and custom metadata
- 🔍 **Advanced Filtering**: Filter files by owner, status, content type, and tags
- 📄 **Pagination**: Efficient file listing with pagination support
- 🗑️ **Soft/Hard Delete**: Choose between marking files as deleted or permanent removal
- 🔄 **Status Management**: Track file status (ACTIVE, DELETED, HIDDEN, etc.)
- 🌐 **CORS Support**: Ready for web application integration

## Tech Stack

- **Backend**: FastAPI (Python 3.12+)
- **Database**: MongoDB with GridFS
- **Package Manager**: uv
- **Containerization**: Docker & Docker Compose
- **ODM**: Beanie (async MongoDB ODM)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for local development)
- uv package manager (for local development)

### 1. Using Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd media-service

# Start all services (uses pre-built image from Docker Hub)
make up

# Check logs
make logs
```

### 2. Development with Docker

```bash
# Build and start services locally for development
make up-dev

# Check logs
make logs-api
```

### 3. Local Development (without Docker)

```bash
# Install dependencies
make dev-deps

# Start MongoDB (using Docker)
make mongo-start

# Run development server
make dev
```

The API will be available at `http://localhost:8000`

## API Endpoints

### File Operations

- `POST /upload` - Upload a new file
- `GET /files/{file_id}` - Download a file
- `GET /files/{file_id}/info` - Get file metadata
- `PUT /files/{file_id}` - Update file metadata
- `DELETE /files/{file_id}` - Delete a file (soft/hard)
- `GET /files` - List files with filtering

### Upload Example

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@image.jpg" \
  -F "owner_id=user123" \
  -F "tags=vacation,beach,2024" \
  -F "description=Beach vacation photo"
```

### List Files with Filters

```bash
# Get all files for a specific owner
curl "http://localhost:8000/files?owner_id=user123"

# Filter by content type
curl "http://localhost:8000/files?content_type=image/"

# Filter by tags
curl "http://localhost:8000/files?tags=vacation,beach"

# Pagination
curl "http://localhost:8000/files?limit=10&skip=20"
```

## File Status Types

- `ACTIVE` - File is available and visible
- `DELETED` - File is soft deleted (hidden but recoverable)
- `HIDDEN` - File is hidden from normal listings
- `PROCESSING` - File is being processed
- `QUARANTINED` - File is quarantined (e.g., for review)

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGODB_URL` | MongoDB connection string | `mongodb://root:example@localhost:27017` |
| `DB_NAME` | Database name | `media_db` |

### Docker Compose Configuration

The service uses these ports:
- `8000` - API server
- `27017` - MongoDB

## Development

### Available Make Commands

```bash
make help          # Show all available commands
make dev           # Run development server
make build         # Build Docker image
make up            # Start services (production mode)
make up-dev        # Start services (development mode)
make down          # Stop all services
make logs          # View logs
make push          # Push image to Docker Hub
make release       # Build and push all image variants
make mongo-shell   # Connect to MongoDB shell
make clean         # Clean up Docker resources
```

### Docker Hub Integration

The project is configured to use Docker Hub with the `ivantana/media-service` repository:

```bash
# Login to Docker Hub
make login

# Build and push development image
make push

# Build and push all variants (latest, production)
make release
```

**Image variants:**
- `ivantana/media-service:latest` - Latest development build
- `ivantana/media-service:production` - Production optimized build

### Project Structure

```
├── app/
│   ├── main.py          # FastAPI application
│   ├── database.py      # Database configuration
│   └── models/
│       └── file.py      # File model definitions
├── docker-compose.yaml  # Docker services configuration
├── Dockerfile          # Container build instructions
├── Makefile           # Development automation
├── pyproject.toml     # Python project configuration
└── README.md         # This file
```

### Adding New Features

1. Define new models in `app/models/`
2. Add API endpoints in `app/main.py`
3. Update database initialization in `app/database.py`
4. Test with `make dev`

## API Documentation

When the service is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Database Management

### Connect to MongoDB

```bash
# Using make command
make mongo-shell

# Direct docker command
docker-compose exec mongodb mongosh -u root -p example --authenticationDatabase admin
```

### Backup and Restore

```bash
# Backup
docker-compose exec mongodb mongodump --uri="mongodb://root:example@localhost:27017/media_db" --out=/data/backup

# Restore
docker-compose exec mongodb mongorestore --uri="mongodb://root:example@localhost:27017/media_db" /data/backup/media_db
```

## Production Deployment

### Build Production Image

```bash
make prod-build
```

### Production Considerations

1. **Security**:
   - Change default MongoDB credentials
   - Configure proper CORS origins
   - Use environment variables for secrets

2. **Performance**:
   - Set up MongoDB indexes for frequently queried fields
   - Configure appropriate GridFS chunk sizes
   - Use a reverse proxy (nginx) for static file serving

3. **Monitoring**:
   - Set up health checks
   - Monitor MongoDB performance
   - Log aggregation for debugging

### Environment Variables for Production

```bash
export MONGODB_URL="mongodb://username:password@mongo-host:27017/media_db"
export CORS_ORIGINS="https://yourdomain.com,https://api.yourdomain.com"
```

## Troubleshooting

### Common Issues

1. **Connection refused to MongoDB**:
   ```bash
   make mongo-start
   # Wait a few seconds for MongoDB to start
   make dev
   ```

2. **Port already in use**:
   ```bash
   # Check what's using the port
   lsof -i :8000
   # Kill the process or change the port in docker-compose.yaml
   ```

3. **File upload fails**:
   - Check file size limits
   - Ensure file type is image/* or video/*
   - Verify MongoDB is running and accessible

### Logs

```bash
# All services
make logs

# API only
make logs-api

# MongoDB only
make logs-mongo
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review API documentation at `/docs`
3. Create an issue in the repository
