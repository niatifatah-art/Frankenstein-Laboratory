"""Public ourTTS product package.

The historical :mod:`ttslab` package remains available for laboratory and compatibility
purposes. New product-facing code should prefer this namespace as it grows.
"""

from ttslab.product_contract import GenerationRequest, ResolvedGeneration
from ttslab.product_runtime import generate, plan_generation

from .paths import AppPaths
from .platform import PlatformReport, inspect_platform
from .store import LocalStore

__all__ = [
    "AppPaths",
    "GenerationRequest",
    "LocalStore",
    "PlatformReport",
    "ResolvedGeneration",
    "generate",
    "inspect_platform",
    "plan_generation",
]

__version__ = "0.10.0-dev"
