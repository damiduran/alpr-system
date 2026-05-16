from abc import ABC, abstractmethod
import os

class ALPRProvider(ABC):
    """
    Abstract Base Class for ALPR Perception Providers.
    """
    @abstractmethod
    def recognize_file(self, image_path):
        """
        Takes an image path and returns the raw API response.
        """
        pass

    @abstractmethod
    def parse_best_result(self, api_response):
        """
        Parses the raw API response into a standardized dictionary.
        Standard format:
        {
            "plate": str,
            "confidence": float,
            "make": str or None,
            "model": str or None,
            "color": str or None,
            "body_type": str or None,
            "orientation": str or None,
            "year": str or None,
            "timestamp": int or str or None
        }
        """
        pass
