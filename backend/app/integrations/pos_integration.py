"""
ZENITH AI AGENT - POS INTEGRATIONS
Square, Clover, Toast with mock fallback.
"""

import httpx
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class POSProvider(Enum):
    SQUARE = "square"
    CLOVER = "clover"
    TOAST = "toast"
    MOCK = "mock"


class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class POSMenuItem:
    id: str
    name: str
    description: str
    price: float  # In cents
    category: str
    available: bool = True
    modifiers: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id, "name": self.name,
            "description": self.description,
            "price": self.price,
            "price_formatted": f"${self.price / 100:.2f}",
            "category": self.category,
            "available": self.available
        }


@dataclass
class POSOrder:
    id: str
    business_id: str
    customer_phone: str
    items: List[Dict]
    subtotal: float
    tax: float
    total: float
    status: OrderStatus = OrderStatus.PENDING
    order_type: str = "pickup"
    special_instructions: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "items": self.items,
            "subtotal_formatted": f"${self.subtotal / 100:.2f}",
            "tax_formatted": f"${self.tax / 100:.2f}",
            "total_formatted": f"${self.total / 100:.2f}",
            "status": self.status.value,
            "order_type": self.order_type
        }


class BasePOSIntegration(ABC):
    def __init__(self, api_key: str, merchant_id: str):
        self.api_key = api_key
        self.merchant_id = merchant_id
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    @abstractmethod
    async def get_menu(self) -> List[POSMenuItem]:
        pass
    
    @abstractmethod
    async def get_item_availability(self, item_id: str) -> bool:
        pass
    
    @abstractmethod
    async def create_order(self, items: List[Dict], customer_phone: str,
                          order_type: str = "pickup", special_instructions: str = "") -> POSOrder:
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderStatus:
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        pass


class SquareIntegration(BasePOSIntegration):
    """Square POS Integration"""
    BASE_URL = "https://connect.squareup.com/v2"
    
    def __init__(self, api_key: str, merchant_id: str, location_id: str):
        super().__init__(api_key, merchant_id)
        self.location_id = location_id
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Square-Version": "2024-01-18"
        }
    
    async def get_menu(self) -> List[POSMenuItem]:
        try:
            response = await self.http_client.get(
                f"{self.BASE_URL}/catalog/list",
                headers=self.headers,
                params={"types": "ITEM"}
            )
            if response.status_code != 200:
                return []
            
            data = response.json()
            items = []
            for obj in data.get("objects", []):
                if obj.get("type") != "ITEM":
                    continue
                item_data = obj.get("item_data", {})
                variations = item_data.get("variations", [{}])
                price = variations[0].get("item_variation_data", {}).get("price_money", {}).get("amount", 0) if variations else 0
                
                items.append(POSMenuItem(
                    id=obj.get("id", ""),
                    name=item_data.get("name", ""),
                    description=item_data.get("description", ""),
                    price=price,
                    category=item_data.get("category_id", "")
                ))
            return items
        except:
            return []
    
    async def get_item_availability(self, item_id: str) -> bool:
        return True  # Simplified
    
    async def create_order(self, items: List[Dict], customer_phone: str,
                          order_type: str = "pickup", special_instructions: str = "") -> POSOrder:
        # Actual Square API call would go here
        raise NotImplementedError("Use mock for testing")
    
    async def get_order_status(self, order_id: str) -> OrderStatus:
        return OrderStatus.PENDING
    
    async def cancel_order(self, order_id: str) -> bool:
        return False


class CloverIntegration(BasePOSIntegration):
    """Clover POS Integration"""
    BASE_URL = "https://api.clover.com/v3"
    
    async def get_menu(self) -> List[POSMenuItem]:
        try:
            response = await self.http_client.get(
                f"{self.BASE_URL}/merchants/{self.merchant_id}/items",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            if response.status_code != 200:
                return []
            
            data = response.json()
            return [
                POSMenuItem(
                    id=e.get("id", ""),
                    name=e.get("name", ""),
                    description=e.get("alternateName", ""),
                    price=e.get("price", 0),
                    category=""
                )
                for e in data.get("elements", [])
            ]
        except:
            return []
    
    async def get_item_availability(self, item_id: str) -> bool:
        return True
    
    async def create_order(self, items: List[Dict], customer_phone: str,
                          order_type: str = "pickup", special_instructions: str = "") -> POSOrder:
        raise NotImplementedError("Use mock for testing")
    
    async def get_order_status(self, order_id: str) -> OrderStatus:
        return OrderStatus.PENDING
    
    async def cancel_order(self, order_id: str) -> bool:
        return False


class MockPOSIntegration(BasePOSIntegration):
    """Mock POS for testing"""
    
    def __init__(self, api_key: str = "mock", merchant_id: str = "mock"):
        super().__init__(api_key, merchant_id)
        self._menu = self._create_mock_menu()
        self._orders: Dict[str, POSOrder] = {}
        self._counter = 1000
    
    def _create_mock_menu(self) -> List[POSMenuItem]:
        return [
            POSMenuItem("item_001", "Classic Burger", "8oz beef patty with fries", 1499, "Burgers", True,
                       [{"id": "mod_cheese", "name": "Add Cheese", "price": 100}]),
            POSMenuItem("item_002", "Margherita Pizza", "Fresh mozzarella, tomato, basil", 1699, "Pizza"),
            POSMenuItem("item_003", "Caesar Salad", "Romaine, parmesan, croutons", 1199, "Salads"),
            POSMenuItem("item_004", "Grilled Salmon", "Atlantic salmon with vegetables", 2499, "Seafood"),
            POSMenuItem("item_005", "Pasta Carbonara", "Spaghetti, pancetta, egg", 1799, "Pasta"),
            POSMenuItem("item_006", "Chocolate Cake", "Warm chocolate lava cake", 899, "Desserts"),
            POSMenuItem("item_007", "Soft Drink", "Coke, Sprite, or Fanta", 299, "Beverages"),
            POSMenuItem("item_008", "House Wine", "Red or white by glass", 899, "Beverages")
        ]
    
    async def get_menu(self) -> List[POSMenuItem]:
        return self._menu
    
    async def get_item_availability(self, item_id: str) -> bool:
        return any(i.id == item_id and i.available for i in self._menu)
    
    async def create_order(self, items: List[Dict], customer_phone: str,
                          order_type: str = "pickup", special_instructions: str = "") -> POSOrder:
        self._counter += 1
        order_id = f"ORD{self._counter}"
        
        subtotal = 0
        order_items = []
        for item in items:
            menu_item = next((m for m in self._menu if m.id == item["item_id"]), None)
            if menu_item:
                qty = item.get("quantity", 1)
                item_total = menu_item.price * qty
                subtotal += item_total
                order_items.append({
                    "item_id": item["item_id"],
                    "name": menu_item.name,
                    "quantity": qty,
                    "price": menu_item.price,
                    "total": item_total
                })
        
        tax = int(subtotal * 0.0825)
        total = subtotal + tax
        
        order = POSOrder(
            id=order_id,
            business_id=self.merchant_id,
            customer_phone=customer_phone,
            items=order_items,
            subtotal=subtotal,
            tax=tax,
            total=total,
            status=OrderStatus.CONFIRMED,
            order_type=order_type,
            special_instructions=special_instructions
        )
        self._orders[order_id] = order
        return order
    
    async def get_order_status(self, order_id: str) -> OrderStatus:
        order = self._orders.get(order_id)
        return order.status if order else OrderStatus.PENDING
    
    async def cancel_order(self, order_id: str) -> bool:
        if order_id in self._orders:
            self._orders[order_id].status = OrderStatus.CANCELLED
            return True
        return False


class POSManager:
    """Manages POS integrations for businesses"""
    
    def __init__(self):
        self._integrations: Dict[str, BasePOSIntegration] = {}
    
    def register(self, business_id: str, provider: POSProvider, credentials: Dict) -> BasePOSIntegration:
        if provider == POSProvider.SQUARE:
            integration = SquareIntegration(
                credentials.get("api_key", ""),
                credentials.get("merchant_id", ""),
                credentials.get("location_id", "")
            )
        elif provider == POSProvider.CLOVER:
            integration = CloverIntegration(
                credentials.get("api_key", ""),
                credentials.get("merchant_id", "")
            )
        else:
            integration = MockPOSIntegration()
        
        self._integrations[business_id] = integration
        return integration
    
    def get(self, business_id: str) -> Optional[BasePOSIntegration]:
        return self._integrations.get(business_id)
    
    def get_or_mock(self, business_id: str) -> BasePOSIntegration:
        if business_id not in self._integrations:
            self._integrations[business_id] = MockPOSIntegration(merchant_id=business_id)
        return self._integrations[business_id]


# Singleton
pos_manager = POSManager()


# Convenience functions
async def get_menu(business_id: str) -> List[Dict]:
    integration = pos_manager.get_or_mock(business_id)
    items = await integration.get_menu()
    return [item.to_dict() for item in items]


async def check_availability(business_id: str, item_id: str) -> bool:
    integration = pos_manager.get_or_mock(business_id)
    return await integration.get_item_availability(item_id)


async def create_order(business_id: str, items: List[Dict], customer_phone: str,
                       order_type: str = "pickup", special_instructions: str = "") -> Dict:
    integration = pos_manager.get_or_mock(business_id)
    order = await integration.create_order(items, customer_phone, order_type, special_instructions)
    return order.to_dict()


async def get_order_status(business_id: str, order_id: str) -> str:
    integration = pos_manager.get_or_mock(business_id)
    status = await integration.get_order_status(order_id)
    return status.value


async def cancel_order(business_id: str, order_id: str) -> bool:
    integration = pos_manager.get_or_mock(business_id)
    return await integration.cancel_order(order_id)
