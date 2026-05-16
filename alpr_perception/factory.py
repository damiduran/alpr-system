import os
from .rekor_client import RekorClient
from .plate_recognizer import PlateRecognizerClient

def get_alpr_provider():
    """
    Factory to return the configured ALPR provider.
    Defaults to Rekor if not specified.
    """
    provider_type = os.getenv('ALPR_PROVIDER', 'rekor').lower()
    
    if provider_type == 'platerecognizer':
        return PlateRecognizerClient()
    else:
        # Default to Rekor
        return RekorClient()
