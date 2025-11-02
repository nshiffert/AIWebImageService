# AIWebImageService

An AI-powered, vector-searchable image library and CDN designed specifically for cottage food business websites. Generate once, use everywhere.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Node](https://img.shields.io/badge/node-18+-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)

## 🎯 Overview

AIWebImageService solves the problem of providing high-quality, relevant imagery for thousands of cottage food business websites without the cost of generating unique images for each site. 

### Key Features

- 🎨 **AI-Powered Generation** - Create beautiful food photography using OpenAI GPT Image
- 🏷️ **Automatic Tagging** - GPT-4 Vision analyzes and tags images automatically
- 🔍 **Vector Search** - Find the perfect image using natural language queries
- 📐 **Multiple Sizes** - Each image available in 5 optimized sizes
- 💰 **Cost Efficient** - Generate once, reuse across thousands of sites
- ⚡ **Fast Delivery** - CDN-backed serving for instant loading

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenAI API key with access to:
  - GPT Image (gpt-image-1)
  - GPT-4 Vision
  - Text Embeddings Ada-002
- 8GB+ RAM recommended
- 20GB+ storage for images

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/aiwebimageservice.git
   cd aiwebimageservice
   ```

2. **Set up environment variables**
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env with your OpenAI API key and other settings
   ```

3. **Start the services**
   ```bash
   docker-compose up -d
   ```

4. **Initialize the database**
   ```bash
   docker-compose exec api python scripts/setup_db.py
   ```

5. **Create admin user**
   ```bash
   docker-compose exec api python scripts/create_admin.py
   ```

6. **Access the application**
   - Admin Panel: http://localhost:3000
   - API Documentation: http://localhost:8000/docs
   - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

## 📖 Documentation

### Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed technical documentation including:
- System design and components
- Database schema
- API specifications
- Implementation details

### API Usage

#### Search for Images

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "chocolate chip cookies on white plate",
    "size": "product_card",
    "limit": 5
  }'
```

#### Response Example

```json
{
  "results": [
    {
      "id": "img_abc123",
      "url": "https://cdn.example.com/images/img_abc123_400x300.jpg",
      "score": 0.92,
      "tags": ["cookie", "chocolate-chip", "white-plate"],
      "description": "Golden brown chocolate chip cookies on white ceramic plate",
      "dominant_color": "#F5E6D3",
      "sizes": {
        "thumbnail": "https://..._150x150.jpg",
        "product_card": "https://..._400x300.jpg",
        "full_product": "https://..._800x600.jpg",
        "hero_image": "https://..._1920x600.jpg",
        "full_res": "https://..._2048x2048.jpg"
      }
    }
  ],
  "total": 5,
  "query_time_ms": 45
}
```

## 🛠️ Development

### Project Structure

```
aiwebimageservice/
├── backend/           # FastAPI application
├── frontend/          # React admin panel
├── scripts/           # Utility scripts
├── docker-compose.yml # Local development setup
└── ARCHITECTURE.md    # Technical documentation
```

### Running Tests

```bash
# Backend tests
docker-compose exec api pytest

# Frontend tests
docker-compose exec frontend npm test

# Search performance test
docker-compose exec api python scripts/test_search.py
```

### CLI Tools

```bash
# Generate images from command line
docker-compose exec api python scripts/cli.py generate "rustic sourdough bread" --count 3

# Test search
docker-compose exec api python scripts/cli.py search "chocolate cake"

# View statistics
docker-compose exec api python scripts/cli.py stats
```

## 🎨 Admin Panel Features

### Image Generation
- Batch generation with templates
- Custom color palette selection
- Style presets for consistent aesthetics

### Image Management
- Review auto-generated tags
- Approve/reject images
- Override tags when needed
- Browse image library

### Analytics
- Search query patterns
- Tag usage statistics
- Generation costs tracking
- Image reuse metrics

## 💡 Use Cases

Perfect for:
- 🍪 Cottage food business websites
- 🛍️ Artisan marketplace platforms
- 📱 Food delivery apps
- 🎂 Bakery website builders
- 🥖 Restaurant menu systems

## 📊 Performance

- **Search Latency**: < 100ms (p95)
- **Image Sizes**: ~2MB per complete set
- **Generation Cost**: ~$0.052 per image
- **Capacity**: Supports thousands of websites
- **Cache Hit Rate**: > 95%

## 🔧 Configuration

### Image Sizes

| Preset | Dimensions | Use Case |
|--------|------------|----------|
| thumbnail | 150×150 | Grid views, lists |
| product_card | 400×300 | Product cards |
| full_product | 800×600 | Product pages |
| hero_image | 1920×600 | Page headers |
| full_res | 2048×2048 | Original quality |

### Cottage Food Categories

- 🍪 Cookies & Biscuits
- 🍞 Breads & Rolls
- 🎂 Cakes & Cupcakes
- 🥧 Pies & Pastries
- 🍯 Jams & Preserves
- 🍬 Candies & Confections

## 🚢 Production Deployment

### Environment Variables

```bash
# Production settings
DATABASE_URL=postgresql://user:pass@host/aiwebimage
S3_BUCKET=production-images
S3_REGION=us-east-1
CDN_BASE_URL=https://images.yourdomain.com
OPENAI_API_KEY=sk-...
```

### Recommended Infrastructure

- **Database**: PostgreSQL 16 with pgvector extension (RDS or Supabase)
- **Storage**: AWS S3 or Cloudflare R2
- **CDN**: CloudFront or Cloudflare
- **Hosting**: AWS ECS, Google Cloud Run, or Railway
- **Redis**: ElastiCache or Upstash

## 📈 Monitoring

The application includes built-in metrics for:
- Search request volume and latency
- Image generation success/failure rates
- Tag confidence distribution
- API usage by client
- Storage and bandwidth usage

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/aiwebimageservice/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/aiwebimageservice/discussions)

## 🙏 Acknowledgments

- OpenAI for GPT Image and GPT-4 Vision
- The pgvector team for PostgreSQL vector support
- The cottage food business community for inspiration

## 🚀 Roadmap

- [ ] Multi-language tag support
- [ ] Seasonal image variations
- [ ] A/B testing for image effectiveness
- [ ] Custom style training
- [ ] Bulk export tools
- [ ] Advanced analytics dashboard

---

Built with ❤️ for cottage food entrepreneurs