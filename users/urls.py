from django.urls import path
from . import views


urlpatterns = [

    # ==========================================
    # CUSTOMER
    # ==========================================
    path(
        "register/customer/",
        views.register_customer,
        name="register_customer",
    ),

    # ==========================================
    # RESTAURANT
    # ==========================================
    path(
        "register/restaurant/",
        views.register_restaurant,
        name="register_restaurant",
    ),

    # ==========================================
    # LOGIN
    # ==========================================
    path(
        "login/",
        views.login_customer,
        name="login_customer",
    ),

    # ==========================================
    # MENU API
    # ==========================================
    path(
        "menu/",
        views.get_menu,
        name="get_menu",
    ),

    path(
        "menu/recommendations/",
        views.get_recommendations,
        name="get_recommendations",
    ),

    path(
        "menu/previous-recommendations/",
        views.previous_order_recommendations,
        name="previous_order_recommendations",
    ),

    # ==========================================
    # CREATE ORDER
    # ==========================================
    path(
        "orders/",
        views.create_order,
        name="create_order",
    ),

    # ==========================================
    # GET CUSTOMER ORDERS
    # ==========================================
    path(
        "orders/list/",
        views.get_orders,
        name="get_orders",
    ),

    # ==========================================
    # SUBMIT REVIEW
    # ==========================================
    path(
        "review/",
        views.submit_review,
        name="submit_review",
    ),

    # ==========================================
    # PROMOTIONS
    # ==========================================
    path(
        "promotions/",
        views.get_promotions,
        name="get_promotions",
    ),

    # ==========================================
    # CART
    # ==========================================
    path(
        "cart/add/",
        views.add_to_cart,
        name="add_to_cart",
    ),

    path(
        "cart/view/",
        views.view_cart,
        name="view_cart",
    ),

    path(
        "cart/remove/",
        views.remove_from_cart,
        name="remove_from_cart",
    ),

    path(
        "cart/update/",
        views.update_cart,
        name="update_cart",
    ),

    path(
        "cart/clear/",
        views.clear_cart,
        name="clear_cart",
    ),

    # ==========================================
    # BOOKING
    # ==========================================
    path(
        "booking/",
        views.book_table,
        name="book_table",
    ),

    path(
        "booking/list/",
        views.get_bookings,
        name="get_bookings",
    ),

    # ==========================================
    # WAITLIST (NEW -- views.py defines these but
    # they weren't wired up here yet)
    # ==========================================
    path(
        "waitlist/join/",
        views.join_waitlist,
        name="join_waitlist",
    ),

    path(
        "waitlist/status/",
        views.waitlist_status,
        name="waitlist_status",
    ),

    path(
        "waitlist/leave/",
        views.leave_waitlist,
        name="leave_waitlist",
    ),

    # ==========================================
    # FOODBOT AI CHATBOT
    # ==========================================
    path(
        "chat/",
        views.chatbot,
        name="chatbot",
    ),

]