from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseBroker(ABC):
    """सर्व ब्रोकर्ससाठी बेस अ‍ॅब्स्ट्रॅक्ट क्लास"""

    @abstractmethod
    def get_candles(self, symbol: str, resolution: str, limit: int = 100) -> List[Dict[str, Any]]:
        """कँडल्स डेटा मिळवणे"""
        pass

    @abstractmethod
    def place_order(self, symbol: str, size: int, side: str, order_type: str = "market", price: float = 0.0) -> Dict[str, Any]:
        """ऑर्डर लावणे"""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """चालू पोझिशन्स मिळवणे"""
        pass

    @abstractmethod
    def get_balance(self) -> float:
        """वॉलेट शिल्लक मिळवणे"""
        pass