import cv2
import numpy as np
import requests


class PhoneCamera:

    def __init__(
        self,
        snapshot_url: str,
        timeout: int = 5,
        verify_ssl: bool = True,
    ):
        self.snapshot_url = snapshot_url
        self.timeout = timeout
        self.verify_ssl = verify_ssl

    def capture_image(self):
        response = requests.get(
            self.snapshot_url,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            content_type = response.headers.get("Content-Type", "unknown")
            body_preview = response.text[:200].replace("\n", " ")
            raise RuntimeError(
                "Phone camera snapshot request failed "
                f"with HTTP {response.status_code} for {self.snapshot_url}. "
                f"Content-Type={content_type!r}. Body preview={body_preview!r}"
            ) from exc

        image_bytes = np.frombuffer(response.content, dtype=np.uint8)
        image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)

        if image is None:
            raise RuntimeError("Failed to decode image from phone")

        return image
