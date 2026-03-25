from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product
from .models import Cart, CartItem, Order, OrderItem, UserInteraction
from .serializers import (
    AddCartItemSerializer,
    CartSerializer,
    CreateOrderSerializer,
    OrderSerializer,
    UpdateCartItemSerializer,
)


# ── Cart ─────────────────────────────────────────────────────────────────────


class CartView(APIView):
    """GET: 장바구니 조회 / 비어 있으면 자동 생성"""

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return Response(CartSerializer(cart).data)


class CartItemListView(APIView):
    """POST: 장바구니에 상품 추가"""

    def post(self, request):
        ser = AddCartItemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        goods_id = ser.validated_data["goods_id"]
        quantity = ser.validated_data["quantity"]

        try:
            product = Product.objects.get(goods_id=goods_id)
        except Product.DoesNotExist:
            return Response({"detail": "상품을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        cart, _ = Cart.objects.get_or_create(user=request.user)

        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={"quantity": quantity},
        )
        if not created:
            item.quantity += quantity
            item.save(update_fields=["quantity"])

        return Response(
            CartSerializer(cart).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CartItemDetailView(APIView):
    """PATCH: 수량 변경 / DELETE: 삭제"""

    def _get_item(self, request, cart_item_id):
        try:
            return CartItem.objects.select_related("cart").get(
                cart_item_id=cart_item_id,
                cart__user=request.user,
            )
        except CartItem.DoesNotExist:
            return None

    def patch(self, request, cart_item_id):
        item = self._get_item(request, cart_item_id)
        if not item:
            return Response({"detail": "장바구니 항목을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        ser = UpdateCartItemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        item.quantity = ser.validated_data["quantity"]
        item.save(update_fields=["quantity"])
        return Response(CartSerializer(item.cart).data)

    def delete(self, request, cart_item_id):
        item = self._get_item(request, cart_item_id)
        if not item:
            return Response({"detail": "장바구니 항목을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        cart = item.cart
        item.delete()
        return Response(CartSerializer(cart).data)


# ── Order ────────────────────────────────────────────────────────────────────


class OrderListView(APIView):
    """GET: 주문 목록 / POST: 장바구니 -> 주문 전환"""

    def get(self, request):
        orders = request.user.orders.order_by("-created_at")
        return Response(OrderSerializer(orders, many=True).data)

    @transaction.atomic
    def post(self, request):
        ser = CreateOrderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            cart = Cart.objects.prefetch_related("items__product").get(user=request.user)
        except Cart.DoesNotExist:
            return Response({"detail": "장바구니가 비어 있습니다."}, status=status.HTTP_400_BAD_REQUEST)

        cart_items = list(cart.items.select_related("product").all())
        if not cart_items:
            return Response({"detail": "장바구니가 비어 있습니다."}, status=status.HTTP_400_BAD_REQUEST)

        total = sum(
            (ci.product.discount_price or ci.product.price) * ci.quantity
            for ci in cart_items
        )

        order = Order.objects.create(
            user=request.user,
            recipient_name=ser.validated_data["recipient_name"],
            delivery_address=ser.validated_data["delivery_address"],
            total_price=total,
        )

        order_items = []
        interactions = []
        for ci in cart_items:
            price = ci.product.discount_price or ci.product.price
            order_items.append(OrderItem(
                order=order,
                product=ci.product,
                quantity=ci.quantity,
                price_at_order=price,
            ))
            interactions.append(UserInteraction(
                user=request.user,
                product=ci.product,
                interaction_type="purchase",
                weight=5,
            ))

        OrderItem.objects.bulk_create(order_items)
        UserInteraction.objects.bulk_create(interactions)

        # 장바구니 비우기
        cart.items.all().delete()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    """GET: 주문 상세"""

    def get(self, request, order_id):
        try:
            order = request.user.orders.prefetch_related("items__product").get(order_id=order_id)
        except Order.DoesNotExist:
            return Response({"detail": "주문을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrderSerializer(order).data)


# ── UserInteraction ──────────────────────────────────────────────────────────


class InteractionView(APIView):
    """POST: 상호작용 로깅 (click, cart, purchase, reject)"""

    WEIGHT_MAP = {"click": 1, "cart": 3, "purchase": 5, "reject": -1}

    def post(self, request):
        goods_id = request.data.get("goods_id")
        interaction_type = request.data.get("interaction_type")
        session_id = request.data.get("session_id")

        if not goods_id or interaction_type not in self.WEIGHT_MAP:
            return Response({"detail": "goods_id와 유효한 interaction_type이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(goods_id=goods_id)
        except Product.DoesNotExist:
            return Response({"detail": "상품을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        UserInteraction.objects.create(
            user=request.user,
            product=product,
            session_id=session_id,
            interaction_type=interaction_type,
            weight=self.WEIGHT_MAP[interaction_type],
        )
        return Response({"status": "ok"}, status=status.HTTP_201_CREATED)
