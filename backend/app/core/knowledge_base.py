"""
ZENITH AI AGENT - BUSINESS KNOWLEDGE BASE
Stores menus, hours, policies for intelligent responses.
"""

import json
from typing import Optional, Dict, List, Any
from datetime import datetime, time, timedelta
from dataclasses import dataclass, field
from enum import Enum


class DayOfWeek(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


@dataclass
class MenuItem:
    id: str
    name: str
    description: str
    price: float
    category: str
    available: bool = True
    dietary_info: List[str] = field(default_factory=list)
    popular: bool = False


@dataclass
class BusinessHours:
    open_time: time
    close_time: time
    is_closed: bool = False
    
    def is_open_at(self, check_time: time) -> bool:
        if self.is_closed:
            return False
        return self.open_time <= check_time <= self.close_time
    
    def to_string(self) -> str:
        if self.is_closed:
            return "Closed"
        return f"{self.open_time.strftime('%I:%M %p')} - {self.close_time.strftime('%I:%M %p')}"


@dataclass
class Policy:
    name: str
    description: str
    category: str


@dataclass
class SpecialOffer:
    id: str
    name: str
    description: str
    discount_type: str
    discount_value: float
    valid_from: datetime
    valid_until: datetime
    conditions: str
    
    def is_active(self) -> bool:
        now = datetime.utcnow()
        return self.valid_from <= now <= self.valid_until
    
    def to_spoken(self) -> str:
        if self.discount_type == "percentage":
            return f"{self.name}: {int(self.discount_value)}% off. {self.conditions}"
        return f"{self.name}: {self.description}"


class BusinessKnowledgeBase:
    """Central repository for business information"""
    
    def __init__(self, business_id: str):
        self.business_id = business_id
        self.business_name = ""
        self.business_type = "restaurant"
        self.location = ""
        self.phone = ""
        self.description = ""
        
        self.hours: Dict[DayOfWeek, BusinessHours] = {}
        self.menu_items: Dict[str, MenuItem] = {}
        self.policies: List[Policy] = []
        self.specials: List[SpecialOffer] = []
        
        self.total_capacity = 50
        self.max_party_size = 10
        self.faq: Dict[str, str] = {}
        self._popular_items: List[str] = []
    
    def load_from_dict(self, data: Dict[str, Any]):
        """Load business data from dictionary"""
        self.business_name = data.get("name", "")
        self.business_type = data.get("type", "restaurant")
        self.location = data.get("location", "")
        self.phone = data.get("phone_number", "")
        self.description = data.get("description", "")
        
        # Load hours
        hours_data = data.get("hours_of_operation", {})
        for day_name, hours in hours_data.items():
            try:
                day = DayOfWeek[day_name.upper()]
                if hours.get("closed"):
                    self.hours[day] = BusinessHours(time(0, 0), time(0, 0), is_closed=True)
                else:
                    open_t = self._parse_time(hours.get("open", "09:00"))
                    close_t = self._parse_time(hours.get("close", "21:00"))
                    self.hours[day] = BusinessHours(open_t, close_t)
            except (KeyError, ValueError):
                continue
        
        # Load menu
        for item_data in data.get("menu_items", []):
            item = MenuItem(
                id=item_data.get("id", str(len(self.menu_items))),
                name=item_data.get("name", ""),
                description=item_data.get("description", ""),
                price=float(item_data.get("price", 0)),
                category=item_data.get("category", "main"),
                available=item_data.get("available", True),
                dietary_info=item_data.get("dietary_info", []),
                popular=item_data.get("popular", False)
            )
            self.menu_items[item.id] = item
        
        # Load policies
        for policy_data in data.get("policies", []):
            if isinstance(policy_data, dict):
                self.policies.append(Policy(
                    name=policy_data.get("name", ""),
                    description=policy_data.get("description", ""),
                    category=policy_data.get("category", "general")
                ))
        
        # Load specials
        for special_data in data.get("specials", []):
            if isinstance(special_data, dict):
                self.specials.append(SpecialOffer(
                    id=special_data.get("id", str(len(self.specials))),
                    name=special_data.get("name", ""),
                    description=special_data.get("description", ""),
                    discount_type=special_data.get("discount_type", "percentage"),
                    discount_value=float(special_data.get("discount_value", 0)),
                    valid_from=datetime.fromisoformat(special_data.get("valid_from", datetime.utcnow().isoformat())),
                    valid_until=datetime.fromisoformat(special_data.get("valid_until", (datetime.utcnow() + timedelta(days=30)).isoformat())),
                    conditions=special_data.get("conditions", "")
                ))
        
        # Capacity
        capacity = data.get("capacity", {})
        if isinstance(capacity, dict):
            self.total_capacity = capacity.get("total", 50)
            self.max_party_size = capacity.get("max_party", 10)
        
        self.faq = data.get("faq", {})
        self._build_caches()
    
    def _parse_time(self, time_str: str) -> time:
        try:
            if ":" in time_str:
                parts = time_str.replace(" ", "").upper()
                if "AM" in parts or "PM" in parts:
                    return datetime.strptime(parts, "%I:%M%p").time()
                return datetime.strptime(time_str, "%H:%M").time()
            return time(int(time_str), 0)
        except:
            return time(9, 0)
    
    def _build_caches(self):
        self._popular_items = [
            item.name for item in self.menu_items.values()
            if item.popular and item.available
        ]
    
    def is_open_now(self) -> bool:
        now = datetime.now()
        today = DayOfWeek(now.weekday())
        if today not in self.hours:
            return True
        return self.hours[today].is_open_at(now.time())
    
    def get_hours_today(self) -> str:
        today = DayOfWeek(datetime.now().weekday())
        if today not in self.hours:
            return "We're open regular hours today."
        hours = self.hours[today]
        if hours.is_closed:
            return "We're closed today."
        return f"We're open from {hours.to_string()} today."
    
    def get_popular_items(self, count: int = 3) -> List[str]:
        return self._popular_items[:count]
    
    def get_items_by_category(self, category: str) -> List[MenuItem]:
        return [i for i in self.menu_items.values() 
                if i.category.lower() == category.lower() and i.available]
    
    def get_dietary_options(self, dietary_type: str) -> List[MenuItem]:
        return [i for i in self.menu_items.values()
                if i.available and dietary_type.lower() in [d.lower() for d in i.dietary_info]]
    
    def get_active_specials(self) -> List[SpecialOffer]:
        return [s for s in self.specials if s.is_active()]
    
    def get_policy(self, category: str) -> Optional[Policy]:
        for policy in self.policies:
            if policy.category.lower() == category.lower():
                return policy
        return None
    
    def get_cancellation_policy(self) -> str:
        policy = self.get_policy("cancellation")
        if policy:
            return policy.description
        return "We ask for 24 hours notice for cancellations."
    
    def answer_faq(self, question: str) -> Optional[str]:
        question_lower = question.lower()
        if question_lower in self.faq:
            return self.faq[question_lower]
        
        for faq_q, answer in self.faq.items():
            faq_words = set(faq_q.lower().split())
            q_words = set(question_lower.split())
            if len(faq_words & q_words) >= 2:
                return answer
        return None
    
    def to_context_dict(self) -> Dict[str, Any]:
        return {
            "name": self.business_name,
            "type": self.business_type,
            "location": self.location,
            "hours_today": self.get_hours_today(),
            "is_open_now": self.is_open_now(),
            "popular_items": self.get_popular_items(5),
            "active_specials": [s.to_spoken() for s in self.get_active_specials()],
            "max_party_size": self.max_party_size,
            "cancellation_policy": self.get_cancellation_policy()
        }


class KnowledgeBaseManager:
    """Manages knowledge bases for multiple businesses"""
    
    def __init__(self):
        self._knowledge_bases: Dict[str, BusinessKnowledgeBase] = {}
    
    def get_knowledge_base(self, business_id: str) -> Optional[BusinessKnowledgeBase]:
        return self._knowledge_bases.get(business_id)
    
    def create_knowledge_base(self, business_id: str, business_data: Dict) -> BusinessKnowledgeBase:
        kb = BusinessKnowledgeBase(business_id)
        kb.load_from_dict(business_data)
        self._knowledge_bases[business_id] = kb
        return kb


# Singleton
knowledge_manager = KnowledgeBaseManager()


# Sample data for testing
SAMPLE_RESTAURANT = {
    "name": "Bella Notte Italian Kitchen",
    "type": "restaurant",
    "location": "123 Main Street, Downtown",
    "phone_number": "+15555551234",
    "description": "Authentic Italian cuisine",
    "hours_of_operation": {
        "monday": {"open": "11:00", "close": "22:00"},
        "tuesday": {"open": "11:00", "close": "22:00"},
        "wednesday": {"open": "11:00", "close": "22:00"},
        "thursday": {"open": "11:00", "close": "23:00"},
        "friday": {"open": "11:00", "close": "23:00"},
        "saturday": {"open": "10:00", "close": "23:00"},
        "sunday": {"open": "10:00", "close": "21:00"}
    },
    "menu_items": [
        {"id": "1", "name": "Margherita Pizza", "description": "Classic tomato, mozzarella, basil", 
         "price": 16.99, "category": "pizza", "popular": True, "dietary_info": ["vegetarian"]},
        {"id": "2", "name": "Spaghetti Carbonara", "description": "Creamy egg sauce with pancetta", 
         "price": 18.99, "category": "pasta", "popular": True},
        {"id": "3", "name": "Caesar Salad", "description": "Romaine, parmesan, croutons", 
         "price": 12.99, "category": "salad", "dietary_info": ["vegetarian"]},
        {"id": "4", "name": "Tiramisu", "description": "Classic Italian dessert", 
         "price": 9.99, "category": "dessert", "popular": True}
    ],
    "policies": [
        {"name": "Cancellation", "description": "4 hours notice required. $25 fee for late cancellations on parties of 6+.", "category": "cancellation"},
        {"name": "Large Parties", "description": "Parties of 8+ require credit card to hold reservation.", "category": "large_party"}
    ],
    "specials": [
        {"id": "1", "name": "Happy Hour", "description": "Half-price apps and $5 wine",
         "discount_type": "percentage", "discount_value": 50,
         "valid_from": "2024-01-01T00:00:00", "valid_until": "2025-12-31T23:59:59",
         "conditions": "Mon-Fri 4-6pm"}
    ],
    "capacity": {"total": 80, "max_party": 12},
    "faq": {
        "do you have parking": "Yes, free parking behind the restaurant.",
        "do you take reservations": "Yes! Call or book online.",
        "is there outdoor seating": "Yes, patio seats 20 guests."
    }
}


def create_sample_knowledge_base() -> BusinessKnowledgeBase:
    return knowledge_manager.create_knowledge_base("sample-restaurant", SAMPLE_RESTAURANT)
