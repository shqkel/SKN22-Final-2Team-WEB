from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem
from products.models import Product


class CartProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "goods_id", "goods_name", "brand_name", "price", "discount_price",
            "rating", "review_count", "thumbnail_url", "product_url",
            "pet_type", "category", "health_concern_tags",
        ]


class CartItemSerializer(serializers.ModelSerializer):
    product = CartProductSerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = ["cart_item_id", "product", "quantity", "added_at"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["cart_id", "items", "total_price", "item_count", "updated_at"]

    def get_total_price(self, obj):
        return sum(
            (item.product.discount_price or item.product.price) * item.quantity
            for item in obj.items.select_related("product").all()
        )

    def get_item_count(self, obj):
        return sum(item.quantity for item in obj.items.all())


class AddCartItemSerializer(serializers.Serializer):
    goods_id = serializers.CharField(max_length=20)
    quantity = serializers.IntegerField(default=1, min_value=1)


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class OrderItemSerializer(serializers.ModelSerializer):
    product = CartProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["order_item_id", "product", "quantity", "price_at_order"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "order_id", "recipient_name", "delivery_address",
            "total_price", "status", "items", "created_at",
        ]


class CreateOrderSerializer(serializers.Serializer):
    recipient_name = serializers.CharField(max_length=100)
    delivery_address = serializers.CharField()
