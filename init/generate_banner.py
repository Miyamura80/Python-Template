from io import BytesIO
from PIL import Image
from google import genai
from google.genai import types
from common import global_config
from utils.llm.dspy_inference import DSPYInference
import dspy
import asyncio
from pathlib import Path


class BannerDescription(dspy.Signature):
    """Generate a creative description of a person/animal/object holding a banner. Go for a japanese style, creative and fun, but make sense."""

    title: str = dspy.InputField()
    suggestion: str = dspy.InputField(
        desc="Optional suggestion to guide the banner description generation"
    )
    banner_description: str = dspy.OutputField(
        desc="A creative description of a person/animal/object holding a banner with the given title. Do not mention any colors"
    )


client = genai.Client(api_key=global_config.GEMINI_API_KEY)


async def generate_banner(title: str, suggestion: str | None = None) -> Image.Image:
    # First, use LLM to generate a creative banner description
    inf_module = DSPYInference(
        pred_signature=BannerDescription,
        observe=False,  # Enable langfuse observability
    )

    result = await inf_module.run(
        title=title,
        suggestion=suggestion or "",
    )

    print(result.banner_description)
    style_prompt = "Style the image in a Japanese minimalist style, inspired by traditional sumi-e ink wash painting. The artwork should feature clean, elegant brushstrokes with a sense of fluidity and balance. Use a monochrome palette dominated by black ink on a textured white background, with subtle gradients achieved through water dilution. Incorporate negative space thoughtfully to emphasize simplicity and harmony. Include natural elements such as bamboo, cherry blossoms, or mountains, temples, etc. depicted with minimal yet expressive lines, evoking a sense of tranquility and Zen. Avoid unnecessary details, focusing instead on evoking emotion through subtle contrasts and the beauty of imperfection."

    # Use the generated description for the image with enhanced prompt for horizontal aspect
    prompt = f"{result.banner_description}. Create an image with the banner prominently displayed and taking 80% of the screen. The text '{title}' should be large and centered at the top. Use professional photography composition with the banner as the main focal point. Make sure the text is large, highly readable (good color contrast with background) and the banner is visually appealing with good contrast. Remember, the banner text should take up majority of the image. You should zoom into the image as much as possible. \n\n {style_prompt}"

    resp = client.models.generate_images(
        model="imagen-3.0-generate-002",
        prompt=prompt,
        config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="16:9"),
    )

    # Extract image data with proper error handling
    try:
        if not resp.generated_images:
            raise ValueError("No images generated")

        generated_image = resp.generated_images[0]  # type: ignore
        if not generated_image.image or not generated_image.image.image_bytes:  # type: ignore
            raise ValueError("Invalid image data")

        img = Image.open(BytesIO(generated_image.image.image_bytes))  # type: ignore
    except (IndexError, AttributeError, TypeError) as e:
        raise ValueError(f"Failed to extract image from response: {e}") from e

    # Create media directory if it doesn't exist
    media_dir = Path(__file__).parent.parent / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    img.save(media_dir / "banner.png")
    return img


if __name__ == "__main__":
    title = "Python-Template"
    suggestion = "use a snake in the image"
    asyncio.run(generate_banner(title, suggestion))
