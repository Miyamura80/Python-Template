# Python-Template

<p align="center">
  <img src="media/banner.png" alt="2" width="400">
</p>

<p align="center">
<b>Description of the project here. </b>
</p>

<p align="center">
<p align="center">
  <a href="#key-features">Key Features</a> •
  <a href="#requirements">Requirements</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#configuration-options">Configuration</a> •
  <a href="#credits">Credits</a>
  <a href="#related">Related</a>
  <a href="#about-the-core-contributors">About the Core Contributors</a>
</p>

</p>

<p align="center">
  <img src="https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2FMiyamura80%2FPython-Template%2Fmain%2Fpyproject.toml&query=%24.project.name&label=Project Name&color=purple" alt="Dynamic TOML Badge">
  <img alt="Project Version" src="https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2FMiyamura80%2FPython-Template%2Fmain%2Fpyproject.toml&query=%24.project.version&label=version&color=blue">
  <img alt="Python Version" src="https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2FMiyamura80%2FPython-Template%2Fmain%2Fpyproject.toml&query=%24.project['requires-python']&label=python&logo=python&color=blue">
  <img src="https://img.shields.io/badge/License-MIT-blue" alt="License">
  <img alt="Dynamic YAML Badge" src="https://img.shields.io/badge/dynamic/yaml?url=https%3A%2F%2Fraw.githubusercontent.com%2FMiyamura80%2FPython-Template%2Fmain%2Fcommon%2Fglobal_config.yaml&query=%24%5B%27model_name%27%5D&label=Model in Use&color=yellow">
  <img alt="GitHub repo size" src="https://img.shields.io/github/repo-size/Miyamura80/Python-Template">
  <img alt="GitHub Actions Workflow Status" src="https://img.shields.io/github/actions/workflow/status/Miyamura80/Python-Template/test_target_tests.yaml?branch=main">

</p>

--- 

<p align="center">
  <img src="media/creating_banner.gif" alt="2" width="600">
</p>


## Key Features

- Super opinionated python stack to enable super fast development on new projects without getting the usual tooling available
- CI/Linters built-in
- LLM Inference/Observability built-in
- (Optional) `saas` branch contains default template for building SaaS apps

## Requirements

- [uv](https://docs.astral.sh/uv/)
  ```
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

## Quick Start

- `make all` - runs `main.py`
- `make fmt` - runs `black` linter, an opinionated linter
- `make banner` - create a new banner that makes the README nice 😊
- `make test` - runs all tests defined by `TEST_TARGETS = tests/folder1 tests/folder2`



## Configuration Options

This project uses **pydantic-settings** for configuration management, providing automatic validation and type checking.

**Configuration Files:**
- `common/global_config.yaml` - Base configuration values
- `common/config_models.py` - Pydantic models for validation
- `common/global_config.py` - Main Config class
- `.env` - Environment variables and secrets (create this file)

1. **Global config:** [`common/global_config.yaml`](common/global_config.yaml) - Add hyperparameters here
2. **Environment Variables:** Store environment variables in `.env` (git-ignored) and `common/global_config.py` will read them automatically with validation:

    `.env` file:
    ```env
    OPENAI_API_KEY=sk-...
    ```
    python file:
    ```python
    from common import global_config

    print(global_config.OPENAI_API_KEY)
    ```

## Credits

This software uses the following tools:
- [Cursor: The AI Code Editor](cursor.com)
- [uv](https://docs.astral.sh/uv/)
- [DSPY: Pytorch for LLM Inference](https://dspy.ai/)
- [LangFuse: LLM Observability Tool](https://langfuse.com/)

## Related

Coming soon...

## You may also like...

Coming soon...


