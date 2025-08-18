# Agent Guidelines for TheFrame

## Build/Test Commands
- **Format**: `make format` or `black .`
- **Lint**: `make lint` or `flake8 .`
- **Type Check**: `make type-check` or `mypy .`
- **Test All**: `make test` or `pytest`
- **Single Test**: `pytest tests/test_specific.py::test_function_name`
- **All Checks**: `make check` (runs format, lint, type-check, test)

## Code Style
- **Python Version**: 3.8+ (configured for 3.8-3.12 support)
- **Formatting**: Black with 88-character line length
- **Type Hints**: Required for all function definitions (`disallow_untyped_defs = true`)
- **Imports**: Group stdlib, third-party, local imports separately
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Error Handling**: Use logging with rich formatting, sys.exit(1) for CLI errors
- **Models**: Use Pydantic BaseModel/BaseSettings for configuration and data validation
- **Optional Types**: Use `Optional[Type]` from typing module
- **String Types**: Use `str` over `typing.Text`
- **Async**: Support async operations with aiohttp/httpx where needed
- **Environment**: Use pydantic-settings with env_prefix for configuration