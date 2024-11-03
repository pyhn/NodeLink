from django.core.exceptions import ValidationError
from PIL import Image
import base64


def validate_image_file(img, max_size=2 * 1024 * 1024):
    """
    Validates the uploaded image file.

    Args:
        img (UploadedFile): The uploaded image file.
        max_size (int): Maximum allowed file size in bytes.

    Raises:
        ValidationError: If the image is invalid or exceeds the size limit.
    """
    if img.size > max_size:
        raise ValidationError("Image file too large ( > 2MB ).")

    try:
        image = Image.open(img)
        image.verify()  # Verify that it is, in fact, an image
    except (IOError, SyntaxError) as exc:
        raise ValidationError("Uploaded file is not a valid image.") from exc


def process_image_file(img):
    """
    Processes the uploaded image file by converting it to a base64 data URL.

    Args:
        img (UploadedFile): The uploaded image file.

    Returns:
        tuple: A tuple containing the base64 data URL and the content type.
    """
    image = Image.open(img)
    detected_type = image.format.lower()  # e.g., 'png', 'jpeg', 'gif'

    # Map detected type to contentType
    mime_to_content = {
        "png": "png",
        "jpeg": "jpeg",
        "jpg": "jpeg",  # Pillow returns 'JPEG' for both 'jpeg' and 'jpg'
        # Add more mappings if needed
    }

    actual_content_type = mime_to_content.get(
        detected_type, "a"
    )  # Default to 'a' if unknown

    # Reset the file pointer after Pillow has read the file
    img.seek(0)

    # Convert image to base64
    img_base64 = base64.b64encode(img.read()).decode("utf-8")
    data_url = f"data:image/{detected_type};base64,{img_base64}"

    return data_url, actual_content_type
