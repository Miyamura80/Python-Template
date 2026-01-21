# Initialization Scripts

This directory contains one-time initialization scripts for generating brand assets using AI.

## Scripts

### generate_banner.py

Generates a banner image for the project using LLM-powered description generation and Gemini's image generation.

**Usage:**
```bash
# From project root
make banner

# From init/ directory
cd init && make banner

# Or directly
uv run python -m init.generate_banner
```

**Output:**
- `media/banner.png` - Wide horizontal banner (16:9 aspect ratio)

**Configuration:**
- Edit the `title` and `suggestion` variables in the `__main__` block
- Uses Japanese minimalist sumi-e style by default

### generate_logo.py

Generates a logo and favicon for the documentation site using LLM-powered description generation and Gemini's image generation. The favicon icon is extracted from the wordmark to ensure visual consistency.

**Usage:**
```bash
# From project root
make logo

# From init/ directory
cd init && make logo

# Or directly
uv run python -m init.generate_logo
```

**Output:**
- `docs/public/icon.png` - Icon-only version (512x512, for Apple touch icon)
- `docs/public/favicon.ico` - Favicon (32x32, icon-only, no text)
- `docs/public/logo-light.png` - Horizontal wordmark for light mode (3200x800)
- `docs/public/logo-dark.png` - Horizontal wordmark for dark mode (3200x800)

**Configuration:**
- Edit the `project_name` and `suggestion` variables in the `__main__` block
- Uses minimalist, modern design style by default

## Dependencies

Both scripts require:
- `PIL` (Pillow) - Image manipulation
- `google-genai` - Gemini API for image generation
- `GEMINI_API_KEY` - Set in your `.env` file

## Architecture

Both scripts follow the same pattern:

1. **LLM Description Generation**: Use DSPYInference with a custom signature to generate a creative description
2. **Image Generation**: Use Gemini's image generation API with detailed prompts
3. **Post-processing**: Resize, format, and save the generated images
4. **File Output**: Save to appropriate directories with proper naming

## Notes

- These are one-time initialization scripts intended to be run manually
- The generated assets should be committed to the repository
- You can regenerate assets anytime by running the scripts again
- Consider deleting this directory after initial setup (as noted in Makefile comments)
