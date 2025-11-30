"""
ZENITH AI AGENT - CALENDAR INTEGRATION
Google Calendar, Outlook, with mock fallback.
"""

from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta, time
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class CalendarProvider(Enum):
    GOOGLE = "google"
    OUTLOOK = "outlook"
    MOCK = "mock"


class BookingStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    MODIFIED = "modified"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


@dataclass
class TimeSlot:
    start_time: datetime
    end_time: datetime
    available: bool = True
    capacity_remaining: int = 1
    
    def to_dict(self) -> Dict:
        return {
            "start": self.start_time.isoformat(),
            "start_formatted": self.start_time.strftime("%I:%M %p"),
            "available": self.available,
            "capacity": self.capacity_remaining
        }


@dataclass
class Reservation:
    id: str
    business_id: str
    customer_phone: str
    customer_name: str
    customer_email: Optional[str] = None
    date: datetime = field(default_factory=datetime.utcnow)
    time: datetime.time = field(default_factory=lambda: datetime.time(19, 0))
    party_size: int = 2
    duration_minutes: int = 90
    status: BookingStatus = BookingStatus.PENDING
    confirmation_code: str = ""
    special_requests: str = ""
    seating_preference: Optional[str] = None
    occasion: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    calendar_event_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "confirmation_code": self.confirmation_code,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "date": self.date.strftime("%Y-%m-%d"),
            "time": self.time.strftime("%I:%M %p"),
            "party_size": self.party_size,
            "status": self.status.value,
            "special_requests": self.special_requests
        }
    
    def to_confirmation_message(self, business_name: str) -> str:
        return f"""
Your reservation at {business_name} is confirmed!

📅 {self.date.strftime('%A, %B %d')}
⏰ {self.time.strftime('%I:%M %p')}
👥 Party of {self.party_size}
🔢 Confirmation: {self.confirmation_code}

To modify or cancel, please call us.
"""


class BaseCalendarIntegration(ABC):
    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
    
    @abstractmethod
    async def get_availability(self, date: datetime, duration_minutes: int = 90) -> List[TimeSlot]:
        pass
    
    @abstractmethod
    async def create_booking(self, reservation: Reservation) -> Tuple[bool, str]:
        pass
    
    @abstractmethod
    async def cancel_booking(self, event_id: str) -> bool:
        pass


class MockCalendarIntegration(BaseCalendarIntegration):
    """Mock calendar for testing"""
    
    def __init__(self, credentials: Dict = None):
        super().__init__(credentials or {})
        self._bookings: Dict[str, Reservation] = {}
        self.slot_capacity = 10
    
    async def get_availability(self, date: datetime, duration_minutes: int = 90) -> List[TimeSlot]:
        slots = []
        for hour in range(11, 22):
            for minute in [0, 30]:
                slot_start = date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                slot_end = slot_start + timedelta(minutes=30)
                
                bookings_at_slot = sum(
                    1 for b in self._bookings.values()
                    if b.date.date() == date.date() and
                    b.time.hour == hour and b.time.minute == minute and
                    b.status in [BookingStatus.CONFIRMED, BookingStatus.PENDING]
                )
                
                capacity = self.slot_capacity - bookings_at_slot
                slots.append(TimeSlot(
                    start_time=slot_start,
                    end_time=slot_end,
                    available=capacity > 0,
                    capacity_remaining=max(0, capacity)
                ))
        return slots
    
    async def create_booking(self, reservation: Reservation) -> Tuple[bool, str]:
        slots = await self.get_availability(reservation.date)
        
        for slot in slots:
            if (slot.start_time.hour == reservation.time.hour and
                slot.start_time.minute == reservation.time.minute):
                if not slot.available:
                    return False, "Time slot not available"
                if slot.capacity_remaining < reservation.party_size:
                    return False, f"Not enough capacity for party of {reservation.party_size}"
                break
        
        event_id = f"mock_event_{reservation.id}"
        reservation.calendar_event_id = event_id
        self._bookings[reservation.id] = reservation
        return True, event_id
    
    async def cancel_booking(self, event_id: str) -> bool:
        for booking in self._bookings.values():
            if booking.calendar_event_id == event_id:
                booking.status = BookingStatus.CANCELLED
                return True
        return False


class ReservationManager:
    """High-level reservation management"""
    
    def __init__(self):
        self._calendars: Dict[str, BaseCalendarIntegration] = {}
        self._reservations: Dict[str, Reservation] = {}
        self._confirmation_counter = 100000
    
    def get_calendar(self, business_id: str) -> BaseCalendarIntegration:
        if business_id not in self._calendars:
            self._calendars[business_id] = MockCalendarIntegration()
        return self._calendars[business_id]
    
    def _generate_code(self) -> str:
        self._confirmation_counter += 1
        return f"RES{self._confirmation_counter}"
    
    async def check_availability(self, business_id: str, date: datetime, party_size: int = 2) -> List[Dict]:
        calendar = self.get_calendar(business_id)
        slots = await calendar.get_availability(date)
        return [s.to_dict() for s in slots if s.available and s.capacity_remaining >= party_size]
    
    async def create_reservation(self, business_id: str, customer_phone: str, customer_name: str,
                                  date: datetime, time_slot: time, party_size: int,
                                  special_requests: str = "", **kwargs) -> Tuple[bool, Reservation, str]:
        import uuid
        
        res_id = str(uuid.uuid4())[:8].upper()
        confirmation = self._generate_code()
        
        reservation = Reservation(
            id=res_id,
            business_id=business_id,
            customer_phone=customer_phone,
            customer_name=customer_name,
            date=date,
            time=time_slot,
            party_size=party_size,
            confirmation_code=confirmation,
            special_requests=special_requests,
            **kwargs
        )
        
        calendar = self.get_calendar(business_id)
        success, result = await calendar.create_booking(reservation)
        
        if success:
            reservation.calendar_event_id = result
            reservation.status = BookingStatus.CONFIRMED
            self._reservations[res_id] = reservation
            return True, reservation, "Reservation confirmed!"
        
        return False, reservation, result
    
    async def cancel_reservation(self, reservation_id: str, reason: str = "") -> Tuple[bool, str]:
        reservation = self._reservations.get(reservation_id)
        if not reservation:
            return False, "Reservation not found"
        
        if reservation.status == BookingStatus.CANCELLED:
            return False, "Already cancelled"
        
        calendar = self.get_calendar(reservation.business_id)
        if reservation.calendar_event_id:
            success = await calendar.cancel_booking(reservation.calendar_event_id)
            if success:
                reservation.status = BookingStatus.CANCELLED
                return True, "Reservation cancelled"
        
        return False, "Failed to cancel"
    
    def get_reservation(self, reservation_id: str = None, confirmation_code: str = None,
                        phone: str = None) -> Optional[Reservation]:
        if reservation_id:
            return self._reservations.get(reservation_id)
        
        for res in self._reservations.values():
            if confirmation_code and res.confirmation_code == confirmation_code:
                return res
            if phone and res.customer_phone == phone:
                return res
        return None


# Singleton
reservation_manager = ReservationManager()


# Convenience functions
async def check_availability(business_id: str, date: datetime, party_size: int = 2) -> List[Dict]:
    return await reservation_manager.check_availability(business_id, date, party_size)


async def make_reservation(business_id: str, customer_phone: str, customer_name: str,
                           date: datetime, time_slot: time, party_size: int, **kwargs) -> Dict:
    success, reservation, message = await reservation_manager.create_reservation(
        business_id, customer_phone, customer_name, date, time_slot, party_size, **kwargs
    )
    return {
        "success": success,
        "message": message,
        "reservation": reservation.to_dict() if reservation else None,
        "confirmation_code": reservation.confirmation_code if success else None
    }


async def cancel_reservation(reservation_id: str, reason: str = "") -> Dict:
    success, message = await reservation_manager.cancel_reservation(reservation_id, reason)
    return {"success": success, "message": message}


def lookup_reservation(confirmation_code: str = None, phone: str = None) -> Optional[Dict]:
    res = reservation_manager.get_reservation(confirmation_code=confirmation_code, phone=phone)
    return res.to_dict() if res else None
