import cv2
import numpy as np
import requests

class PhoneCamera:

    def __init__(self, snapshot_url: str, timeout: int = 5):
        self.snapshot_url = snapshot_url
        self.timeout = timeout

    def capture_image(self):

        response = requests.get(self, self.snapshot_url, self.timeout)
        response.raise_for_status()

        image_bytes = np.frombuffer(response.content, dtype=np.uint8)
        image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)

        if image is None:
            raise RuntimeError("Failed to decode image from phone")
        
        return image