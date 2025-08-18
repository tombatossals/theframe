# TheFrame - Modern Architecture Overview

## 🚀 Modernization Summary

The codebase has been completely modernized with a clean, modular architecture:

### ✨ New Features
- **Modular Design**: Clear separation of concerns with dedicated modules
- **Async/Await Support**: Modern async patterns for better performance  
- **Type Safety**: Full Pydantic models with validation
- **Command Pattern**: Clean CLI architecture with dedicated command classes
- **Error Handling**: Comprehensive exception hierarchy
- **Configuration Management**: Environment-based settings with validation
- **AI Integration**: Enhanced metadata population with Ollama
- **Service Layer**: Dedicated services for image processing, TV communication, and metadata

### 📁 New Directory Structure

```
src/theframe/
├── core/
│   ├── models.py          # Domain models (Artwork, TVDevice, etc.)
│   ├── exceptions.py      # Custom exception hierarchy
│   └── config.py          # Configuration management
├── services/
│   ├── image_processor.py # Image processing and embedding
│   ├── tv_service.py      # Samsung TV communication
│   └── metadata_service.py # JSON/metadata management
├── cli/
│   ├── base.py           # Base command interface
│   ├── commands.py       # Specific command implementations
│   └── main.py           # CLI entry point
└── utils/                # Utility functions
```

### 🔧 Modern Features

1. **Pydantic Models**: Type-safe domain models with validation
2. **Async Services**: Non-blocking image processing and API calls
3. **Command Pattern**: Extensible CLI with clean command separation
4. **Environment Config**: Flexible configuration with .env support
5. **Rich Logging**: Beautiful console output with error details
6. **Error Handling**: Specific exceptions with helpful messages
7. **AI Enhancement**: Automatic metadata population using Ollama

### 🎯 Usage

The modernized version provides the same functionality with better architecture:

```bash
# Using the modern CLI
theframe upload --ip 192.168.1.100 --embed --debug
theframe generate --images-dir ./art --base-url https://example.com/images
theframe populate --increment --debug
theframe errors --debug

# Legacy version still available
theframe-legacy upload --ip 192.168.1.100
```

### 🔄 Migration Guide

**Environment Variables** (recommended):
```bash
export THEFRAME_TV_IP="192.168.1.100"
export THEFRAME_TV_TOKEN="your-token"
export THEFRAME_PAINTINGS_JSON="./data/paintings.json"
export THEFRAME_POPULATED_JSON="./data/populated.json"
export THEFRAME_IMAGES_DIR="./images"
export THEFRAME_BASE_URL="https://your-server.com/images"
```

**Key Improvements:**
- Better error messages with actionable details
- Async processing for faster operations
- Type safety prevents runtime errors
- Modular design for easier testing and maintenance
- Rich logging for better debugging experience

### 🧪 Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run the modern version
python -m src.theframe.cli.main upload --help

# Run tests (when implemented)
pytest tests/

# Code quality
make check  # format, lint, type-check, test
```

The modernized codebase maintains backward compatibility while providing a much cleaner foundation for future development.