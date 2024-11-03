from PIL import Image
from django.core.exceptions import ValidationError
import base64


def check_image(img, content_type, is_create):

    image = Image.open(img)
    detected_type = image.format.lower()  # e.g., 'png', 'jpeg',

    # Map detected type to contentType
    mime_to_content = {
        "png": "png",
        "jpeg": "jpeg",
        "jpg": "jpeg",  # Pillow returns 'JPEG' for both 'jpeg' and 'jpg'
    }

    actual_content_type = mime_to_content.get(
        detected_type, "a"
    )  # Default to 'a' if unknown

    if is_create:
        # Compare with provided content_type
        if content_type != actual_content_type:
            raise ValidationError("MIME type does not match contentType.")

    # Reset the file pointer after Pillow has read the file
    img.seek(0)

    # Convert image to base64
    img_base64 = base64.b64encode(img.read()).decode("utf-8")
    content = f"data:image/{actual_content_type};base64,{img_base64}"

    return content, actual_content_type
