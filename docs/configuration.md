# Configuration

This project uses [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) for configuration management, providing automatic validation and type checking.

## File Structure

```
common/
├── global_config.yaml    # Base configuration values (checked into git)
├── config_models.py      # Pydantic models defining config structure
├── global_config.py      # Config class and singleton instance
└── production_config.yaml # Production overrides (saas branch only)

.env                      # Environment variables/secrets (git-ignored)
.global_config.yaml       # Local YAML overrides (git-ignored)
```

## Quick Usage

```python
from common import global_config

# Access nested YAML config values
global_config.example_parent.example_child
global_config.llm_config.retry.max_attempts

# Access environment variables from .env
global_config.OPENAI_API_KEY
global_config.DEV_ENV
```

## Configuration Sources (Priority Order)

The config system merges values from multiple sources. Higher priority sources override lower ones:

1. **Environment variables** (highest priority)
2. **`.env` file** (or `.prod.env` when `DEV_ENV=prod`)
3. **YAML files** (merged in order):
   - `.global_config.yaml` (local overrides, git-ignored)
   - `production_config.yaml` (when `DEV_ENV=prod`)
   - `global_config.yaml` (base config)

## Adding New Config Values

### 1. Add to YAML

Add your values to `common/global_config.yaml`:

```yaml
my_feature:
  enabled: true
  threshold: 0.5
```

### 2. Create Pydantic Model

Define the structure in `common/config_models.py`:

```python
class MyFeatureConfig(BaseModel):
    enabled: bool
    threshold: float
```

### 3. Register in Config Class

Add the field to `common/global_config.py`:

```python
from .config_models import MyFeatureConfig

class Config(BaseSettings):
    # ... existing fields ...
    my_feature: MyFeatureConfig
```

### 4. Use It

```python
from common import global_config

if global_config.my_feature.enabled:
    do_something(global_config.my_feature.threshold)
```

## Adding New Environment Variables

### 1. Add to `.env`

```env
MY_API_KEY=sk-...
```

### 2. Register in Config Class

Add the field to `common/global_config.py`:

```python
class Config(BaseSettings):
    # ... existing fields ...
    MY_API_KEY: str
```

## Local Overrides

To override config values locally without modifying tracked files, create `.global_config.yaml` in the project root:

```yaml
# .global_config.yaml (git-ignored)
llm_config:
  cache_enabled: true

logging:
  verbose: false
```

## Production Configuration

When `DEV_ENV=prod` is set:
- `.prod.env` is loaded instead of `.env`
- `production_config.yaml` values override `global_config.yaml`

## Validation

Pydantic automatically validates all config values at startup. If a required field is missing or has the wrong type, you'll get a clear error:

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Config
OPENAI_API_KEY
  Field required [type=missing, input_value={...}, input_type=dict]
```
