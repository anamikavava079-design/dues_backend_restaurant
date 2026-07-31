import hashlib
from rest_framework import serializers
from .models import (
    UserProfile,
    Restaurant,
    MenuItem,
    CustomizationOption,
    Order,
    OrderItem,
    Cart,
    CartItem,
    Booking,
    Review,
    Promotion,
    Waitlist,
)


# =====================================
# CUSTOMER REGISTRATION
# =====================================

class CustomerRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    address = serializers.CharField(required=True)
    dietaryPreferences = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )

    class Meta:
        model = UserProfile
        fields = [
            "name",
            "email",
            "phone",
            "password",
            "address",
            "dietaryPreferences",
        ]

    def validate_email(self, value):
        if UserProfile.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return value

    def create(self, validated_data):
        dietary = validated_data.pop("dietaryPreferences", [])
        password = validated_data.pop("password")

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        user = UserProfile.objects.create(
            **validated_data,
            password_hash=password_hash,
            dietary_preferences=dietary,
            role="customer",
        )

        return user


# =====================================
# RESTAURANT REGISTRATION
# =====================================

class RestaurantRegistrationSerializer(serializers.ModelSerializer):
    ownerName = serializers.CharField(source="owner_name")

    openTime = serializers.TimeField(
        source="open_time",
        required=False,
        allow_null=True,
    )

    closeTime = serializers.TimeField(
        source="close_time",
        required=False,
        allow_null=True,
    )

    prepTime = serializers.IntegerField(source="prep_time")

    deliveryRadiusKm = serializers.IntegerField(
        source="delivery_radius_km"
    )

    seatingCapacity = serializers.IntegerField(
        source="seating_capacity",
        required=False,
        allow_null=True,
    )

    dietaryOptionsOffered = serializers.ListField(
        child=serializers.CharField(),
        source="dietary_options_offered",
        required=False,
        default=list,
    )

    channelsToActivate = serializers.ListField(
        child=serializers.CharField(),
        source="channels_to_activate",
        required=False,
        default=list,
    )

    paymentMethodsOffered = serializers.ListField(
        child=serializers.CharField(),
        source="payment_methods_offered",
        required=False,
        default=list,
    )

    # ---- NEW: match the fields added to the Restaurant model so the
    # chatbot's FAQ section (delivery areas / parking) can actually be
    # populated at registration time instead of always reading blank.
    parkingInfo = serializers.CharField(
        source="parking_info",
        required=False,
        allow_blank=True,
        default="",
    )

    deliveryAreas = serializers.ListField(
        child=serializers.CharField(),
        source="delivery_areas",
        required=False,
        default=list,
    )

    class Meta:
        model = Restaurant
        fields = [
            "name",
            "brand",
            "cuisine",
            "type",
            "description",
            "ownerName",
            "phone",
            "email",
            "address",
            "city",
            "state",
            "openTime",
            "closeTime",
            "prepTime",
            "deliveryRadiusKm",
            "seatingCapacity",
            "gstin",
            "fssai",
            "source",
            "dietaryOptionsOffered",
            "channelsToActivate",
            "paymentMethodsOffered",
            "parkingInfo",
            "deliveryAreas",
        ]

    def validate_email(self, value):
        if Restaurant.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A restaurant with this email is already registered."
            )
        return value


# =====================================
# CUSTOMIZATION SERIALIZER
# =====================================

class CustomizationOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomizationOption
        fields = [
            "id",
            "category",
            "option",
            "extra_price",
            "selection_type",
        ]


# =====================================
# MENU SERIALIZER
# =====================================

class MenuItemSerializer(serializers.ModelSerializer):
    customizations = CustomizationOptionSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = MenuItem
        fields = [
            "id",
            "restaurant",
            "name",
            "category",
            "description",
            "price",
            "is_available",
            "is_veg",
            "is_vegan",
            "is_spicy",
            "calories",
            "allergens",
            "image",
            "customizations",
        ]


# =====================================
# ORDER SERIALIZERS
# =====================================

class OrderItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(
        source="menu_item.name",
        read_only=True,
    )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "menu_item",
            "menu_item_name",
            "quantity",
            "price",
            "customization",
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(
        many=True,
        read_only=True,
    )

    customer_name = serializers.CharField(
        source="customer.name",
        read_only=True,
    )

    restaurant_name = serializers.CharField(
        source="restaurant.name",
        read_only=True,
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "customer_name",
            "restaurant",
            "restaurant_name",
            "total_price",
            "status",
            "created_at",
            "items",
        ]


# =====================================
# CART SERIALIZERS
# =====================================

class CartItemSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        source="menu_item.name",
        read_only=True,
    )

    category = serializers.CharField(
        source="menu_item.category",
        read_only=True,
    )

    image = serializers.CharField(
        source="menu_item.image",
        read_only=True,
    )

    price = serializers.DecimalField(
        source="menu_item.price",
        max_digits=8,
        decimal_places=2,
        read_only=True,
    )

    menu_item_id = serializers.IntegerField(
        source="menu_item.id",
        read_only=True,
    )

    class Meta:
        model = CartItem
        fields = [
            "id",
            "menu_item_id",
            "name",
            "category",
            "image",
            "price",
            "quantity",
            "customization",
        ]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(
        many=True,
        read_only=True,
    )

    customer_name = serializers.CharField(
        source="customer.name",
        read_only=True,
    )

    class Meta:
        model = Cart
        fields = [
            "id",
            "customer",
            "customer_name",
            "created_at",
            "items",
        ]


# =====================================
# BOOKING SERIALIZER
# =====================================

class BookingSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.name",
        read_only=True,
    )

    restaurant_name = serializers.CharField(
        source="restaurant.name",
        read_only=True,
    )

    class Meta:
        model = Booking
        fields = [
            "id",
            "customer",
            "customer_name",
            "restaurant",
            "restaurant_name",
            "booking_date",
            "booking_time",
            "guests",
            "special_request",
            "status",
            "created_at",
        ]


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = "__all__"


class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = "__all__"


# =====================================
# WAITLIST SERIALIZER (NEW -- was missing entirely)
# =====================================

class WaitlistSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.name",
        read_only=True,
    )

    restaurant_name = serializers.CharField(
        source="restaurant.name",
        read_only=True,
    )

    class Meta:
        model = Waitlist
        fields = [
            "id",
            "customer",
            "customer_name",
            "restaurant",
            "restaurant_name",
            "party_size",
            "status",
            "joined_at",
        ]