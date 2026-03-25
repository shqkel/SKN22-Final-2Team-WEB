from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from orders.models import Cart, CartItem, Order, OrderItem, UserInteraction
from products.models import Product
from users.models import User, UserProfile


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _create_user(email="orders@example.com"):
    user = User.objects.create_user(email=email, password="Password123!")
    UserProfile.objects.create(user=user, nickname=email.split("@")[0])
    return user


def _create_product(goods_id="GI0001", price=10000, discount_price=9000, name="테스트 사료"):
    return Product.objects.create(
        goods_id=goods_id,
        goods_name=name,
        brand_name="테스트 브랜드",
        price=price,
        discount_price=discount_price,
        thumbnail_url="https://example.com/thumb.png",
        product_url="https://example.com/product",
        crawled_at=timezone.now(),
    )


# ── Cart Tests ───────────────────────────────────────────────────────────────


class CartViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _create_user("cart@example.com")
        self.client.force_authenticate(self.user)
        self.product = _create_product()

    def test_get_cart_creates_if_not_exists(self):
        self.assertFalse(Cart.objects.filter(user=self.user).exists())

        response = self.client.get("/api/cart/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Cart.objects.filter(user=self.user).exists())
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["total_price"], 0)
        self.assertEqual(response.data["item_count"], 0)

    def test_get_cart_unauthenticated_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/cart/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CartItemTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _create_user("cart-item@example.com")
        self.client.force_authenticate(self.user)
        self.product1 = _create_product("GI0001", 10000, 9000, "사료 A")
        self.product2 = _create_product("GI0002", 20000, 18000, "사료 B")

    def test_add_item_to_cart(self):
        response = self.client.post(
            "/api/cart/items/",
            {"goods_id": "GI0001", "quantity": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["product"]["goods_id"], "GI0001")
        self.assertEqual(response.data["items"][0]["quantity"], 1)
        self.assertEqual(response.data["total_price"], 9000)

    def test_add_duplicate_item_increases_quantity(self):
        self.client.post("/api/cart/items/", {"goods_id": "GI0001", "quantity": 1}, format="json")
        response = self.client.post("/api/cart/items/", {"goods_id": "GI0001", "quantity": 2}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["quantity"], 3)
        self.assertEqual(response.data["total_price"], 27000)

    def test_add_nonexistent_product_returns_404(self):
        response = self.client.post(
            "/api/cart/items/",
            {"goods_id": "NOTEXIST", "quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_item_quantity(self):
        self.client.post("/api/cart/items/", {"goods_id": "GI0001", "quantity": 1}, format="json")
        cart_item = CartItem.objects.get(cart__user=self.user, product__goods_id="GI0001")

        response = self.client.patch(
            f"/api/cart/items/{cart_item.cart_item_id}/",
            {"quantity": 5},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 5)
        self.assertEqual(response.data["total_price"], 45000)

    def test_delete_item_from_cart(self):
        self.client.post("/api/cart/items/", {"goods_id": "GI0001", "quantity": 1}, format="json")
        self.client.post("/api/cart/items/", {"goods_id": "GI0002", "quantity": 1}, format="json")
        cart_item = CartItem.objects.get(cart__user=self.user, product__goods_id="GI0001")

        response = self.client.delete(f"/api/cart/items/{cart_item.cart_item_id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["product"]["goods_id"], "GI0002")
        self.assertFalse(CartItem.objects.filter(cart_item_id=cart_item.cart_item_id).exists())

    def test_cannot_access_other_users_cart_item(self):
        self.client.post("/api/cart/items/", {"goods_id": "GI0001", "quantity": 1}, format="json")
        cart_item = CartItem.objects.get(cart__user=self.user)

        other_user = _create_user("cart-other@example.com")
        self.client.force_authenticate(other_user)

        response = self.client.patch(
            f"/api/cart/items/{cart_item.cart_item_id}/",
            {"quantity": 99},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_multiple_items_total_calculation(self):
        self.client.post("/api/cart/items/", {"goods_id": "GI0001", "quantity": 2}, format="json")
        self.client.post("/api/cart/items/", {"goods_id": "GI0002", "quantity": 3}, format="json")

        response = self.client.get("/api/cart/")

        self.assertEqual(response.data["item_count"], 5)
        self.assertEqual(response.data["total_price"], 2 * 9000 + 3 * 18000)


# ── Order Tests ──────────────────────────────────────────────────────────────


class OrderTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _create_user("order@example.com")
        self.client.force_authenticate(self.user)
        self.product1 = _create_product("GI0001", 10000, 9000, "사료 A")
        self.product2 = _create_product("GI0002", 20000, 18000, "사료 B")

    def _fill_cart(self):
        self.client.post("/api/cart/items/", {"goods_id": "GI0001", "quantity": 2}, format="json")
        self.client.post("/api/cart/items/", {"goods_id": "GI0002", "quantity": 1}, format="json")

    def test_create_order_from_cart(self):
        self._fill_cart()

        response = self.client.post(
            "/api/orders/",
            {"recipient_name": "홍길동", "delivery_address": "서울시 강남구"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["recipient_name"], "홍길동")
        self.assertEqual(response.data["total_price"], 2 * 9000 + 18000)
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(len(response.data["items"]), 2)

    def test_create_order_clears_cart(self):
        self._fill_cart()
        self.client.post(
            "/api/orders/",
            {"recipient_name": "홍길동", "delivery_address": "서울시"},
            format="json",
        )

        cart_response = self.client.get("/api/cart/")
        self.assertEqual(len(cart_response.data["items"]), 0)

    def test_create_order_logs_purchase_interactions(self):
        self._fill_cart()
        self.client.post(
            "/api/orders/",
            {"recipient_name": "홍길동", "delivery_address": "서울시"},
            format="json",
        )

        interactions = UserInteraction.objects.filter(user=self.user, interaction_type="purchase")
        self.assertEqual(interactions.count(), 2)
        self.assertTrue(all(i.weight == 5 for i in interactions))

    def test_create_order_empty_cart_returns_400(self):
        response = self.client.post(
            "/api/orders/",
            {"recipient_name": "홍길동", "delivery_address": "서울시"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_orders(self):
        self._fill_cart()
        self.client.post("/api/orders/", {"recipient_name": "홍길동", "delivery_address": "서울시"}, format="json")

        # 두 번째 주문
        self.client.post("/api/cart/items/", {"goods_id": "GI0001", "quantity": 1}, format="json")
        self.client.post("/api/orders/", {"recipient_name": "김철수", "delivery_address": "부산시"}, format="json")

        response = self.client.get("/api/orders/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # 최신 순 정렬
        self.assertEqual(response.data[0]["recipient_name"], "김철수")

    def test_order_detail(self):
        self._fill_cart()
        create_response = self.client.post(
            "/api/orders/",
            {"recipient_name": "홍길동", "delivery_address": "서울시 강남구"},
            format="json",
        )
        order_id = create_response.data["order_id"]

        response = self.client.get(f"/api/orders/{order_id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["order_id"], order_id)
        self.assertEqual(len(response.data["items"]), 2)

    def test_cannot_access_other_users_order(self):
        self._fill_cart()
        create_response = self.client.post(
            "/api/orders/",
            {"recipient_name": "홍길동", "delivery_address": "서울시"},
            format="json",
        )
        order_id = create_response.data["order_id"]

        other_user = _create_user("order-other@example.com")
        self.client.force_authenticate(other_user)

        response = self.client.get(f"/api/orders/{order_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_order_preserves_price_at_order_time(self):
        self._fill_cart()
        self.client.post("/api/orders/", {"recipient_name": "홍길동", "delivery_address": "서울시"}, format="json")

        # 상품 가격 변경
        self.product1.discount_price = 1
        self.product1.save()

        order = Order.objects.get(user=self.user)
        item = order.items.get(product=self.product1)
        self.assertEqual(item.price_at_order, 9000)


# ── Interaction Tests ────────────────────────────────────────────────────────


class InteractionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _create_user("interaction@example.com")
        self.client.force_authenticate(self.user)
        self.product = _create_product()

    def test_log_click_interaction(self):
        response = self.client.post(
            "/api/interactions/",
            {"goods_id": "GI0001", "interaction_type": "click"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        interaction = UserInteraction.objects.get(user=self.user)
        self.assertEqual(interaction.interaction_type, "click")
        self.assertEqual(interaction.weight, 1)

    def test_log_cart_interaction(self):
        response = self.client.post(
            "/api/interactions/",
            {"goods_id": "GI0001", "interaction_type": "cart", "session_id": "11111111-1111-1111-1111-111111111111"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        interaction = UserInteraction.objects.get(user=self.user)
        self.assertEqual(interaction.weight, 3)
        self.assertEqual(str(interaction.session_id), "11111111-1111-1111-1111-111111111111")

    def test_log_reject_interaction(self):
        self.client.post(
            "/api/interactions/",
            {"goods_id": "GI0001", "interaction_type": "reject"},
            format="json",
        )

        interaction = UserInteraction.objects.get(user=self.user)
        self.assertEqual(interaction.weight, -1)

    def test_invalid_interaction_type_returns_400(self):
        response = self.client.post(
            "/api/interactions/",
            {"goods_id": "GI0001", "interaction_type": "invalid"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_product_returns_404(self):
        response = self.client.post(
            "/api/interactions/",
            {"goods_id": "NOTEXIST", "interaction_type": "click"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_goods_id_returns_400(self):
        response = self.client.post(
            "/api/interactions/",
            {"interaction_type": "click"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            "/api/interactions/",
            {"goods_id": "GI0001", "interaction_type": "click"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
