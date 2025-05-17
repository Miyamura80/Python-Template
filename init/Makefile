.PHONY: all

all:
	@if [ -z "$(name)" ] || [ -z "$(description)" ]; then \
		echo "Error: Both 'name' and 'description' parameters are required"; \
		echo "Usage: make all name=<project_name> description=<project_description>"; \
		exit 1; \
	fi
	sed -i '' "s/name = \"python-template\"/name = \"$(name)\"/" ../pyproject.toml
	sed -i '' "s/description = \"Add your description here\"/description = \"$(description)\"/" ../pyproject.toml
	@echo "Updated project name to: $(name)"
	@echo "Updated project description to: $(description)"

