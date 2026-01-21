from io import BytesIO
from PIL import Image
from google import genai
from google.genai import types
from common import global_config
from utils.llm.dspy_inference import DSPYInference
import dspy
import asyncio
from pathlib import Path
import numpy as np


class WordmarkDescription(dspy.Signature):
    """Generate a creative description for a horizontal wordmark logo with text. The wordmark should be clean, modern, and professional."""

    project_name: str = dspy.InputField()
    suggestion: str = dspy.InputField(
        desc="Optional suggestion to guide the wordmark description generation"
    )
    wordmark_description: str = dspy.OutputField(
        desc="A creative description for a horizontal wordmark logo that includes the project name as text. Focus on typography, icon placement, and professional branding. The wordmark should be wide and horizontal."
    )


class IconDescription(dspy.Signature):
    """Generate a creative description for a square icon (no text). The icon should be clean, modern, and recognizable."""

    project_name: str = dspy.InputField()
    suggestion: str = dspy.InputField(
        desc="Optional suggestion to guide the icon description generation"
    )
    is_dark_mode: bool = dspy.InputField(
        desc="Whether this is for dark mode (light colors) or light mode (dark colors)"
    )
    icon_description: str = dspy.OutputField(
        desc="A creative description for a square icon without any text. Focus on simple shapes, clean lines, and a professional look."
    )


client = genai.Client(api_key=global_config.GEMINI_API_KEY)


def remove_greenscreen(img: Image.Image, tolerance: int = 60) -> Image.Image:
    """Remove lime green/greenscreen background using aggressive chroma key removal."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    data = np.array(img, dtype=np.float32)
    r, g, b, alpha = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]

    # Step 1: Identify obvious greenscreen pixels (more aggressive threshold)
    green_high = g > 160  # Lowered from 180
    green_dominant = (g > r + tolerance) & (g > b + tolerance)
    red_blue_low = (r < 200) & (b < 200)  # Raised from 180
    greenscreen_mask = green_high & green_dominant & red_blue_low

    # Set alpha to 0 for greenscreen pixels
    alpha[greenscreen_mask] = 0

    # Step 2: Aggressively remove green spill from ALL pixels with green tint
    visible = alpha > 0
    has_green_tint = g > r + 10  # Very low threshold
    has_strong_green_tint = g > b + 10

    green_tinted = visible & has_green_tint & has_strong_green_tint

    if np.any(green_tinted):
        # Reduce green channel more aggressively
        avg_rb = (r[green_tinted] + b[green_tinted]) / 2
        # Take whichever is lower: 30% of original green, or average of R&B
        g[green_tinted] = np.minimum(g[green_tinted] * 0.3, avg_rb)

    # Step 3: Make any remaining greenish pixels more transparent
    still_greenish = (alpha > 0) & (g > r + 5) & (g > b + 5)
    alpha[still_greenish] *= 0.5  # Make them much more transparent

    # Step 4: Completely remove very faint greenish pixels
    very_faint_green = (alpha > 0) & (alpha < 150) & (g > np.maximum(r, b))
    alpha[very_faint_green] = 0

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
    r, g, b, alpha = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]

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
    """Generate logo assets using the new pipeline:
    1. Generate light mode wordmark
    2. Reduce color variance
    3. Invert colors for dark mode
    4. Generate square icons for both light and dark modes

    Args:
        project_name: Name of the project
        suggestion: Optional suggestion to guide the logo generation
        output_dir: Output directory for the generated images. Defaults to docs/public/

    Returns:
        Dictionary of generated images
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

    print("Removing greenscreen...")
    light_img = remove_greenscreen(light_img)

    # ============================================================
    # 2. Reduce color variance
    # ============================================================
    print("\n=== Step 2: Reducing Color Variance ===")
    print("Quantizing colors to reduce variance...")
    light_img = reduce_color_variance(light_img, colors=6)

    light_path = output_dir / "logo-light.png"
    light_img.save(light_path)
    print(f"✓ Light mode wordmark saved to: {light_path}")
    results["wordmark_light"] = light_img

    # ============================================================
    # 3. Generate dark mode by inverting colors
    # ============================================================
    print("\n=== Step 3: Generating Dark Mode (Invert Colors) ===")
    print("Inverting colors from light mode...")
    dark_img = invert_colors(light_img)

    dark_path = output_dir / "logo-dark.png"
    dark_img.save(dark_path)
    print(f"✓ Dark mode wordmark saved to: {dark_path}")
    results["wordmark_dark"] = dark_img

    # ============================================================
    # 4. Generate square icons for light mode
    # ============================================================
    print("\n=== Step 4: Generating Square Icon (Light Mode) ===")
    icon_inf = DSPYInference(pred_signature=IconDescription, observe=False)
    icon_light_result = await icon_inf.run(
        project_name=project_name,
        suggestion=suggestion or "",
        is_dark_mode=False,
    )

    print(f"Light icon description: {icon_light_result.icon_description}")

    icon_light_prompt = f"{icon_light_result.icon_description}. Create a SQUARE 1:1 aspect ratio icon/symbol. NO TEXT should appear. Use DARK colors (black, dark gray, dark blue, etc.) suitable for light backgrounds. The icon should be bold, simple, and instantly recognizable. Center it with minimal padding. CRITICAL: Use a BRIGHT LIME GREEN (#00FF00) GREENSCREEN background. Do not use lime green in the icon itself."

    print("Generating light mode icon with Gemini...")
    icon_light_resp = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=[icon_light_prompt],
        config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
    )

    icon_light_img = None
    for part in icon_light_resp.candidates[0].content.parts:  # type: ignore
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):  # type: ignore
            icon_light_img = Image.open(BytesIO(part.inline_data.data))  # type: ignore
            break

    if icon_light_img is None:
        raise ValueError("No light mode icon generated")

    print("Removing greenscreen from light icon...")
    icon_light_img = remove_greenscreen(icon_light_img)

    # ============================================================
    # 5. Generate square icons for dark mode
    # ============================================================
    print("\n=== Step 5: Generating Square Icon (Dark Mode) ===")
    icon_dark_result = await icon_inf.run(
        project_name=project_name,
        suggestion=suggestion or "",
        is_dark_mode=True,
    )

    print(f"Dark icon description: {icon_dark_result.icon_description}")

    icon_dark_prompt = f"{icon_dark_result.icon_description}. Create a SQUARE 1:1 aspect ratio icon/symbol. NO TEXT should appear. Use LIGHT colors (white, light gray, light cyan, etc.) suitable for dark backgrounds. The icon should be bold, simple, and instantly recognizable. Center it with minimal padding. CRITICAL: Use a BRIGHT LIME GREEN (#00FF00) GREENSCREEN background. Do not use lime green in the icon itself."

    print("Generating dark mode icon with Gemini...")
    icon_dark_resp = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=[icon_dark_prompt],
        config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
    )

    icon_dark_img = None
    for part in icon_dark_resp.candidates[0].content.parts:  # type: ignore
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):  # type: ignore
            icon_dark_img = Image.open(BytesIO(part.inline_data.data))  # type: ignore
            break

    if icon_dark_img is None:
        raise ValueError("No dark mode icon generated")

    print("Removing greenscreen from dark icon...")
    icon_dark_img = remove_greenscreen(icon_dark_img)

    # ============================================================
    # 6. Save icon versions (use light mode icon for favicon)
    # ============================================================
    print("\n=== Saving Icon Versions ===")

    # Ensure icon is square
    width, height = icon_light_img.size
    if width != height:
        size = max(width, height)
        new_icon = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        paste_x = (size - width) // 2
        paste_y = (size - height) // 2
        new_icon.paste(icon_light_img, (paste_x, paste_y))
        icon_light_img = new_icon

    # Generate favicon sizes
    favicon_32 = icon_light_img.resize((32, 32), Image.Resampling.LANCZOS)
    icon_512 = icon_light_img.resize((512, 512), Image.Resampling.LANCZOS)

    # Save icon versions
    icon_path = output_dir / "icon.png"
    favicon_path = output_dir / "favicon.ico"

    icon_512.save(icon_path)
    favicon_32.save(favicon_path, format="ICO")

    print(f"✓ Icon saved to: {icon_path}")
    print(f"✓ Favicon saved to: {favicon_path}")

    results["icon_light"] = icon_light_img
    results["icon_dark"] = icon_dark_img
    results["favicon"] = favicon_32

    print("\n=== All assets generated successfully! ===")
    return results


if __name__ == "__main__":
    project_name = "Python-Template"
    suggestion = "incorporate python snake and modern tech aesthetics, simple and clean"
    asyncio.run(generate_logo(project_name, suggestion))
