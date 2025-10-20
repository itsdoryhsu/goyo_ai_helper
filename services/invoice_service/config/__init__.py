# Invoice Service Configuration Module
# 跨服務導入fallback機制
try:
    from .settings import *
except ImportError:
    from services.invoice_service.config.settings import *