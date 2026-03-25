from django.urls import path
from .views import (
    CartView,
    CartItemListView,
    CartItemDetailView,
    InteractionView,
    OrderDetailView,
    OrderListView,
)

urlpatterns = [
    # Cart
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/", CartItemListView.as_view(), name="cart-item-list"),
    path("cart/items/<uuid:cart_item_id>/", CartItemDetailView.as_view(), name="cart-item-detail"),
    # Orders
    path("orders/", OrderListView.as_view(), name="order-list"),
    path("orders/<uuid:order_id>/", OrderDetailView.as_view(), name="order-detail"),
    # Interactions
    path("interactions/", InteractionView.as_view(), name="interaction"),
]
