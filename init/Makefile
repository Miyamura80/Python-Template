.PHONY: all banner logo

all:
	@if [ -z "$(name)" ] || [ -z "$(description)" ]; then \
		echo "Error: Both 'name' and 'description' parameters are required"; \
		echo "Usage: make all name=<project_name> description=<project_description>"; \
		exit 1; \
	fi
	sed -i '' "s/name = \"python-template\"/name = \"$(name)\"/" ../pyproject.toml
	sed -i '' "s/description = \"Add your description here\"/description = \"$(description)\"/" ../pyproject.toml
	sed -i '' "s/# Python-Template/# $(name)/" ../README.md
	sed -i '' "s/<b>Description of the project here. <\/b>/<b>$(description)<\/b>/" ../README.md
	@echo "Updated project name to: $(name)"
	@echo "Updated project description to: $(description)"

banner:
	@echo "🎨 Generating banner..."
	@cd .. && uv run python -m init.generate_banner
	@echo "✅ Banner generated in media/banner.png"

logo:
	@echo "🎨 Generating logo and favicon..."
	@cd .. && uv run python -m init.generate_logo
	@echo "✅ Logo and favicon generated in docs/public/"
