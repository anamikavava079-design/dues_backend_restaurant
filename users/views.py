import hashlib
import re
import os
import requests
from django.utils import timezone

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta

from .models import (
    UserProfile,
    Restaurant,
    MenuItem,
    Order,
    OrderItem,
    Cart,
    CartItem,
    Booking,
    Promotion,
    Waitlist,
)

from .serializers import (
    CustomerRegistrationSerializer,
    RestaurantRegistrationSerializer,
    MenuItemSerializer,
    OrderSerializer,
    CartSerializer,
    BookingSerializer,
    ReviewSerializer,
    PromotionSerializer,
    WaitlistSerializer,
)

# ==========================================
# CUSTOMER REGISTRATION
# ==========================================

@api_view(['POST'])
def register_customer(request):
    serializer = CustomerRegistrationSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        return Response(
            {
                "message": "Customer registered successfully.",
                "id": user.id,
                "name": user.name,
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# RESTAURANT REGISTRATION
# ==========================================

@api_view(['POST'])
def register_restaurant(request):
    serializer = RestaurantRegistrationSerializer(data=request.data)

    if serializer.is_valid():
        restaurant = serializer.save()

        return Response(
            {
                "message": "Restaurant registered successfully.",
                "id": restaurant.id,
                "name": restaurant.name,
                "email": restaurant.email,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# CUSTOMER LOGIN
# ==========================================

@api_view(['POST'])
def login_customer(request):
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response(
            {"error": "Email and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    password_hash = hashlib.sha256(password.encode()).hexdigest()

    try:
        user = UserProfile.objects.get(email=email)

        if user.password_hash != password_hash:
            return Response(
                {"error": "Invalid password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {
                "message": "Login successful.",
                "id": user.id,
                "name": user.name,
                "email": user.email,
            },
            status=status.HTTP_200_OK,
        )

    except UserProfile.DoesNotExist:
        return Response(
            {"error": "User not found."},
            status=status.HTTP_404_NOT_FOUND,
        )


# ==========================================
# MENU API
# ==========================================

@api_view(["GET"])
def get_menu(request):
    menu = MenuItem.objects.filter(is_available=True)
    serializer = MenuItemSerializer(menu, many=True)
    return Response(serializer.data)


# ==========================================
# RECOMMENDED MENU
# ==========================================

@api_view(["GET"])
def get_recommendations(request):
    customer_id = request.GET.get("customer_id")

    try:
        user = UserProfile.objects.get(id=customer_id)

        recommendations = MenuItem.objects.filter(
            is_available=True
        )

        # Vegetarian preference
        if "Vegetarian" in user.dietary_preferences:
            recommendations = recommendations.filter(is_veg=True)

        # Vegan preference
        elif "Vegan" in user.dietary_preferences:
            recommendations = recommendations.filter(is_vegan=True)

        serializer = MenuItemSerializer(
            recommendations[:4],
            many=True
        )

        return Response(serializer.data)

    except Exception:
        recommendations = MenuItem.objects.filter(
            is_available=True
        )[:4]

        serializer = MenuItemSerializer(
            recommendations,
            many=True
        )

        return Response(serializer.data)


# ==========================================
# PREVIOUS ORDER RECOMMENDATIONS
# ==========================================

@api_view(["GET"])
def previous_order_recommendations(request):
    customer_id = request.GET.get("customer_id")

    if not customer_id:
        return Response([])

    last_order = (
        Order.objects.filter(customer_id=customer_id)
        .order_by("-created_at")
        .first()
    )

    if not last_order:
        return Response([])

    categories = OrderItem.objects.filter(order=last_order).values_list(
        "menu_item__category", flat=True
    )

    recommendations = (
        MenuItem.objects.filter(
            category__in=categories,
            is_available=True,
        )
        .exclude(
            id__in=OrderItem.objects.filter(order=last_order).values_list(
                "menu_item_id",
                flat=True,
            )
        )[:4]
    )

    serializer = MenuItemSerializer(recommendations, many=True)
    return Response(serializer.data)


# ==========================================
# CREATE ORDER API
# ==========================================

@api_view(["POST"])
def create_order(request):
    customer_id = request.data.get("customer_id")
    restaurant_id = request.data.get("restaurant_id")
    items = request.data.get("items", [])

    try:
        customer = UserProfile.objects.get(id=customer_id)
        restaurant = Restaurant.objects.get(id=restaurant_id)

        order = Order.objects.create(
            customer=customer,
            restaurant=restaurant,
            total_price=0,
        )

        total = 0

        for item in items:
            menu_item = MenuItem.objects.get(id=item["menu_item"])

            quantity = int(item["quantity"])
            customization = item.get("customization", "")

            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=quantity,
                price=menu_item.price,
                customization=customization,
            )

            total += float(menu_item.price) * quantity

        order.total_price = total
        order.save()

        serializer = OrderSerializer(order)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ==========================================
# GET ORDERS API
# ==========================================

@api_view(["GET"])
def get_orders(request):
    customer_id = request.GET.get("customer_id")

    if customer_id:
        orders = Order.objects.filter(
            customer_id=customer_id
        ).order_by("-created_at")
    else:
        orders = Order.objects.none()

    now = timezone.now()

    for order in orders:
        if order.status == "Cancelled":
            continue

        minutes = (now - order.created_at).total_seconds() / 60

        if minutes < 1:
            new_status = "Placed"

        elif minutes < 2:
            new_status = "Preparing"

        elif minutes < 3:
            new_status = "Out for Delivery"

        else:
            new_status = "Delivered"

        if order.status != new_status:
            order.status = new_status
            order.save(update_fields=["status"])

    serializer = OrderSerializer(orders, many=True)

    return Response(serializer.data)


# ==========================================
# SUBMIT REVIEW
# ==========================================

@api_view(["POST"])
def submit_review(request):
    serializer = ReviewSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()

        return Response(
            {
                "message": "Review submitted successfully."
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )


# ==========================================
# PROMOTIONS
# ==========================================

@api_view(["GET"])
def get_promotions(request):
    promotions = Promotion.objects.filter(is_active=True)
    serializer = PromotionSerializer(promotions, many=True)
    return Response(serializer.data)


# ==========================================
# ADD TO CART
# ==========================================

@api_view(["POST"])
def add_to_cart(request):
    customer_id = request.data.get("customer_id")
    menu_item_id = request.data.get("menu_item_id")
    quantity = int(request.data.get("quantity", 1))
    customization = request.data.get("customization", "")

    try:
        customer = UserProfile.objects.get(id=customer_id)

        menu_item = MenuItem.objects.get(
            id=menu_item_id,
            is_available=True
        )

        cart, created = Cart.objects.get_or_create(
            customer=customer
        )

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            menu_item=menu_item,
            customization=customization,
            defaults={
                "quantity": quantity
            }
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        serializer = CartSerializer(cart)

        return Response(
            {
                "message": f"{menu_item.name} added to cart.",
                "cart": serializer.data
            },
            status=status.HTTP_200_OK
        )

    except UserProfile.DoesNotExist:
        return Response(
            {"error": "Customer not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    except MenuItem.DoesNotExist:
        return Response(
            {"error": "Menu item not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


# ==========================================
# VIEW CART
# ==========================================

@api_view(["GET"])
def view_cart(request):
    customer_id = request.GET.get("customer_id")

    try:
        customer = UserProfile.objects.get(id=customer_id)

        cart, created = Cart.objects.get_or_create(
            customer=customer
        )

        serializer = CartSerializer(cart)

        total = 0

        for item in cart.items.all():
            total += float(item.menu_item.price) * item.quantity

        return Response(
            {
                "cart": serializer.data,
                "total_price": total
            },
            status=status.HTTP_200_OK
        )

    except UserProfile.DoesNotExist:
        return Response(
            {"error": "Customer not found."},
            status=status.HTTP_404_NOT_FOUND
        )


# ==========================================
# REMOVE ITEM FROM CART
# ==========================================

@api_view(["POST"])
def remove_from_cart(request):
    customer_id = request.data.get("customer_id")
    cart_item_id = request.data.get("cart_item_id")

    try:
        cart = Cart.objects.get(customer_id=customer_id)

        item = CartItem.objects.get(
            id=cart_item_id,
            cart=cart
        )

        item.delete()

        serializer = CartSerializer(cart)

        return Response(
            {
                "message": "Item removed from cart.",
                "cart": serializer.data
            },
            status=status.HTTP_200_OK
        )

    except Cart.DoesNotExist:
        return Response(
            {"error": "Cart not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    except CartItem.DoesNotExist:
        return Response(
            {"error": "Item not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


# ==========================================
# UPDATE CART ITEM QUANTITY
# ==========================================

@api_view(["POST"])
def update_cart(request):
    customer_id = request.data.get("customer_id")
    cart_item_id = request.data.get("cart_item_id")

    try:
        quantity = int(request.data.get("quantity"))
    except (TypeError, ValueError):
        return Response(
            {"error": "quantity must be a whole number."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        cart = Cart.objects.get(customer_id=customer_id)

        item = CartItem.objects.get(
            id=cart_item_id,
            cart=cart
        )

        # A quantity of 0 or less removes the item instead of leaving a
        # zero/negative-quantity row in the cart.
        if quantity <= 0:
            item.delete()
            serializer = CartSerializer(cart)
            return Response(
                {
                    "message": "Item removed from cart.",
                    "cart": serializer.data
                },
                status=status.HTTP_200_OK
            )

        item.quantity = quantity
        item.save()

        serializer = CartSerializer(cart)

        return Response(
            {
                "message": "Cart updated.",
                "cart": serializer.data
            },
            status=status.HTTP_200_OK
        )

    except Cart.DoesNotExist:
        return Response(
            {"error": "Cart not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    except CartItem.DoesNotExist:
        return Response(
            {"error": "Cart item not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


# ==========================================
# CLEAR CART
# ==========================================

@api_view(["POST"])
def clear_cart(request):
    customer_id = request.data.get("customer_id")

    try:
        cart = Cart.objects.get(customer_id=customer_id)

        cart.items.all().delete()

        return Response(
            {
                "message": "Cart cleared."
            }
        )

    except Cart.DoesNotExist:
        return Response(
            {
                "error": "Cart not found."
            },
            status=404
        )


# ==========================================
# BOOK TABLE
# ==========================================

@api_view(["POST"])
def book_table(request):
    customer_id = request.data.get("customer_id")
    restaurant_id = request.data.get("restaurant_id")
    booking_date = request.data.get("booking_date")
    booking_time = request.data.get("booking_time")
    guests = request.data.get("guests")
    special_request = request.data.get("special_request", "")

    try:
        customer = UserProfile.objects.get(id=customer_id)
        restaurant = Restaurant.objects.get(id=restaurant_id)

        booking = Booking.objects.create(
            customer=customer,
            restaurant=restaurant,
            booking_date=booking_date,
            booking_time=booking_time,
            guests=guests,
            special_request=special_request,
        )

        serializer = BookingSerializer(booking)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ==========================================
# GET BOOKINGS
# ==========================================

@api_view(["GET"])
def get_bookings(request):
    customer_id = request.GET.get("customer_id")

    bookings = Booking.objects.filter(
        customer_id=customer_id
    ).order_by("-created_at")

    serializer = BookingSerializer(
        bookings,
        many=True
    )

    return Response(serializer.data)


# ==========================================
# WAITLIST (direct REST endpoints)
# ==========================================
# PDF requirement: "Manage walk-in waitlists virtually -- customers join a
# queue and get notified when their table is ready."

@api_view(["POST"])
def join_waitlist(request):
    customer_id = request.data.get("customer_id")
    party_size = request.data.get("party_size")

    try:
        customer = UserProfile.objects.get(id=customer_id)
        restaurant = Restaurant.objects.first()

        if not restaurant:
            return Response(
                {"error": "No restaurant configured."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent the same customer stacking up multiple active entries.
        existing = Waitlist.objects.filter(
            customer=customer, status="Waiting"
        ).first()

        if existing:
            position = Waitlist.objects.filter(
                restaurant=existing.restaurant,
                status="Waiting",
                joined_at__lte=existing.joined_at,
            ).count()

            serializer = WaitlistSerializer(existing)

            return Response(
                {
                    "message": f"You're already on the waitlist -- you're #{position} in line.",
                    "waitlist": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        entry = Waitlist.objects.create(
            customer=customer,
            restaurant=restaurant,
            party_size=int(party_size),
        )

        position = Waitlist.objects.filter(
            restaurant=restaurant,
            status="Waiting",
            joined_at__lte=entry.joined_at,
        ).count()

        serializer = WaitlistSerializer(entry)

        return Response(
            {
                "message": f"You're #{position} in line.",
                "waitlist": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    except UserProfile.DoesNotExist:
        return Response(
            {"error": "Customer not found."}, status=status.HTTP_404_NOT_FOUND
        )
    except (TypeError, ValueError):
        return Response(
            {"error": "party_size must be a number."},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
def waitlist_status(request):
    customer_id = request.GET.get("customer_id")

    entry = (
        Waitlist.objects.filter(customer_id=customer_id, status="Waiting")
        .order_by("-joined_at")
        .first()
    )

    if not entry:
        return Response({"in_queue": False})

    position = Waitlist.objects.filter(
        restaurant=entry.restaurant,
        status="Waiting",
        joined_at__lte=entry.joined_at,
    ).count()

    serializer = WaitlistSerializer(entry)

    return Response(
        {
            "in_queue": True,
            "position": position,
            "waitlist": serializer.data,
        }
    )


@api_view(["POST"])
def leave_waitlist(request):
    customer_id = request.data.get("customer_id")

    entry = (
        Waitlist.objects.filter(customer_id=customer_id, status="Waiting")
        .order_by("-joined_at")
        .first()
    )

    if not entry:
        return Response(
            {"error": "You're not currently on a waitlist."},
            status=status.HTTP_404_NOT_FOUND,
        )

    entry.status = "Cancelled"
    entry.save()

    return Response({"message": "You've been removed from the waitlist."})


def get_upsell_items(menu_item):
    category = menu_item.category.lower()

    if category in ["burger", "pizza", "pasta"]:
        return MenuItem.objects.filter(
            category__in=["Drink", "Dessert"],
            is_available=True
        )[:2]

    elif category in ["biryani", "salad"]:
        return MenuItem.objects.filter(
            category="Drink",
            is_available=True
        )[:2]

    return []


def parse_booking_date(text):
    text = text.strip().lower()

    today = datetime.today().date()

    if text == "today":
        return today

    if text == "tomorrow":
        return today + timedelta(days=1)

    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    if text in weekdays:
        days_ahead = weekdays[text] - today.weekday()

        if days_ahead <= 0:
            days_ahead += 7

        return today + timedelta(days=days_ahead)

    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except Exception:
        return None


def parse_booking_time(text):
    text = text.strip().upper()

    formats = [
        "%I %p",
        "%I:%M %p",
        "%H:%M",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).time()
        except Exception:
            pass

    return None


# ==========================================
# FAST-PATH INTENT DETECTION HELPERS
# ==========================================

_NUMBER_WORDS = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

_ADD_TRIGGER_RE = re.compile(
    r"\b(add|order|buy|get me|give me|i want|i'd like|i would like)\b",
    re.IGNORECASE,
)
_REMOVE_TRIGGER_RE = re.compile(r"\b(remove|delete)\b", re.IGNORECASE)
_ALL_KEYWORD_RE = re.compile(r"\ball\b", re.IGNORECASE)
_WITHOUT_RE = re.compile(r"\bwithout\s+([a-zA-Z]+)\b", re.IGNORECASE)
_NO_X_RE = re.compile(r"\bno\s+([a-zA-Z]+)\b", re.IGNORECASE)
_EXTRA_RE = re.compile(r"\bextra\s+([a-zA-Z]+)\b", re.IGNORECASE)

_CHECKOUT_KEYWORDS = [
    "checkout",
    "check out",
    "pay now",
    "proceed to payment",
    "complete my order",
    "complete the order",
    "place order",
    "place my order",
]

_TRACKING_KEYWORDS = [
    "where is my order",
    "track my order",
    "track order",
    "order status",
    "is my order",
    "delivery status",
    "eta",
    "how long will delivery",
    "when will my food",
    "when will my order",
]

_REORDER_KEYWORDS = [
    "reorder",
    "order again",
    "order the same",
    "repeat my order",
    "same order again",
    "order my previous order",
]

_CANCEL_BOOKING_KEYWORDS = [
    "cancel my booking",
    "cancel my reservation",
    "cancel my table",
    "cancel booking",
    "cancel reservation",
    "delete my booking",
    "delete my reservation",
]

_BOOK_TABLE_KEYWORDS = [
    "book a table",
    "book table",
    "book me a table",
    "reserve a table",
    "reserve table",
    "make a reservation",
    "book a reservation",
    "need a table",
    "table for",
    "reservation for",
]

_JOIN_WAITLIST_KEYWORDS = [
    "join the waitlist",
    "join waitlist",
    "add me to the waitlist",
    "put me on the waitlist",
    "how long is the wait",
    "how long is the waitlist",
    "waiting list",
    "walk in",
    "walk-in",
]

_WAITLIST_STATUS_KEYWORDS = [
    "my position",
    "waitlist status",
    "am i on the waitlist",
    "where am i on the waitlist",
    "my place in line",
]

_LEAVE_WAITLIST_KEYWORDS = [
    "leave the waitlist",
    "leave waitlist",
    "cancel my waitlist",
    "remove me from the waitlist",
    "take me off the waitlist",
]

_MODIFY_BOOKING_KEYWORDS = [
    "change my booking",
    "change my reservation",
    "modify my booking",
    "modify my reservation",
    "update my booking",
    "update my reservation",
    "reschedule my booking",
    "reschedule my reservation",
    "move my booking",
    "move my reservation",
    "increase my booking",
    "reduce my booking",
    "increase my guests",
    "reduce my guests",
    "change the booking",
    "change the reservation",
]

_FEEDBACK_KEYWORDS = [
    "feedback",
    "review",
    "rate my order",
    "rate the food",
    "rate this",
    "leave a review",
    "leave feedback",
]

_RATING_RE = re.compile(r"\b([1-5])\s*(?:star|stars|/5|out of 5)?\b", re.IGNORECASE)

_MOOD_TRIGGER_RE = re.compile(
    r"\b(suggest|recommend|what should i (eat|order)|i'm (in the mood|craving)|craving)\b",
    re.IGNORECASE,
)

_MOOD_CATEGORY_MAP = {
    "comfort": (["comfort food", "feeling low", "sad", "cozy", "homely"], ["Biryani", "Pasta", "Burger"]),
    "spicy": (["spicy", "something hot", "fiery"], ["Biryani", "Pizza"]),
    "light": (["light food", "something light", "not too heavy", "healthy"], ["Salad"]),
    "sweet": (["something sweet", "dessert", "sugar craving", "sweet tooth"], ["Dessert"]),
    "quick": (["quick bite", "in a hurry", "something fast"], ["Burger", "Drink"]),
}


def _mood_phrase_present(message_lower):
    """True if the message contains one of the specific mood phrases in
    _MOOD_CATEGORY_MAP (e.g. 'quick bite', 'in a hurry'), independent of
    whether a generic trigger word like 'suggest'/'recommend'/'craving'
    is also present. FIX: without this, a message like 'quick bite, in a
    hurry' never reached handle_mood_recommendation() at all, because
    _MOOD_TRIGGER_RE only looks for the generic trigger words."""
    for phrases, _categories in _MOOD_CATEGORY_MAP.values():
        if any(phrase in message_lower for phrase in phrases):
            return True
    return False

_DATE_KEYWORD_RE = re.compile(
    r"\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)

_TIME_TOKEN_RE = re.compile(
    r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b|\b([01]?\d|2[0-3]):[0-5]\d\b",
    re.IGNORECASE,
)

_GUESTS_RE = re.compile(
    r"\bfor\s+(\d+)\s*(?:people|guests|persons|pax)?\b|\b(\d+)\s*(?:people|guests|persons)\b",
    re.IGNORECASE,
)


def _extract_customization(message):
    without_match = _WITHOUT_RE.search(message)
    if without_match:
        return f"No {without_match.group(1).capitalize()}"

    no_match = _NO_X_RE.search(message)
    if no_match:
        return f"No {no_match.group(1).capitalize()}"

    extra_match = _EXTRA_RE.search(message)
    if extra_match:
        return f"Extra {extra_match.group(1).capitalize()}"

    return ""


def _quantity_before(message_lower, start_index, default=1):
    preceding_text = message_lower[:start_index].strip()
    words = preceding_text.split()[-3:]

    for word in reversed(words):
        clean_word = word.strip(",.")
        if clean_word.isdigit():
            return int(clean_word)
        if clean_word in _NUMBER_WORDS:
            return _NUMBER_WORDS[clean_word]

    return default


def _extract_booking_details(message_lower):
    date_match = _DATE_KEYWORD_RE.search(message_lower)
    date_text = date_match.group(1) if date_match else None

    time_match = _TIME_TOKEN_RE.search(message_lower)
    time_text = time_match.group(0) if time_match else None

    guests_match = _GUESTS_RE.search(message_lower)
    guests_text = None
    if guests_match:
        guests_text = guests_match.group(1) or guests_match.group(2)

    return date_text, time_text, guests_text


def _normalize_time_text(time_text):
    if not time_text:
        return time_text
    return re.sub(r"(\d)(am|pm)", r"\1 \2", time_text, flags=re.IGNORECASE)


def _find_all_menu_items_in_message(message_lower, menu_items):
    candidates = []

    for menu_item in menu_items:
        name_lower = menu_item.name.lower()
        start = message_lower.find(name_lower)
        if start != -1:
            candidates.append((start, start + len(name_lower), menu_item))

    candidates.sort(key=lambda c: (c[1] - c[0]), reverse=True)

    chosen = []
    occupied_ranges = []

    for start, end, menu_item in candidates:
        overlap = any(
            not (end <= o_start or start >= o_end)
            for o_start, o_end in occupied_ranges
        )
        if not overlap:
            chosen.append((start, end, menu_item))
            occupied_ranges.append((start, end))

    chosen.sort(key=lambda c: c[0])
    return chosen


# ==========================================
# SHARED ACTION HANDLERS
# ==========================================

def handle_add_to_cart(customer_id, item_names, quantities, customizations):
    if not item_names:
        return Response(
            {"reply": "Sorry, I couldn't understand which item to add."},
            status=status.HTTP_200_OK,
        )

    if not customer_id:
        return Response(
            {"reply": "Please login first to add items to your cart."},
            status=status.HTTP_200_OK,
        )

    customer = UserProfile.objects.filter(id=customer_id).first()

    if not customer:
        return Response(
            {"reply": "Customer account not found."},
            status=status.HTTP_200_OK,
        )

    cart, _ = Cart.objects.get_or_create(customer=customer)

    added_items = []
    upsell_items = []

    for index, item_name in enumerate(item_names):
        item_name = str(item_name).strip()

        raw_quantity = quantities[index] if index < len(quantities) else 1
        try:
            quantity = int(raw_quantity)
        except (TypeError, ValueError):
            quantity = 1

        if quantity < 1:
            quantity = 1

        customization = (
            str(customizations[index]).strip()
            if index < len(customizations)
            else "NONE"
        )

        if customization.upper() == "NONE":
            customization = ""

        menu_item = MenuItem.objects.filter(
            name__icontains=item_name,
            is_available=True,
        ).first()

        if not menu_item:
            continue

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            menu_item=menu_item,
            customization=customization,
            defaults={"quantity": quantity},
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        if customization:
            added_items.append(f"{quantity} x {menu_item.name} ({customization})")
        else:
            added_items.append(f"{quantity} x {menu_item.name}")

        recommendations = get_upsell_items(menu_item)

        for rec in recommendations:
            if rec.name != menu_item.name:
                upsell_items.append(rec)

    if not added_items:
        return Response(
            {"reply": "Sorry, none of the requested items are available."},
            status=status.HTTP_200_OK,
        )

    serializer = CartSerializer(cart)

    reply_message = "\u2705 Added to your cart:\n\n"
    reply_message += "\n".join(added_items)

    if upsell_items:
        reply_message += "\n\n\U0001F37D\uFE0F You may also like:\n"

        shown = set()

        for item in upsell_items:
            if item.name not in shown:
                shown.add(item.name)
                reply_message += f"\n\u2022 {item.name} - \u20B9{item.price}"

    return Response(
        {"reply": reply_message, "cart": serializer.data},
        status=status.HTTP_200_OK,
    )


def handle_remove_from_cart(customer_id, item_name, quantity_str):
    if not item_name:
        return Response(
            {"reply": "Sorry, I couldn't understand which item to remove."},
            status=status.HTTP_200_OK,
        )

    if not customer_id:
        return Response({"reply": "Please login first."}, status=status.HTTP_200_OK)

    customer = UserProfile.objects.filter(id=customer_id).first()

    if not customer:
        return Response(
            {"reply": "Customer account not found."}, status=status.HTTP_200_OK
        )

    cart = Cart.objects.filter(customer=customer).first()

    if not cart:
        return Response({"reply": "Your cart is empty."}, status=status.HTTP_200_OK)

    item_name = item_name.strip()
    quantity = (quantity_str or "ALL").strip().upper()

    menu_item = MenuItem.objects.filter(
        name__icontains=item_name,
        is_available=True,
    ).first()

    if not menu_item:
        return Response(
            {"reply": f"{item_name} is not available."}, status=status.HTTP_200_OK
        )

    cart_item = CartItem.objects.filter(cart=cart, menu_item=menu_item).first()

    if not cart_item:
        return Response(
            {"reply": f"{menu_item.name} is not in your cart."},
            status=status.HTTP_200_OK,
        )

    if quantity == "ALL":
        cart_item.delete()

        serializer = CartSerializer(cart)

        return Response(
            {
                "reply": f"\U0001F5D1\uFE0F Removed all {menu_item.name} from your cart.",
                "cart": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    try:
        quantity = int(quantity)
    except ValueError:
        quantity = 1

    if cart_item.quantity > quantity:
        cart_item.quantity -= quantity
        cart_item.save()

        serializer = CartSerializer(cart)

        return Response(
            {
                "reply": f"\u2796 Removed {quantity} x {menu_item.name} from your cart.",
                "cart": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    cart_item.delete()

    serializer = CartSerializer(cart)

    return Response(
        {
            "reply": f"\U0001F5D1\uFE0F Removed all {menu_item.name} from your cart.",
            "cart": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


def handle_reorder_last_order(customer_id):
    if not customer_id:
        return Response({"reply": "Please login first."}, status=status.HTTP_200_OK)

    customer = UserProfile.objects.filter(id=customer_id).first()

    if not customer:
        return Response(
            {"reply": "Customer account not found."}, status=status.HTTP_200_OK
        )

    last_order = (
        Order.objects.filter(customer=customer).order_by("-created_at").first()
    )

    if not last_order:
        return Response(
            {"reply": "You don't have any previous orders yet."},
            status=status.HTTP_200_OK,
        )

    cart, _ = Cart.objects.get_or_create(customer=customer)

    added_items = []
    skipped_items = []

    for order_item in OrderItem.objects.filter(order=last_order):
        # An item that's since gone unavailable shouldn't silently vanish
        # from the reorder -- tell the customer instead of pretending it
        # was added.
        if not order_item.menu_item.is_available:
            skipped_items.append(order_item.menu_item.name)
            continue

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            menu_item=order_item.menu_item,
            customization=order_item.customization,
            defaults={"quantity": order_item.quantity},
        )

        if not created:
            cart_item.quantity += order_item.quantity
            cart_item.save()

        added_items.append(f"{order_item.quantity} x {order_item.menu_item.name}")

    serializer = CartSerializer(cart)

    if not added_items:
        return Response(
            {
                "reply": "Sorry, none of the items from your last order are available right now."
            },
            status=status.HTTP_200_OK,
        )

    reply = "\U0001F504 Reordered your previous order:\n\n" + "\n".join(added_items)

    if skipped_items:
        reply += "\n\n\u26A0\uFE0F No longer available: " + ", ".join(skipped_items)

    return Response(
        {
            "reply": reply,
            "cart": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


def handle_go_to_checkout():
    return Response(
        {
            "reply": "\U0001F4B3 Redirecting you to checkout...",
            "action": "GO_TO_CHECKOUT",
        },
        status=status.HTTP_200_OK,
    )


def handle_delivery_eta(customer_id):
    if not customer_id:
        return Response({"reply": "Please login first."}, status=status.HTTP_200_OK)

    customer = UserProfile.objects.filter(id=customer_id).first()

    if not customer:
        return Response(
            {"reply": "Customer account not found."}, status=status.HTTP_200_OK
        )

    order = Order.objects.filter(customer=customer).order_by("-created_at").first()

    if not order:
        return Response(
            {"reply": "You don't have any recent orders."}, status=status.HTTP_200_OK
        )

    if order.status == "Cancelled":
        return Response(
            {"reply": "Your last order was cancelled."}, status=status.HTTP_200_OK
        )

    now = timezone.now()
    minutes = (now - order.created_at).total_seconds() / 60

    if minutes < 1:
        new_status = "Placed"
    elif minutes < 2:
        new_status = "Preparing"
    elif minutes < 3:
        new_status = "Out for Delivery"
    else:
        new_status = "Delivered"

    if order.status != new_status:
        order.status = new_status
        order.save(update_fields=["status"])

    if order.status == "Placed":
        eta = "30 minutes"
        message_text = "\U0001F6CD\uFE0F Your order has been placed."
    elif order.status == "Preparing":
        eta = "20 minutes"
        message_text = "\U0001F468\u200D\U0001F373 Your food is being prepared."
    elif order.status == "Out for Delivery":
        eta = "10 minutes"
        message_text = "\U0001F6F5 Your order is out for delivery."
    else:
        return Response(
            {"reply": "\u2705 Your order has already been delivered."},
            status=status.HTTP_200_OK,
        )

    return Response(
        {
            "reply": (
                f"{message_text}\n\n"
                f"\u23F1\uFE0F Estimated delivery time: {eta}"
            )
        },
        status=status.HTTP_200_OK,
    )


def handle_book_table(customer_id, date_text, time_text, guests_text):
    if not customer_id:
        return Response(
            {"reply": "Please login first to book a table."},
            status=status.HTTP_200_OK,
        )

    customer = UserProfile.objects.filter(id=customer_id).first()

    if not customer:
        return Response(
            {"reply": "Customer account not found."}, status=status.HTTP_200_OK
        )

    restaurant = Restaurant.objects.first()

    if not restaurant:
        return Response(
            {"reply": "Sorry, we can't take bookings right now. Please try again later."},
            status=status.HTTP_200_OK,
        )

    missing = []
    if not date_text:
        missing.append("date")
    if not time_text:
        missing.append("time")
    if not guests_text:
        missing.append("number of guests")

    if missing:
        return Response(
            {
                "reply": (
                    f"To book a table, please tell me the {', '.join(missing)}. "
                    "For example: 'book a table tomorrow at 8pm for 4 people'."
                )
            },
            status=status.HTTP_200_OK,
        )

    parsed_date = parse_booking_date(date_text)
    parsed_time = parse_booking_time(_normalize_time_text(time_text))

    if not parsed_date:
        return Response(
            {"reply": f"Sorry, I couldn't understand the date '{date_text}'. Try 'today', 'tomorrow', a weekday name, or YYYY-MM-DD."},
            status=status.HTTP_200_OK,
        )

    if not parsed_time:
        return Response(
            {"reply": f"Sorry, I couldn't understand the time '{time_text}'. Try something like '8 PM' or '20:00'."},
            status=status.HTTP_200_OK,
        )

    try:
        guests = int(guests_text)
    except (TypeError, ValueError):
        guests = 1

    # PDF requirement: "Streamline private event / large party reservations
    # with food and beverage options" -- large groups get flagged instead
    # of silently booking a normal table.
    seating_capacity = getattr(restaurant, "seating_capacity", None)
    LARGE_PARTY_THRESHOLD = 12

    if guests >= LARGE_PARTY_THRESHOLD or (
        seating_capacity and guests > int(seating_capacity) * 0.5
    ):
        # FIX: this used to fall through to the model's default status
        # ("Confirmed"), which silently auto-confirmed a booking that the
        # reply text claimed still "needs manual confirmation." Set it to
        # Pending so the two are consistent.
        booking = Booking.objects.create(
            customer=customer,
            restaurant=restaurant,
            booking_date=parsed_date,
            booking_time=parsed_time,
            guests=guests,
            status="Pending",
            special_request="Large party / private event -- needs manual confirmation.",
        )

        return Response(
            {
                "reply": (
                    "\U0001F389 That's a large group! I've logged a request for:\n\n"
                    f"\U0001F4C5 Date: {booking.booking_date}\n"
                    f"\U0001F552 Time: {booking.booking_time}\n"
                    f"\U0001F465 Guests: {booking.guests}\n\n"
                    "Our team will reach out to confirm availability and discuss "
                    f"food & beverage options for your event. You can also call us at {restaurant.phone}."
                )
            },
            status=status.HTTP_201_CREATED,
        )

    booking = Booking.objects.create(
        customer=customer,
        restaurant=restaurant,
        booking_date=parsed_date,
        booking_time=parsed_time,
        guests=guests,
        special_request="",
    )

    return Response(
        {
            "reply": (
                "\u2705 Your table has been booked!\n\n"
                f"\U0001F4C5 Date: {booking.booking_date}\n"
                f"\U0001F552 Time: {booking.booking_time}\n"
                f"\U0001F465 Guests: {booking.guests}"
            )
        },
        status=status.HTTP_201_CREATED,
    )


def handle_modify_booking(customer_id, date_text, time_text, guests_text):
    if not customer_id:
        return Response({"reply": "Please login first."}, status=status.HTTP_200_OK)

    customer = UserProfile.objects.filter(id=customer_id).first()

    if not customer:
        return Response(
            {"reply": "Customer account not found."}, status=status.HTTP_200_OK
        )

    # FIX: this previously only matched status="Confirmed", so a large
    # party booking sitting at "Pending" (see handle_book_table) could
    # never be found or modified here.
    booking = (
        Booking.objects.filter(customer=customer, status__in=["Confirmed", "Pending"])
        .order_by("-created_at")
        .first()
    )

    if not booking:
        return Response(
            {"reply": "You don't have any booking to modify."},
            status=status.HTTP_200_OK,
        )

    if not date_text and not time_text and not guests_text:
        return Response(
            {
                "reply": (
                    "What would you like to change about your booking? "
                    "You can update the date, time, or number of guests -- "
                    "e.g. 'change my booking to 9 PM' or "
                    "'increase my booking to 6 people'."
                )
            },
            status=status.HTTP_200_OK,
        )

    if date_text:
        parsed_date = parse_booking_date(date_text)
        if parsed_date:
            booking.booking_date = parsed_date

    if time_text:
        parsed_time = parse_booking_time(_normalize_time_text(time_text))
        if parsed_time:
            booking.booking_time = parsed_time

    if guests_text:
        try:
            booking.guests = int(guests_text)
        except (TypeError, ValueError):
            pass

    booking.save()

    return Response(
        {
            "reply": (
                "\u2705 Your booking has been updated successfully!\n\n"
                f"\U0001F4C5 Date: {booking.booking_date}\n"
                f"\U0001F552 Time: {booking.booking_time}\n"
                f"\U0001F465 Guests: {booking.guests}"
            )
        },
        status=status.HTTP_200_OK,
    )


def handle_cancel_booking(customer_id):
    if not customer_id:
        return Response({"reply": "Please login first."}, status=status.HTTP_200_OK)

    customer = UserProfile.objects.filter(id=customer_id).first()

    if not customer:
        return Response(
            {"reply": "Customer account not found."}, status=status.HTTP_200_OK
        )

    # FIX: same Pending/Confirmed gap as handle_modify_booking above.
    booking = (
        Booking.objects.filter(customer=customer, status__in=["Confirmed", "Pending"])
        .order_by("-created_at")
        .first()
    )

    if not booking:
        return Response(
            {"reply": "You don't have any active booking to cancel."},
            status=status.HTTP_200_OK,
        )

    booking.status = "Cancelled"
    booking.save()

    return Response(
        {
            "reply": (
                "\u274C Your booking has been cancelled successfully.\n\n"
                f"\U0001F4C5 Date: {booking.booking_date}\n"
                f"\U0001F552 Time: {booking.booking_time}"
            )
        },
        status=status.HTTP_200_OK,
    )


def handle_mood_recommendation(message_lower):
    for mood, (phrases, categories) in _MOOD_CATEGORY_MAP.items():
        if any(phrase in message_lower for phrase in phrases):
            if mood == "spicy":
                items = MenuItem.objects.filter(is_spicy=True, is_available=True)[:4]
            else:
                items = MenuItem.objects.filter(
                    category__in=categories, is_available=True
                )[:4]

            # FIX: this used to `break` here, which fell through to
            # detect_fast_path_response() returning None and letting the
            # request reach the LLM -- which then hallucinated dish names
            # that don't exist in the menu. A recognized mood with no
            # matching stock must be answered here, deterministically,
            # never handed off to Ollama.
            if not items:
                return Response(
                    {
                        "reply": (
                            "Sorry, I don't have anything matching that "
                            "mood on the menu right now. Want me to show "
                            "you the full menu instead?"
                        )
                    },
                    status=status.HTTP_200_OK,
                )

            reply = "\U0001F60B Based on your mood, here's what I'd suggest:\n\n"
            for item in items:
                reply += f"\u2022 {item.name} - \u20B9{item.price}\n"

            return Response({"reply": reply}, status=status.HTTP_200_OK)

    return None


def handle_submit_feedback(customer_id, message, message_lower):
    if not customer_id:
        return Response(
            {"reply": "Please login first so I can log your feedback."},
            status=status.HTTP_200_OK,
        )

    customer = UserProfile.objects.filter(id=customer_id).first()

    if not customer:
        return Response(
            {"reply": "Customer account not found."}, status=status.HTTP_200_OK
        )

    last_order = (
        Order.objects.filter(customer=customer).order_by("-created_at").first()
    )

    if not last_order:
        return Response(
            {
                "reply": (
                    "You'll need to place an order before you can leave "
                    "feedback -- once you've ordered, just tell me how it went!"
                )
            },
            status=status.HTTP_200_OK,
        )

    rating_match = _RATING_RE.search(message_lower)

    if not rating_match:
        return Response(
            {
                "reply": (
                    "\u2B50 I'd love your feedback! Please rate your last order "
                    "from 1 to 5 stars, e.g. 'feedback 5 stars, loved the biryani'."
                )
            },
            status=status.HTTP_200_OK,
        )

    rating = int(rating_match.group(1))

    payload = {
        "customer": customer.id,
        "order": last_order.id,
        "rating": rating,
        "review": message.strip(),
    }

    serializer = ReviewSerializer(data=payload)

    if serializer.is_valid():
        serializer.save()
        return Response(
            {
                "reply": (
                    f"\U0001F64F Thanks for the {rating}-star feedback! "
                    "We really appreciate it."
                )
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(
        {
            "reply": (
                "Thanks! I couldn't save that automatically "
                f"({serializer.errors}), but your feedback has been noted."
            )
        },
        status=status.HTTP_200_OK,
    )


def handle_checkout_cart(customer_id):
    """
    Prepare the customer's cart for checkout.

    This function does NOT create an order and does NOT clear the cart.
    The actual order should only be created after the customer confirms
    delivery details and payment on the checkout page.
    """

    if not customer_id:
        return Response(
            {
                "reply": "Please login first to continue to checkout.",
                "action": "GO_TO_CHECKOUT",
            },
            status=status.HTTP_200_OK,
        )

    customer = UserProfile.objects.filter(id=customer_id).first()

    if not customer:
        return Response(
            {"reply": "Customer account not found."},
            status=status.HTTP_200_OK,
        )

    cart = Cart.objects.filter(customer=customer).first()

    if not cart or not cart.items.exists():
        return Response(
            {
                "reply": "Your cart is empty. Add some items before checking out."
            },
            status=status.HTTP_200_OK,
        )

    # Check whether any cart item became unavailable
    unavailable = [
        cart_item
        for cart_item in cart.items.all()
        if not cart_item.menu_item.is_available
    ]

    if unavailable:
        names = ", ".join(
            cart_item.menu_item.name for cart_item in unavailable
        )

        return Response(
            {
                "reply": (
                    f"Sorry, these items are no longer available: {names}. "
                    "Please remove them from your cart before checking out."
                )
            },
            status=status.HTTP_200_OK,
        )

    # Build cart summary without creating an order
    total = 0
    lines = []

    for cart_item in cart.items.all():
        subtotal = float(cart_item.menu_item.price) * cart_item.quantity
        total += subtotal

        lines.append(
            f"{cart_item.quantity} x {cart_item.menu_item.name} "
            f"- ₹{subtotal:.2f}"
        )

    reply = (
        "🛒 Your cart is ready for checkout!\n\n"
        + "\n".join(lines)
        + f"\n\nTotal: ₹{total:.2f}\n\n"
        + "Please continue to checkout to enter your delivery details "
          "and choose your payment method."
    )

    return Response(
        {
            "reply": reply,
            "total_price": total,
            "action": "GO_TO_CHECKOUT",
        },
        status=status.HTTP_200_OK,
    )

def handle_join_waitlist(customer_id, message_lower):
    if not customer_id:
        return Response(
            {"reply": "Please login first to join the waitlist."},
            status=status.HTTP_200_OK,
        )

    customer = UserProfile.objects.filter(id=customer_id).first()

    if not customer:
        return Response(
            {"reply": "Customer account not found."}, status=status.HTTP_200_OK
        )

    restaurant = Restaurant.objects.first()

    if not restaurant:
        return Response(
            {"reply": "Sorry, the waitlist isn't available right now."},
            status=status.HTTP_200_OK,
        )

    existing = Waitlist.objects.filter(
        customer=customer, status="Waiting"
    ).first()

    if existing:
        position = Waitlist.objects.filter(
            restaurant=existing.restaurant,
            status="Waiting",
            joined_at__lte=existing.joined_at,
        ).count()
        return Response(
            {"reply": f"You're already on the waitlist -- you're #{position} in line."},
            status=status.HTTP_200_OK,
        )

    guests_match = _GUESTS_RE.search(message_lower)
    party_size = 1
    if guests_match:
        party_size = int(guests_match.group(1) or guests_match.group(2))
    else:
        number_match = re.search(r"\b(\d+)\b", message_lower)
        if number_match:
            party_size = int(number_match.group(1))

    entry = Waitlist.objects.create(
        customer=customer, restaurant=restaurant, party_size=party_size
    )

    position = Waitlist.objects.filter(
        restaurant=restaurant, status="Waiting", joined_at__lte=entry.joined_at
    ).count()

    return Response(
        {
            "reply": (
                f"\U0001F4CB You're on the waitlist for a party of {party_size}. "
                f"You're #{position} in line -- we'll let you know when your table "
                "is ready."
            )
        },
        status=status.HTTP_201_CREATED,
    )


def handle_waitlist_status(customer_id):
    if not customer_id:
        return Response({"reply": "Please login first."}, status=status.HTTP_200_OK)

    entry = (
        Waitlist.objects.filter(customer_id=customer_id, status="Waiting")
        .order_by("-joined_at")
        .first()
    )

    if not entry:
        return Response(
            {"reply": "You're not currently on the waitlist."},
            status=status.HTTP_200_OK,
        )

    position = Waitlist.objects.filter(
        restaurant=entry.restaurant, status="Waiting", joined_at__lte=entry.joined_at
    ).count()

    return Response(
        {"reply": f"\U0001F4CB You're #{position} in line for a party of {entry.party_size}."},
        status=status.HTTP_200_OK,
    )


def handle_leave_waitlist(customer_id):
    if not customer_id:
        return Response({"reply": "Please login first."}, status=status.HTTP_200_OK)

    entry = (
        Waitlist.objects.filter(customer_id=customer_id, status="Waiting")
        .order_by("-joined_at")
        .first()
    )

    if not entry:
        return Response(
            {"reply": "You're not currently on a waitlist."},
            status=status.HTTP_200_OK,
        )

    entry.status = "Cancelled"
    entry.save()

    return Response(
        {"reply": "You've been removed from the waitlist."},
        status=status.HTTP_200_OK,
    )


def detect_fast_path_response(message, message_lower, customer_id):
    """
    Deterministic, regex + DB based short-circuit for the chatbot's core
    actions. Runs BEFORE the LLM is called.
    """

    if any(keyword in message_lower for keyword in _CANCEL_BOOKING_KEYWORDS):
        return handle_cancel_booking(customer_id)

    if any(keyword in message_lower for keyword in _LEAVE_WAITLIST_KEYWORDS):
        return handle_leave_waitlist(customer_id)

    if any(keyword in message_lower for keyword in _WAITLIST_STATUS_KEYWORDS):
        return handle_waitlist_status(customer_id)

    if any(keyword in message_lower for keyword in _JOIN_WAITLIST_KEYWORDS):
        return handle_join_waitlist(customer_id, message_lower)

    if any(keyword in message_lower for keyword in _MODIFY_BOOKING_KEYWORDS):
        date_text, time_text, guests_text = _extract_booking_details(message_lower)
        return handle_modify_booking(customer_id, date_text, time_text, guests_text)

    if any(keyword in message_lower for keyword in _BOOK_TABLE_KEYWORDS):
        date_text, time_text, guests_text = _extract_booking_details(message_lower)
        return handle_book_table(customer_id, date_text, time_text, guests_text)

    if any(keyword in message_lower for keyword in _CHECKOUT_KEYWORDS):
        return handle_checkout_cart(customer_id)

    if any(keyword in message_lower for keyword in _FEEDBACK_KEYWORDS):
        return handle_submit_feedback(customer_id, message, message_lower)

    if any(keyword in message_lower for keyword in _TRACKING_KEYWORDS):
        return handle_delivery_eta(customer_id)

    if any(keyword in message_lower for keyword in _REORDER_KEYWORDS):
        return handle_reorder_last_order(customer_id)

    if _MOOD_TRIGGER_RE.search(message_lower) or _mood_phrase_present(message_lower):
        mood_response = handle_mood_recommendation(message_lower)
        if mood_response is not None:
            return mood_response

    if _REMOVE_TRIGGER_RE.search(message_lower):
        menu_items = list(MenuItem.objects.filter(is_available=True))
        matches = _find_all_menu_items_in_message(message_lower, menu_items)

        if matches:
            start, _end, menu_item = matches[0]

            if _ALL_KEYWORD_RE.search(message_lower):
                quantity_str = "ALL"
            else:
                qty = _quantity_before(message_lower, start, default=None)
                quantity_str = str(qty) if qty else "ALL"

            return handle_remove_from_cart(customer_id, menu_item.name, quantity_str)

    if _ADD_TRIGGER_RE.search(message_lower):
        menu_items = list(MenuItem.objects.filter(is_available=True))
        matches = _find_all_menu_items_in_message(message_lower, menu_items)

        if matches:
            single_item = len(matches) == 1
            shared_customization = (
                _extract_customization(message) if single_item else ""
            )

            item_names = []
            quantities = []
            customizations = []

            for start, _end, menu_item in matches:
                item_names.append(menu_item.name)
                quantities.append(_quantity_before(message_lower, start))
                customizations.append(shared_customization or "NONE")

            return handle_add_to_cart(
                customer_id, item_names, quantities, customizations
            )

    return None


# ==========================================
# FOODBOT AI CHATBOT
# ==========================================

@api_view(["POST"])
def chatbot(request):
    message = request.data.get("message")
    customer_id = request.data.get("customer_id")

    if not message:
        return Response(
            {"reply": "Please enter a message."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    message_lower = message.lower().strip()

    # =====================================
    # QUICK COMMAND : SHOW CART
    # =====================================

    if "show cart" in message_lower or "my cart" in message_lower:

        if not customer_id:
            return Response({
                "reply": "Please login first."
            })

        cart = Cart.objects.filter(customer_id=customer_id).first()

        if not cart or not cart.items.exists():
            return Response({
                "reply": "\U0001F6D2 Your cart is empty."
            })

        reply = "\U0001F6D2 Your Cart\n\n"

        total = 0

        for item in cart.items.all():
            subtotal = float(item.menu_item.price) * item.quantity
            total += subtotal

            reply += (
                f"\u2022 {item.menu_item.name} x {item.quantity}"
                f" - \u20B9{subtotal:.2f}\n"
            )

        reply += f"\nTotal : \u20B9{total:.2f}"

        return Response({
            "reply": reply
        })

    # =====================================
    # FAST PATH : DETERMINISTIC ACTION DETECTION
    # =====================================

    fast_path_response = detect_fast_path_response(
        message, message_lower, customer_id
    )

    if fast_path_response is not None:
        return fast_path_response

    try:
        # =====================================
        # RESTAURANT INFORMATION
        # =====================================

        restaurant = Restaurant.objects.first()

        if restaurant:
            restaurant_name = restaurant.name
            brand = restaurant.brand
            cuisine = restaurant.cuisine
            restaurant_type = restaurant.type
            description = restaurant.description

            owner_name = restaurant.owner_name
            phone = restaurant.phone
            email = restaurant.email

            opening_time = (
                restaurant.open_time.strftime("%I:%M %p")
                if restaurant.open_time
                else "Not Available"
            )

            closing_time = (
                restaurant.close_time.strftime("%I:%M %p")
                if restaurant.close_time
                else "Not Available"
            )

            prep_time = restaurant.prep_time
            delivery_radius = restaurant.delivery_radius_km
            seating_capacity = restaurant.seating_capacity

            gstin = restaurant.gstin
            fssai = restaurant.fssai

            dietary_options = (
                ", ".join(restaurant.dietary_options_offered)
                if restaurant.dietary_options_offered
                else "Not Available"
            )

            payment_methods = (
                ", ".join(restaurant.payment_methods_offered)
                if restaurant.payment_methods_offered
                else "Not Available"
            )

            address = (
                f"{restaurant.address}, "
                f"{restaurant.city}, "
                f"{restaurant.state}"
            )

            # PDF requirement: "Handle FAQs: delivery areas, operating
            # hours, payment methods, parking".
            parking_info = restaurant.parking_info or "Not Available"
            delivery_areas = (
                ", ".join(restaurant.delivery_areas)
                if restaurant.delivery_areas
                else "Not Available"
            )

        else:
            restaurant_name = "FoodBot Restaurant"
            brand = "Not Available"
            cuisine = "Not Available"
            restaurant_type = "Not Available"
            description = "Not Available"

            owner_name = "Not Available"
            phone = "Not Available"
            email = "Not Available"

            opening_time = "Not Available"
            closing_time = "Not Available"

            prep_time = "Not Available"
            delivery_radius = "Not Available"
            seating_capacity = "Not Available"

            gstin = "Not Available"
            fssai = "Not Available"

            dietary_options = "Not Available"
            payment_methods = "Not Available"

            address = "Not Available"
            parking_info = "Not Available"
            delivery_areas = "Not Available"

        # =====================================
        # WELCOME MESSAGE
        # =====================================

        greetings = [
            "hi",
            "hello",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
        ]

        if message_lower in greetings:
            return Response(
                {
                    "reply": (
                        f"\U0001F44B Hello! Welcome to {restaurant_name}!\n\n"
                        "I'm FoodBot, your AI restaurant assistant.\n\n"
                        "I can help you with:\n\n"
                        "\U0001F355 Browse our menu\n"
                        "\U0001F354 Recommend delicious dishes\n"
                        "\U0001F6D2 Add food to your cart\n"
                        "\U0001F4C5 Book tables\n"
                        "\U0001F4E6 Track your orders\n"
                        "\U0001F389 Show today's offers\n\n"
                        "How can I help you today?"
                    )
                },
                status=status.HTTP_200_OK,
            )

        # =====================================
        # MENU
        # =====================================

        menu_items = MenuItem.objects.filter(is_available=True)

        if menu_items.exists():
            menu_lines = []

            for item in menu_items:
                if item.is_vegan:
                    diet_tag = "Vegan"
                elif item.is_veg:
                    diet_tag = "Veg"
                else:
                    diet_tag = "Non-Veg"

                spice_tag = " | Spicy" if item.is_spicy else ""

                allergens = ", ".join(item.allergens) if item.allergens else "None listed"
                calories = item.calories if item.calories else "N/A"

                menu_lines.append(
                    f"- {item.name} | {item.category} | \u20B9{item.price} | "
                    f"{diet_tag}{spice_tag} | Allergens: {allergens} | Calories: {calories}"
                )

            menu_text = "\n".join(menu_lines)
        else:
            menu_text = "No menu items available."

        # =====================================
        # PROMOTIONS
        # =====================================

        promotions = Promotion.objects.filter(is_active=True)

        if promotions.exists():
            promotions_text = "\n".join(
                [
                    f"- {promo.title} | {promo.description} | "
                    f"{promo.discount} | Valid Until: {promo.valid_until}"
                    for promo in promotions
                ]
            )
        else:
            promotions_text = "No active promotions available."

        # =====================================
        # CUSTOMER'S LATEST ORDER
        # =====================================

        order_information = "No previous orders."

        if customer_id:
            latest_order = (
                Order.objects.filter(customer_id=customer_id)
                .order_by("-created_at")
                .first()
            )

            if latest_order:
                order_items = OrderItem.objects.filter(order=latest_order)

                items_text = "\n".join(
                    [
                        f"- {item.menu_item.name} x {item.quantity}"
                        for item in order_items
                    ]
                )

                order_information = f"""
Latest Order ID : {latest_order.id}

Status : {latest_order.status}

Total Price : \u20B9{latest_order.total_price}

Items:
{items_text}
"""

        # =====================================
        # CUSTOMER BOOKINGS
        # =====================================

        booking_information = "No bookings."

        if customer_id:
            latest_booking = (
                Booking.objects.filter(customer_id=customer_id)
                .order_by("-created_at")
                .first()
            )

            if latest_booking:
                booking_information = f"""
Booking Date : {latest_booking.booking_date}

Booking Time : {latest_booking.booking_time}

Status : {latest_booking.status}

Guests : {latest_booking.guests}

Special Request :
{latest_booking.special_request}
"""

        # =====================================
        # CUSTOMER CART
        # =====================================

        cart_information = "Cart is empty."

        if customer_id:
            cart = Cart.objects.filter(customer_id=customer_id).first()

            if cart:
                items = CartItem.objects.filter(cart=cart)

                if items.exists():
                    cart_information = "\n".join(
                        [
                            f"- {i.menu_item.name} x {i.quantity}"
                            for i in items
                        ]
                    )

        # =========================
        # PROMPT
        # =========================

        prompt = f"""
You are FoodBot AI, the official virtual assistant of {restaurant_name}.

====================================================
ROLE
====================================================

You are an intelligent AI-powered restaurant assistant.

Your primary responsibility is to understand the customer's intention, even if they do not use exact commands or keywords.

Think like an experienced restaurant staff member.

Customers may ask questions in many different ways.

Understand what they MEAN instead of searching for exact words.

Always be:

- Friendly
- Professional
- Helpful
- Conversational
- Accurate

Your responsibilities include helping customers with:

- Browsing the menu
- Explaining dishes
- Food recommendations (including mood-based, e.g. "something comforting")
- Vegetarian/Vegan food
- Allergens
- Calories
- Prices
- Food customization
- Promotions
- Discounts
- Offers
- Cart management
- Previous orders
- Checkout and payment
- Table booking (including large parties / private events)
- Walk-in waitlist
- Booking modification
- Booking cancellation
- Order tracking
- Delivery ETA
- Post-meal feedback and ratings
- Restaurant information
- FAQs (delivery areas, hours, payment methods, parking)

Always answer naturally like a real restaurant assistant.

Only perform system ACTIONS when the customer clearly wants to perform an operation.

If the customer is simply asking for information, NEVER return an ACTION.

====================================================
RESTAURANT INFORMATION
====================================================

Restaurant Name: {restaurant_name}
Brand: {brand}
Cuisine: {cuisine}
Restaurant Type: {restaurant_type}
Description: {description}
Owner: {owner_name}
Phone: {phone}
Email: {email}
Address: {address}
Opening Time: {opening_time}
Closing Time: {closing_time}
Average Preparation Time: {prep_time} minutes
Delivery Radius: {delivery_radius} km
Seating Capacity: {seating_capacity}
GSTIN: {gstin}
FSSAI: {fssai}
Dietary Options: {dietary_options}
Payment Methods: {payment_methods}
Parking: {parking_info}
Delivery Areas: {delivery_areas}

====================================================
AVAILABLE MENU
====================================================

{menu_text}

====================================================
ACTIVE PROMOTIONS
====================================================

{promotions_text}

====================================================
CUSTOMER'S LATEST ORDER
====================================================

{order_information}

====================================================
CUSTOMER BOOKINGS
====================================================

{booking_information}

====================================================
CUSTOMER CART
====================================================

{cart_information}

====================================================
AVAILABLE ACTIONS
====================================================

The chatbot has two responsibilities:

1. Answer customer questions naturally.
2. Trigger an ACTION only when the customer wants the system to perform an operation.

Never return an ACTION unless it is clearly required.

Valid actions: ADD_TO_CART, REMOVE_FROM_CART, BOOK_TABLE, MODIFY_BOOKING,
CANCEL_BOOKING, DELIVERY_ETA, GO_TO_CHECKOUT, REORDER_LAST_ORDER,
SUBMIT_FEEDBACK, JOIN_WAITLIST, WAITLIST_STATUS, LEAVE_WAITLIST.

Use ONLY the information provided in this prompt. Never invent menu items,
prices, restaurant details, promotions, bookings, orders, or cart items.

Customer:
{message}
"""

        # =====================================
        # ASK QWEN THROUGH HUGGING FACE
        # =====================================

        hf_token = os.getenv("HF_TOKEN")

        response = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
             headers={
                 "Authorization": f"Bearer {hf_token}",
                 "Content-Type": "application/json",
             },
             json={
                 "model": "Qwen/Qwen2.5-7B-Instruct",
                 "messages": [
                     {
                         "role": "user",
                         "content": prompt,
                     }
                 ],
                 "temperature": 0.1,
                 "max_tokens": 300,
             },
             timeout=60,
)

        response.raise_for_status()

        reply = response.json()["choices"][0]["message"]["content"].strip()
        

        # =====================================
        # AI ACTION : ADD TO CART
        # =====================================

        if re.search(r"ACTION\s*:\s*ADD_TO_CART", reply, re.IGNORECASE):

            items = [i.strip() for i in re.findall(r"ITEM:\s*(.+)", reply)]
            quantities = re.findall(r"QUANTITY:\s*(\d+)", reply)
            customizations = [
                c.strip() for c in re.findall(r"CUSTOMIZATION:\s*(.+)", reply)
            ]

            return handle_add_to_cart(
                customer_id, items, quantities, customizations
            )

        # =====================================
        # AI ACTION : REMOVE FROM CART
        # =====================================

        if re.search(r"ACTION\s*:\s*REMOVE_FROM_CART", reply, re.IGNORECASE):

            item_match = re.search(r"ITEM:\s*(.+)", reply)
            qty_match = re.search(r"QUANTITY:\s*(.+)", reply)

            item_name = item_match.group(1).strip() if item_match else None
            quantity_str = qty_match.group(1).strip() if qty_match else "ALL"

            return handle_remove_from_cart(customer_id, item_name, quantity_str)

        # =====================================
        # AI ACTION : REORDER LAST ORDER
        # =====================================

        if re.search(r"ACTION\s*:\s*REORDER_LAST_ORDER", reply, re.IGNORECASE):
            return handle_reorder_last_order(customer_id)

        # =====================================
        # AI ACTION : GO TO CHECKOUT
        # =====================================

        if re.search(r"ACTION\s*:\s*GO_TO_CHECKOUT", reply, re.IGNORECASE):
            return handle_checkout_cart(customer_id)

        # =====================================
        # AI ACTION : SUBMIT FEEDBACK
        # =====================================

        if re.search(r"ACTION\s*:\s*SUBMIT_FEEDBACK", reply, re.IGNORECASE):
            return handle_submit_feedback(customer_id, message, message_lower)

        # =====================================
        # AI ACTION : WAITLIST
        # =====================================

        if re.search(r"ACTION\s*:\s*JOIN_WAITLIST", reply, re.IGNORECASE):
            return handle_join_waitlist(customer_id, message_lower)

        if re.search(r"ACTION\s*:\s*WAITLIST_STATUS", reply, re.IGNORECASE):
            return handle_waitlist_status(customer_id)

        if re.search(r"ACTION\s*:\s*LEAVE_WAITLIST", reply, re.IGNORECASE):
            return handle_leave_waitlist(customer_id)

        # =====================================
        # AI ACTION : BOOK TABLE
        # =====================================

        if re.search(r"ACTION\s*:\s*BOOK_TABLE", reply, re.IGNORECASE):

            date_match = re.search(r"DATE:\s*(.+)", reply)
            time_match = re.search(r"TIME:\s*(.+)", reply)
            guest_match = re.search(r"GUESTS:\s*(.+)", reply)

            date_text = date_match.group(1).strip() if date_match else None
            time_text = time_match.group(1).strip() if time_match else None
            guests_text = guest_match.group(1).strip() if guest_match else None

            return handle_book_table(customer_id, date_text, time_text, guests_text)

        # =====================================
        # AI ACTION : MODIFY BOOKING
        # =====================================

        if re.search(r"ACTION\s*:\s*MODIFY_BOOKING", reply, re.IGNORECASE):

            date_match = re.search(r"DATE:\s*(.+)", reply)
            time_match = re.search(r"TIME:\s*(.+)", reply)
            guest_match = re.search(r"GUESTS:\s*(.+)", reply)

            date_text = date_match.group(1).strip() if date_match else None
            time_text = time_match.group(1).strip() if time_match else None
            guests_text = guest_match.group(1).strip() if guest_match else None

            if date_text and date_text.upper() == "SAME":
                date_text = None
            if time_text and time_text.upper() == "SAME":
                time_text = None
            if guests_text and guests_text.upper() == "SAME":
                guests_text = None

            return handle_modify_booking(customer_id, date_text, time_text, guests_text)

        # =====================================
        # AI ACTION : CANCEL BOOKING
        # =====================================

        if re.search(r"ACTION\s*:\s*CANCEL_BOOKING", reply, re.IGNORECASE):
            return handle_cancel_booking(customer_id)

        # =====================================
        # AI ACTION : DELIVERY ETA
        # =====================================

        if re.search(r"ACTION\s*:\s*DELIVERY_ETA", reply, re.IGNORECASE):
            return handle_delivery_eta(customer_id)

        # =====================================
        # DEFAULT CHATBOT RESPONSE
        # =====================================

        return Response(
            {
                "reply": reply
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"reply": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )