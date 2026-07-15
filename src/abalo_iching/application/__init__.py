"""Framework-independent application services."""

from .sites_meihua_service import CONTRACT_VERSION, process_sites_meihua_request
from .sites_meihua_service_v2 import CONTRACT_VERSION_V2, process_sites_meihua_v2_request

__all__ = [
    "CONTRACT_VERSION",
    "CONTRACT_VERSION_V2",
    "process_sites_meihua_request",
    "process_sites_meihua_v2_request",
]
