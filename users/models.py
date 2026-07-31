from django.db import models


# ==========================================
# USER PROFILE
# ==========================================

class UserProfile(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, max_length=150)
    phone = models.CharField(max_length=20)
    password_hash = models.CharField(max_length=255)
    address = models.TextField(blank=True, default='')
    dietary_preferences = models.JSONField(default=list, blank=True)

    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('admin', 'Admin'),
        ('support', 'Support'),
    ]

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='customer'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.role})"


# ==========================================
# RESTAURANT
# ==========================================

class Restaurant(models.Model):
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=200, blank=True, null=True)
    cuisine = models.CharField(max_length=100)
    type = models.CharField(max_length=100)
    description = models.TextField()

    owner_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(unique=True, max_length=150)

    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)

    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)

    prep_time = models.IntegerField(
        help_text="Prep time in minutes"
    )

    delivery_radius_km = models.IntegerField()

    seating_capacity = models.IntegerField(
        null=True,
        blank=True
    )

    gstin = models.CharField(
        max_length=50,
        blank=True,
        default=''
    )

    fssai = models.CharField(max_length=50)

    source = models.CharField(
        max_length=100,
        blank=True,
        default=''
    )

    dietary_options_offered = models.JSONField(
        default=list,
        blank=True
    )

    channels_to_activate = models.JSONField(
        default=list,
        blank=True
    )

    payment_methods_offered = models.JSONField(
        default=list,
        blank=True
    )

    # ---- NEW: required by chatbot() FAQ section (PDF requirement:
    # "Handle FAQs: delivery areas, operating hours, payment methods,
    # parking") -- views.py was already reading these but they never
    # existed on the model, causing an AttributeError on every chat call.
    parking_info = models.CharField(max_length=255, blank=True, default='')

    delivery_areas = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.city})"


# ==========================================
# MENU ITEM
# ==========================================

class MenuItem(models.Model):

    CATEGORY_CHOICES = [
        ("Pizza", "Pizza"),
        ("Burger", "Burger"),
        ("Pasta", "Pasta"),
        ("Biryani", "Biryani"),
        ("Dessert", "Dessert"),
        ("Drink", "Drink"),
        ("Salad", "Salad"),
    ]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="menu_items"
    )

    name = models.CharField(max_length=100)

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES
    )

    description = models.TextField(blank=True)

    price = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    is_available = models.BooleanField(default=True)

    is_veg = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_spicy = models.BooleanField(default=False)
    calories = models.PositiveIntegerField(default=0)

    allergens = models.JSONField(
        default=list,
        blank=True
    )

    image = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ==========================================
# FOOD CUSTOMIZATION
# ==========================================
class CustomizationOption(models.Model):
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name="customizations"
    )

    category = models.CharField(max_length=50)

    option = models.CharField(max_length=100)

    extra_price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    selection_type = models.CharField(
        max_length=10,
        choices=[
            ("single", "Single"),
            ("multiple", "Multiple"),
        ],
        default="single",
    )

    def __str__(self):
        return (
            f"{self.menu_item.name} - "
            f"{self.category}: {self.option}"
        )


# ==========================================
# ORDER
# ==========================================

class Order(models.Model):

    STATUS_CHOICES = [
        ("Placed", "Placed"),
        ("Preparing", "Preparing"),
        ("Out for Delivery", "Out for Delivery"),
        ("Delivered", "Delivered"),
        ("Cancelled", "Cancelled"),
    ]

    customer = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="Placed"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Order #{self.id} - {self.customer.name}"


# ==========================================
# ORDER ITEM
# ==========================================

class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField(default=1)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # NOTE: handle_reorder_last_order() in views.py reads
    # order_item.customization via getattr(..., "") as a safe fallback,
    # so this field is optional but recommended -- without it, reordering
    # an item that had a customization (e.g. "No Onion") loses that
    # customization when re-added to the cart.
    customization = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.menu_item.name} x {self.quantity}"


# ==========================================
# CART
# ==========================================

class Cart(models.Model):

    customer = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="cart"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.customer.name}'s Cart"


# ==========================================
# CART ITEM
# ==========================================

class CartItem(models.Model):

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )

    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField(default=1)

    # Stores selected customization options
    customization = models.TextField(
        blank=True,
        default=""
    )

    def __str__(self):
        return f"{self.menu_item.name} x {self.quantity}"


# ==========================================
# BOOKING
# ==========================================

class Booking(models.Model):

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Confirmed", "Confirmed"),
        ("Cancelled", "Cancelled"),
    ]

    customer = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="bookings"
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="bookings"
    )

    booking_date = models.DateField()

    booking_time = models.TimeField()

    guests = models.PositiveIntegerField()

    special_request = models.TextField(
        blank=True,
        default=""
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Confirmed"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.customer.name} - "
            f"{self.booking_date} "
            f"{self.booking_time}"
        )


class Review(models.Model):
    customer = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    rating = models.PositiveIntegerField()

    review = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.name} - {self.rating}⭐"


class Promotion(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    discount = models.CharField(max_length=100, blank=True)
    valid_until = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


# ==========================================
# WAITLIST  (NEW -- was missing entirely)
# ==========================================
# PDF requirement: "Manage walk-in waitlists virtually -- customers join a
# queue and get notified when their table is ready."
# views.py already imports and uses this model (join_waitlist,
# waitlist_status, leave_waitlist, and the chatbot's waitlist handlers)
# but it did not exist yet, which would crash the app on import.

class Waitlist(models.Model):

    STATUS_CHOICES = [
        ("Waiting", "Waiting"),
        ("Notified", "Notified"),
        ("Seated", "Seated"),
        ("Cancelled", "Cancelled"),
    ]

    customer = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="waitlist_entries"
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="waitlist_entries"
    )

    party_size = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Waiting"
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.name} - party of {self.party_size} ({self.status})"