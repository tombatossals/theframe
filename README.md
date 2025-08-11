# TheFrame

Upload a TOP 1000 most-famous painting image from a curated JSON list to your Samsung TheFrame TV.

## Features

- Automatically selects and uploads random artwork to your Samsung TheFrame TV
- Embeds metadata directly onto images before uploading (Author, Title, Century, Location)
- Manages artwork collections with metadata enrichment using AI
- Modern Python implementation with type hints and async operations
- Improved error handling and logging
- Cross-platform font support for metadata embedding

## Requirements

- Python 3.8 or higher
- A Samsung TheFrame TV with network access
- An Ollama server for metadata enrichment (optional)

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/tombatossals/theframe.git
   cd theframe
   ```

2. Create a virtual environment and activate it:

   ```bash
   uv venv # Alto valid: python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

## Configuration

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your Samsung TheFrame TV settings:
   - `THEFRAME_IP`: IP address of your TV
   - `THEFRAME_TOKEN`: Authentication token for your TV
   - Other settings as needed

## Usage

### Upload a random image to your TV:

```bash
python main.py upload --embed
```

### Generate artwork metadata from image files:

```bash
python main.py generate
```

### Populate artwork metadata with AI enrichment:

```bash
python main.py populate
```

### Check for errors in artwork metadata:

```bash
python main.py errors
```

### Quick upload script:

```bash
./upload.sh
```

You can also use the installed command:

```bash
theframe upload --embed
```

## Development

### Install development dependencies:

```bash
pip install -e ".[dev]"
```

### Run code formatting:

```bash
black .
```

### Run linting:

```bash
flake8
```

### Run type checking:

```bash
mypy .
```

### Run all checks:

```bash
make check
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
