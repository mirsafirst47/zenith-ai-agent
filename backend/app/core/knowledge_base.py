"""
ZENITH AI AGENT - BUSINESS KNOWLEDGE BASE
Vertical-neutral store of what the agent knows about a business:
service catalog, hours, capacity, policies, specials, FAQ.

Everything loads from the business row's `config` JSON — the same
conventional keys documented in the businesses migration:
service_catalog, appointment_capacity, faq, policies, specials.
A new vertical never needs code changes, only different config.
"""
import re
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
class ServiceCatalogItem:
    """One thing a business offers: a salon service, a mechanic job, a
    clinic procedure, a menu item. Formerly restaurant-only MenuItem."""
    id: str
    name: str
    description: str = ""
    price: Optional[float] = None
    duration_minutes: Optional[int] = None
    category: str = "general"
    available: bool = True
    tags: List[str] = field(default_factory=list)  # e.g. dietary info, "walk-in ok"
    popular: bool = False

    def to_spoken(self) -> str:
        parts = [self.name]
        if self.price is not None:
            parts.append(f"${self.price:g}")
        if self.duration_minutes:
            parts.append(f"about {self.duration_minutes} minutes")
        return " — ".join(parts)


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


@dataclass
class AppointmentCapacity:
    """How many things can happen at once, vertical-neutral.

    - max_concurrent: bays for a mechanic, chairs for a salon, exam
      rooms for a clinic, tables (roughly) for a restaurant.
    - max_party_size: only meaningful where bookings have a headcount
      (restaurants). None = this vertical doesn't collect party size.
    """
    max_concurrent: int = 10
    max_party_size: Optional[int] = None


class BusinessKnowledgeBase:
    """Central repository for business information"""

    def __init__(self, business_id: str):
        self.business_id = business_id
        self.business_name = ""
        self.business_type = ""
        self.location = ""
        self.phone = ""
        self.description = ""

        self.hours: Dict[DayOfWeek, BusinessHours] = {}
        self.catalog: Dict[str, ServiceCatalogItem] = {}
        self.policies: List[Policy] = []
        self.specials: List[SpecialOffer] = []
        self.capacity = AppointmentCapacity()
        self.faq: Dict[str, str] = {}
        self.booking_fields: List[str] = []
        self._popular_items: List[str] = []

    # ------------------------------------------------------------ loading

    def load_from_dict(self, data: Dict[str, Any]):
        """Load from a business row shaped by voice.build_business_data
        (top-level fields + the raw config dict)."""
        self.business_name = data.get("name", "")
        self.business_type = data.get("business_type", data.get("type", ""))
        self.location = data.get("location", "")
        self.phone = data.get("phone_number", "")
        self.description = data.get("description", "") or ""

        config = data.get("config") or {}

        hours_data = data.get("hours_of_operation", {}) or {}
        for day_name, hours in hours_data.items():
            try:
                day = DayOfWeek[day_name.upper()]
                if hours.get("closed"):
                    self.hours[day] = BusinessHours(time(0, 0), time(0, 0), is_closed=True)
                else:
                    open_t = self._parse_time(hours.get("open", "09:00"))
                    close_t = self._parse_time(hours.get("close", "21:00"))
                    self.hours[day] = BusinessHours(open_t, close_t)
            except (KeyError, ValueError, AttributeError):
                continue

        for raw in config.get("service_catalog", []):
            item = self._parse_catalog_item(raw)
            if item:
                self.catalog[item.id] = item

        for policy_data in config.get("policies", []):
            if isinstance(policy_data, dict):
                self.policies.append(Policy(
                    name=policy_data.get("name", ""),
                    description=policy_data.get("description", ""),
                    category=policy_data.get("category", "general"),
                ))

        for special_data in config.get("specials", []):
            if isinstance(special_data, dict):
                try:
                    self.specials.append(SpecialOffer(
                        id=special_data.get("id", str(len(self.specials))),
                        name=special_data.get("name", ""),
                        description=special_data.get("description", ""),
                        discount_type=special_data.get("discount_type", "percentage"),
                        discount_value=float(special_data.get("discount_value", 0)),
                        valid_from=datetime.fromisoformat(special_data.get("valid_from", datetime.utcnow().isoformat())),
                        valid_until=datetime.fromisoformat(special_data.get("valid_until", (datetime.utcnow() + timedelta(days=30)).isoformat())),
                        conditions=special_data.get("conditions", ""),
                    ))
                except (ValueError, TypeError):
                    continue

        cap = config.get("appointment_capacity") or {}
        if isinstance(cap, dict):
            self.capacity = AppointmentCapacity(
                max_concurrent=int(cap.get("max_concurrent", 10)),
                max_party_size=cap.get("max_party_size"),
            )
        elif isinstance(cap, int):
            self.capacity = AppointmentCapacity(max_concurrent=cap)

        self.faq = {str(k): str(v) for k, v in (config.get("faq") or {}).items()}
        self.booking_fields = self._resolve_booking_fields(config)
        self._build_caches()

    def _parse_catalog_item(self, raw: Any) -> Optional[ServiceCatalogItem]:
        """Accept both bare strings ("oil change") and rich dicts."""
        if isinstance(raw, str):
            return ServiceCatalogItem(id=self._slug(raw), name=raw)
        if isinstance(raw, dict):
            name = raw.get("name", "")
            if not name:
                return None
            price = raw.get("price")
            return ServiceCatalogItem(
                id=raw.get("id") or self._slug(name),
                name=name,
                description=raw.get("description", ""),
                price=float(price) if price is not None else None,
                duration_minutes=raw.get("duration_minutes"),
                category=raw.get("category", "general"),
                available=raw.get("available", True),
                tags=raw.get("tags", raw.get("dietary_info", [])),
                popular=raw.get("popular", False),
            )
        return None

    def _resolve_booking_fields(self, config: Dict) -> List[str]:
        """What the agent must collect to book. Config-driven, with a
        back-compat default: restaurants also collect party_size."""
        fields = config.get("booking_fields")
        if isinstance(fields, list) and fields:
            return [str(f) for f in fields]
        base = ["date", "time", "name"]
        if self.business_type == "restaurant" or self.capacity.max_party_size:
            return ["party_size"] + base
        return base

    @staticmethod
    def _slug(name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

    def _parse_time(self, time_str: str) -> time:
        try:
            if ":" in time_str:
                parts = time_str.replace(" ", "").upper()
                if "AM" in parts or "PM" in parts:
                    return datetime.strptime(parts, "%I:%M%p").time()
                return datetime.strptime(time_str, "%H:%M").time()
            return time(int(time_str), 0)
        except (ValueError, TypeError):
            return time(9, 0)

    def _build_caches(self):
        self._popular_items = [
            item.name for item in self.catalog.values()
            if item.popular and item.available
        ]

    # ------------------------------------------------------------ queries

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

    def get_items_by_category(self, category: str) -> List[ServiceCatalogItem]:
        return [i for i in self.catalog.values()
                if i.category.lower() == category.lower() and i.available]

    def find_item(self, spoken_text: str) -> Optional[ServiceCatalogItem]:
        """Match a catalog item mentioned anywhere in the caller's speech."""
        text = spoken_text.lower()
        for item in self.catalog.values():
            if item.available and item.name.lower() in text:
                return item
        return None

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

        best, best_overlap = None, 0
        q_words = set(re.findall(r"\w+", question_lower))
        for faq_q, answer in self.faq.items():
            faq_words = set(re.findall(r"\w+", faq_q.lower()))
            overlap = len(faq_words & q_words)
            if overlap >= 2 and overlap > best_overlap:
                best, best_overlap = answer, overlap
        return best

    def to_context_dict(self) -> Dict[str, Any]:
        return {
            "name": self.business_name,
            "type": self.business_type,
            "location": self.location,
            "hours_today": self.get_hours_today(),
            "is_open_now": self.is_open_now(),
            "catalog": [i.to_spoken() for i in self.catalog.values() if i.available],
            "popular_items": self.get_popular_items(5),
            "active_specials": [s.to_spoken() for s in self.get_active_specials()],
            "max_concurrent_appointments": self.capacity.max_concurrent,
            "max_party_size": self.capacity.max_party_size,
            "cancellation_policy": self.get_cancellation_policy(),
            "faq": self.faq,
            "booking_fields": self.booking_fields,
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


def create_sample_knowledge_base() -> BusinessKnowledgeBase:
    """Sample KB used by dev/test scripts — a mechanic, deliberately,
    to keep restaurant assumptions from creeping back in."""
    kb = BusinessKnowledgeBase("sample")
    kb.load_from_dict({
        "name": "Sample Auto Care",
        "business_type": "mechanic",
        "config": {
            "service_catalog": [
                {"name": "Oil Change", "price": 49.99, "duration_minutes": 30, "popular": True},
                {"name": "Brake Inspection", "price": 0, "duration_minutes": 45},
                {"name": "Tire Rotation", "price": 29.99, "duration_minutes": 30},
            ],
            "appointment_capacity": {"max_concurrent": 3},
            "faq": {
                "do you take walk-ins": "Yes, walk-ins are welcome before 3pm on weekdays.",
                "do you offer loaner cars": "We don't offer loaners, but we're next to the light rail.",
            },
        },
    })
    return kb
