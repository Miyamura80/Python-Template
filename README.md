# Python-Template

<p align="center">
  <img src="media/banner.png" alt="2" width="400">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12.4-blue?logo=python" alt="Python Version">
  <img src="https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2FMiyamura80%2FPython-Template%2Fmain%2Fpyproject.toml&query=%24.project.version&label=version" alt="Dynamic TOML Badge">
</p>

## Environment Variables

Store environmnent variables in `.env` and `global_config/global_config.py`  will read those out automatically. Then, you can import them as follows:

```python
from global_config import global_config

print(global_config.OPENAI_API_KEY)
```