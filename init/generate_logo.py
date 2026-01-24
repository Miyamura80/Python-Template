import asyncio
from io import BytesIO
from pathlib import Path

import dspy
import numpy as np
from google import genai
from google.genai import types
from PIL import Image

from common import global_config
from utils.llm.dspy_inference import DSPYInference


class WordmarkDescription(dspy.Signature):
    """Generate a creative description for a horizontal wordmark logo with text. The wordmark should be clean, modern, and professional."""

    project_name: str = dspy.InputField()
    suggestion: str = dspy.InputField(
        desc="Optional suggestion to guide the wordmark description generation"
    )
    wordmark_description: str = dspy.OutputField(
        desc="A creative description for a horizontal wordmark logo that includes the project name as text. Focus on typography, icon placement, and professional branding. The wordmark should be wide and horizontal."
    )


client = genai.Client(api_key=global_config.GEMINI_API_KEY)


def remove_greenscreen(img: Image.Image, tolerance: int = 60) -> Image.Image:
    """Remove greenscreen with better edge preservation."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    data = np.array(img, dtype=np.float32)
    r, g, b, alpha = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]

    # More conservative greenscreen detection
    green_high = g > 180  # Higher threshold
    green_dominant = (g > r + tolerance + 20) & (g > b + tolerance + 20)
    greenscreen_mask = green_high & green_dominant

    # Set alpha to 0 for greenscreen pixels
    alpha[greenscreen_mask] = 0

    # Gentler green spill removal - only on visible pixels
    visible = alpha > 128  # Only strong pixels
    has_green_tint = (g > r + 20) & (g > b + 20)
    green_tinted = visible & has_green_tint

    if np.any(green_tinted):
        avg_rb = (r[green_tinted] + b[green_tinted]) / 2
        g[green_tinted] = np.minimum(g[green_tinted] * 0.6, avg_rb)  # Less aggressive

    data[:, :, 0] = r
    data[:, :, 1] = g
    data[:, :, 2] = b
    data[:, :, 3] = alpha

    data = np.clip(data, 0, 255).astype(np.uint8)
    return Image.fromarray(data)


def reduce_color_variance(img: Image.Image, colors: int = 8) -> Image.Image:
    """Reduce color variance by quantizing to a limited palette."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Quantize to reduce color variance
    # This will unify similar colors
    quantized = img.quantize(colors=colors, method=2)
    return quantized.convert("RGBA")


def invert_colors(img: Image.Image) -> Image.Image:
    """Invert colors while preserving alpha channel."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    data = np.array(img)
    r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]

    # Invert RGB channels only (not alpha)
    r = 255 - r
    g = 255 - g
    b = 255 - b

    data[:, :, 0] = r
    data[:, :, 1] = g
    data[:, :, 2] = b

    return Image.fromarray(data)


async def generate_logo(
    project_name: str, suggestion: str | None = None, output_dir: Path | None = None
) -> dict[str, Image.Image]:
    """Generate logo assets using AI-powered pipeline with consistent branding:
    1. Generate light mode wordmark with greenscreen
    2. Extract icon from wordmark (removes text, keeps icon)
    3. Remove greenscreen from both wordmark and icon
    4. Invert colors for dark mode wordmark
    5. Invert colors for dark mode icon
    6. Save all assets including favicon

    This ensures the icon in the wordmark matches the standalone icon perfectly.

    Args:
        project_name: Name of the project
        suggestion: Optional suggestion to guide the logo generation
        output_dir: Output directory for the generated images. Defaults to docs/public/

    Returns:
        Dictionary of generated images (wordmark_light, wordmark_dark, icon_light, icon_dark, favicon)
    """
    # Determine output directory
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "docs" / "public"

    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    # ============================================================
    # 1. Generate light mode wordmark
    # ============================================================
    print("\n=== Step 1: Generating Light Mode Wordmark ===")
    wordmark_inf = DSPYInference(pred_signature=WordmarkDescription, observe=False)
    wordmark_result = await wordmark_inf.run(
        project_name=project_name,
        suggestion=suggestion or "",
    )

    print(f"Wordmark description: {wordmark_result.wordmark_description}")

    wordmark_style = "Create a minimalist, modern horizontal wordmark logo. The design should include both an icon/symbol and the text '{project_name}'. Use clean typography and simple geometric shapes. The wordmark should be professional and work well in a navigation bar. Use a limited color palette with good contrast. The design should be iconic and memorable. Avoid excessive detail or photorealistic elements."

    light_prompt = f"{wordmark_result.wordmark_description}. Create a HORIZONTAL 4:1 aspect ratio (3200x800) wordmark logo that includes the text '{project_name}'. {wordmark_style.format(project_name=project_name)} This is for LIGHT MODE, so use DARK colors (black, dark gray, dark blue, etc.). The text should be highly readable. Position the icon on the left and text on the right in a horizontal layout. CRITICAL: Use a BRIGHT LIME GREEN (#00FF00) GREENSCREEN background - this is essential for chroma key removal. Do not use any lime green color in the logo itself, only in the background."

    print("Generating light mode wordmark with Gemini...")
    light_resp = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=[light_prompt],
        config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
    )

    light_img = None
    for part in light_resp.candidates[0].content.parts:  # type: ignore
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):  # type: ignore
            light_img = Image.open(BytesIO(part.inline_data.data))  # type: ignore
            break

    if light_img is None:
        raise ValueError("No light mode wordmark generated")

    # ============================================================
    # 2. Extract icon from wordmark (before greenscreen removal)
    # ============================================================
    print("\n=== Step 2: Extracting Square Icon from Wordmark ===")
    print("Asking AI to remove text and preserve only the icon...")

    icon_extract_prompt = f"Remove ALL TEXT from this image. Keep ONLY the icon/symbol on the left side. Output a SQUARE 1:1 aspect ratio image with the icon centered. Preserve the BRIGHT LIME GREEN (#00FF00) GREENSCREEN background exactly as it is. Do not change any colors of the icon itself - keep them identical to the original. Just remove the text '{project_name}' and center the icon in a square format."

    print("Generating square icon by extracting from wordmark...")
    icon_extract_resp = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=[icon_extract_prompt, light_img],
        config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
    )

    icon_light_img = None
    for part in icon_extract_resp.candidates[0].content.parts:  # type: ignore
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):  # type: ignore
            icon_light_img = Image.open(BytesIO(part.inline_data.data))  # type: ignore
            break

    if icon_light_img is None:
        raise ValueError("No light mode icon extracted")

    print("Removing greenscreen from extracted icon...")
    icon_light_img = remove_greenscreen(icon_light_img)

    # ============================================================
    # 3. Remove greenscreen from wordmark
    # ============================================================
    print("\n=== Step 3: Removing Greenscreen from Wordmark ===")
    print("Removing greenscreen...")
    light_img = remove_greenscreen(light_img)

    light_path = output_dir / "logo-light.png"
    light_img.save(light_path)
    print(f"✓ Light mode wordmark saved to: {light_path}")
    results["wordmark_light"] = light_img

    # ============================================================
    # 4. Generate dark mode by inverting colors
    # ============================================================
    print("\n=== Step 4: Generating Dark Mode (Invert Colors) ===")
    print("Inverting colors from light mode for wordmark...")
    dark_img = invert_colors(light_img)

    dark_path = output_dir / "logo-dark.png"
    dark_img.save(dark_path)
    print(f"✓ Dark mode wordmark saved to: {dark_path}")
    results["wordmark_dark"] = dark_img

    # ============================================================
    # 5. Generate dark mode icon by inverting
    # ============================================================
    print("\n=== Step 5: Inverting Icon for Dark Mode ===")
    print("Inverting colors from light mode icon...")
    icon_dark_img = invert_colors(icon_light_img)

    # ============================================================
    # 6. Save icon versions (use light mode icon for favicon)
    # ============================================================
    print("\n=== Saving Icon Versions ===")

    # Ensure light icon is square
    width, height = icon_light_img.size
    if width != height:
        size = max(width, height)
        new_icon = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        paste_x = (size - width) // 2
        paste_y = (size - height) // 2
        new_icon.paste(icon_light_img, (paste_x, paste_y))
        icon_light_img = new_icon

    # Ensure dark icon is square
    width, height = icon_dark_img.size
    if width != height:
        size = max(width, height)
        new_icon = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        paste_x = (size - width) // 2
        paste_y = (size - height) // 2
        new_icon.paste(icon_dark_img, (paste_x, paste_y))
        icon_dark_img = new_icon

    # Generate favicon and icon sizes
    favicon_32 = icon_light_img.resize((32, 32), Image.Resampling.LANCZOS)
    icon_light_512 = icon_light_img.resize((512, 512), Image.Resampling.LANCZOS)
    icon_dark_512 = icon_dark_img.resize((512, 512), Image.Resampling.LANCZOS)

    # Save icon versions
    icon_light_path = output_dir / "icon-light.png"
    icon_dark_path = output_dir / "icon-dark.png"
    favicon_path = output_dir / "favicon.ico"

    icon_light_512.save(icon_light_path)
    icon_dark_512.save(icon_dark_path)
    favicon_32.save(favicon_path, format="ICO")

    print(f"✓ Light icon saved to: {icon_light_path}")
    print(f"✓ Dark icon saved to: {icon_dark_path}")
    print(f"✓ Favicon saved to: {favicon_path}")

    results["icon_light"] = icon_light_512
    results["icon_dark"] = icon_dark_512
    results["favicon"] = favicon_32

    print("\n=== All assets generated successfully! ===")
    return results


if __name__ == "__main__":
    project_name = "Python-Template"
    suggestion = "incorporate python snake and modern tech aesthetics, simple and clean"
    asyncio.run(generate_logo(project_name, suggestion))
