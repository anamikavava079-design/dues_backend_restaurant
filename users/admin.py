from django.contrib import admin
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
    Promotion,

)

admin.site.register(UserProfile)
admin.site.register(Restaurant)
@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price",
        "is_veg",
        "is_vegan",
        "is_spicy",
        "calories",
        "is_available",
    )

    list_filter = (
        "category",
        "is_veg",
        "is_vegan",
        "is_spicy",
        "is_available",
    )

    search_fields = (
        "name",
        "description",
    )
admin.site.register(CustomizationOption)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Booking)
admin.site.register(Promotion)