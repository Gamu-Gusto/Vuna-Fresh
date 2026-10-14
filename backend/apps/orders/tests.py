"""
Tests for the orders app.

Covers:
- Cart: add item, price snapshot, re-add updates quantity, out-of-stock rejection
- Checkout: OrderItems created with correct snapshots and farmer FK, cart marked converted
- Order list visibility: farmer A cannot see orders that only contain farmer B's products
- Status transitions: history row created, invalid transitions rejected, role enforcement
- Release: unpaid prepaid orders are hidden from farmers and can't be prepared;
  credit-terms orders are released straight away
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.products.models import Category, Product
from apps.users.models import Address, BuyerProfile, DriverProfile, FarmerProfile, User
from .models import Cart, CartItem, CartStatus, Order, OrderItem, OrderStatus, OrderStatusHistory


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_user(email, role, **kwargs):
    return User.objects.create_user(
        email=email,
        password="TestPass123!",
        first_name="Test",
        last_name="User",
        role=role,
        status="active",
        **kwargs,
    )


def make_farmer(email, farm_name="Green Farm"):
    user = make_user(email, "farmer")
    profile = FarmerProfile.objects.create(user=user, farm_name=farm_name, is_approved=True)
    return user, profile


def make_buyer(email):
    user = make_user(email, "customer")
    profile = BuyerProfile.objects.create(user=user)
    address = Address.objects.create(
        user=user,
        street_address="1 Test Road",
        city="Cape Town",
        province="Western Cape",
        postal_code="8001",
        is_default=True,
    )
    return user, profile, address


def make_driver(email):
    user = make_user(email, "driver")
    profile = DriverProfile.objects.create(user=user, is_approved=True)
    return user, profile


def make_admin(email):
    return make_user(email, "admin", is_staff=True)


def make_product(farmer_profile, name="Tomatoes", price="10.00", stock=100):
    category, _ = Category.objects.get_or_create(name="Vegetables")
    return Product.objects.create(
        farmer=farmer_profile,
        category=category,
        name=name,
        price=Decimal(price),
        unit="kg",
        stock_quantity=stock,
        is_available=True,
    )


def mark_paid(order):
    """Helper: record a confirmed (completed) payment, which releases the order to farmers."""
    from apps.payments.models import Transaction
    return Transaction.objects.create(
        order=order, user=order.buyer.user, provider="direct_deposit",
        type="payment", amount=order.total, status="completed",
    )


def checkout(buyer_user, buyer_profile, address, cart):
    """Helper: POST to /api/v1/orders/ as the given customer."""
    client = APIClient()
    client.force_authenticate(user=buyer_user)
    response = client.post(
        "/api/v1/orders/",
        {"delivery_address_id": address.id},
        format="json",
    )
    return response


# ── Cart tests ────────────────────────────────────────────────────────────────

class CartAddItemTests(TestCase):

    def setUp(self):
        self.buyer_user, self.buyer_profile, self.address = make_buyer("customer@test.com")
        _, self.farmer_profile = make_farmer("farmer@test.com")
        self.product = make_product(self.farmer_profile, price="25.00", stock=50)
        self.client = APIClient()
        self.client.force_authenticate(user=self.buyer_user)

    def test_add_item_creates_cart_and_item(self):
        response = self.client.post(
            "/api/v1/cart/add_item/",
            {"product_id": self.product.id, "quantity": 3},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CartItem.objects.count(), 1)
        item = CartItem.objects.get()
        self.assertEqual(item.quantity, 3)

    def test_price_is_snapshotted_at_add_time(self):
        self.client.post(
            "/api/v1/cart/add_item/",
            {"product_id": self.product.id, "quantity": 1},
            format="json",
        )
        item = CartItem.objects.get()
        self.assertEqual(item.price_at_add, Decimal("25.00"))

        # Now change the product price
        self.product.price = Decimal("99.00")
        self.product.save()

        # The snapshot on the existing CartItem is unchanged
        item.refresh_from_db()
        self.assertEqual(item.price_at_add, Decimal("25.00"))

    def test_re_adding_same_product_updates_quantity(self):
        self.client.post(
            "/api/v1/cart/add_item/",
            {"product_id": self.product.id, "quantity": 2},
            format="json",
        )
        self.client.post(
            "/api/v1/cart/add_item/",
            {"product_id": self.product.id, "quantity": 5},
            format="json",
        )
        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(CartItem.objects.get().quantity, 5)

    def test_add_item_rejects_quantity_exceeding_stock(self):
        response = self.client.post(
            "/api/v1/cart/add_item/",
            {"product_id": self.product.id, "quantity": 999},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_add_unavailable_product_rejected(self):
        self.product.is_available = False
        self.product.save()
        response = self.client.post(
            "/api/v1/cart/add_item/",
            {"product_id": self.product.id, "quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_non_customer_cannot_add_to_cart(self):
        farmer_user, _ = make_farmer("other_farmer@test.com", farm_name="Other Farm")
        client = APIClient()
        client.force_authenticate(user=farmer_user)
        response = client.post(
            "/api/v1/cart/add_item/",
            {"product_id": self.product.id, "quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_get_cart_creates_empty_cart_if_none(self):
        response = self.client.get("/api/v1/cart/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "active")
        self.assertEqual(response.data["items"], [])
        self.assertEqual(Cart.objects.filter(buyer=self.buyer_profile, status="active").count(), 1)


# ── Checkout tests ────────────────────────────────────────────────────────────

class CheckoutTests(TestCase):

    def setUp(self):
        self.buyer_user, self.buyer_profile, self.address = make_buyer("customer@test.com")
        _, self.farmer_profile = make_farmer("farmer@test.com")
        self.product = make_product(self.farmer_profile, price="30.00", stock=20)

        # Pre-load a cart
        cart = Cart.objects.create(buyer=self.buyer_profile, status=CartStatus.ACTIVE)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=2,
            price_at_add=Decimal("30.00"),
        )
        self.cart = cart

    def _checkout(self):
        client = APIClient()
        client.force_authenticate(user=self.buyer_user)
        return client.post(
            "/api/v1/orders/",
            {"delivery_address_id": self.address.id},
            format="json",
        )

    def test_checkout_creates_order(self):
        response = self._checkout()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Order.objects.count(), 1)

    def test_checkout_creates_order_items_from_cart(self):
        self._checkout()
        order = Order.objects.get()
        self.assertEqual(order.items.count(), 1)
        item = order.items.get()
        self.assertEqual(item.product, self.product)
        self.assertEqual(item.quantity, 2)

    def test_checkout_snapshots_price_at_purchase(self):
        # Change product price before checkout — should not affect order
        self.product.price = Decimal("99.00")
        self.product.save()

        self._checkout()
        item = OrderItem.objects.get()
        # price_at_add from cart is what gets snapshotted, not the live product price
        self.assertEqual(item.price_at_purchase, Decimal("30.00"))

    def test_checkout_denormalizes_farmer_fk(self):
        self._checkout()
        item = OrderItem.objects.get()
        self.assertEqual(item.farmer, self.farmer_profile)

    def test_checkout_calculates_subtotal_from_snapshots(self):
        self._checkout()
        order = Order.objects.get()
        # 2 × 30.00 = 60.00
        self.assertEqual(order.subtotal, Decimal("60.00"))
        self.assertEqual(order.total, Decimal("60.00"))

    def test_checkout_marks_cart_as_converted(self):
        self._checkout()
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.status, CartStatus.CONVERTED)

    def test_checkout_creates_initial_status_history_row(self):
        self._checkout()
        order = Order.objects.get()
        self.assertEqual(order.status_history.count(), 1)
        self.assertEqual(order.status_history.first().status, OrderStatus.PLACED)

    def test_checkout_with_empty_cart_rejected(self):
        self.cart.items.all().delete()
        response = self._checkout()
        self.assertEqual(response.status_code, 400)

    def test_checkout_with_no_cart_rejected(self):
        self.cart.delete()
        response = self._checkout()
        self.assertEqual(response.status_code, 400)

    def test_checkout_with_wrong_address_rejected(self):
        other_user, _, other_address = make_buyer("other@test.com")
        client = APIClient()
        client.force_authenticate(user=self.buyer_user)
        response = client.post(
            "/api/v1/orders/",
            {"delivery_address_id": other_address.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_farmer_cannot_place_order(self):
        farmer_user, _ = make_farmer("farmer2@test.com", farm_name="Farm 2")
        client = APIClient()
        client.force_authenticate(user=farmer_user)
        response = client.post(
            "/api/v1/orders/",
            {"delivery_address_id": self.address.id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


# ── Order visibility tests ────────────────────────────────────────────────────

class OrderVisibilityTests(TestCase):
    """
    A farmer can only see orders that contain at least one of their products.
    """

    def setUp(self):
        # Two farmers, two products, one customer, one order per farmer
        self.buyer_user, self.buyer_profile, self.address = make_buyer("customer@test.com")

        _, self.farmer_a_profile = make_farmer("farmer_a@test.com", farm_name="Farm A")
        _, self.farmer_b_profile = make_farmer("farmer_b@test.com", farm_name="Farm B")

        self.product_a = make_product(self.farmer_a_profile, name="Apples", price="10.00")
        self.product_b = make_product(self.farmer_b_profile, name="Bananas", price="20.00")

        # Order 1: only contains farmer A's product
        self.order_a = Order.objects.create(
            buyer=self.buyer_profile,
            delivery_address=self.address,
            status=OrderStatus.PLACED,
            subtotal=Decimal("10.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("10.00"),
        )
        OrderItem.objects.create(
            order=self.order_a,
            product=self.product_a,
            farmer=self.farmer_a_profile,
            quantity=1,
            price_at_purchase=Decimal("10.00"),
        )

        # Order 2: only contains farmer B's product
        self.order_b = Order.objects.create(
            buyer=self.buyer_profile,
            delivery_address=self.address,
            status=OrderStatus.PLACED,
            subtotal=Decimal("20.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("20.00"),
        )
        OrderItem.objects.create(
            order=self.order_b,
            product=self.product_b,
            farmer=self.farmer_b_profile,
            quantity=1,
            price_at_purchase=Decimal("20.00"),
        )
        mark_paid(self.order_a)
        mark_paid(self.order_b)

    def _get_orders(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client.get("/api/v1/orders/")

    def test_farmer_a_sees_only_their_order(self):
        response = self._get_orders(self.farmer_a_profile.user)
        self.assertEqual(response.status_code, 200)
        ids = [o["id"] for o in response.data["results"]]
        self.assertIn(self.order_a.id, ids)
        self.assertNotIn(self.order_b.id, ids)

    def test_farmer_b_sees_only_their_order(self):
        response = self._get_orders(self.farmer_b_profile.user)
        self.assertEqual(response.status_code, 200)
        ids = [o["id"] for o in response.data["results"]]
        self.assertIn(self.order_b.id, ids)
        self.assertNotIn(self.order_a.id, ids)

    def test_customer_sees_only_their_own_orders(self):
        other_user, other_profile, other_address = make_buyer("other@test.com")
        # Order belonging to the other customer
        other_order = Order.objects.create(
            buyer=other_profile,
            delivery_address=other_address,
            status=OrderStatus.PLACED,
            subtotal=Decimal("5.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("5.00"),
        )
        response = self._get_orders(self.buyer_user)
        ids = [o["id"] for o in response.data["results"]]
        self.assertNotIn(other_order.id, ids)
        self.assertIn(self.order_a.id, ids)
        self.assertIn(self.order_b.id, ids)

    def test_admin_sees_all_orders(self):
        admin = make_admin("admin@test.com")
        response = self._get_orders(admin)
        self.assertEqual(response.status_code, 200)
        ids = [o["id"] for o in response.data["results"]]
        self.assertIn(self.order_a.id, ids)
        self.assertIn(self.order_b.id, ids)

    def test_driver_sees_only_assigned_orders(self):
        driver_user, driver_profile = make_driver("driver@test.com")
        self.order_a.driver = driver_profile
        self.order_a.save(update_fields=["driver"])

        response = self._get_orders(driver_user)
        ids = [o["id"] for o in response.data["results"]]
        self.assertIn(self.order_a.id, ids)
        self.assertNotIn(self.order_b.id, ids)


# ── Status transition tests ───────────────────────────────────────────────────

class OrderStatusTransitionTests(TestCase):

    def setUp(self):
        self.buyer_user, self.buyer_profile, self.address = make_buyer("customer@test.com")
        self.farmer_user, self.farmer_profile = make_farmer("farmer@test.com")
        self.driver_user, self.driver_profile = make_driver("driver@test.com")
        self.admin_user = make_admin("admin@test.com")

        self.product = make_product(self.farmer_profile, price="15.00")

        self.order = Order.objects.create(
            buyer=self.buyer_profile,
            delivery_address=self.address,
            status=OrderStatus.PLACED,
            subtotal=Decimal("15.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("15.00"),
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            farmer=self.farmer_profile,
            quantity=1,
            price_at_purchase=Decimal("15.00"),
        )
        mark_paid(self.order)

    def _update_status(self, user, new_status):
        client = APIClient()
        client.force_authenticate(user=user)
        return client.post(
            f"/api/v1/orders/{self.order.id}/update_status/",
            {"status": new_status},
            format="json",
        )

    # ── History row creation ──────────────────────────────────────────────────

    def test_status_change_creates_history_row(self):
        before = OrderStatusHistory.objects.filter(order=self.order).count()
        self.order.transition_status(OrderStatus.PREPARING, changed_by=self.farmer_user)
        after = OrderStatusHistory.objects.filter(order=self.order).count()
        self.assertEqual(after, before + 1)

    def test_history_row_records_correct_status(self):
        self.order.transition_status(OrderStatus.PREPARING, changed_by=self.farmer_user)
        history = OrderStatusHistory.objects.filter(order=self.order).last()
        self.assertEqual(history.status, OrderStatus.PREPARING)
        self.assertEqual(history.changed_by, self.farmer_user)

    def test_multiple_transitions_each_create_a_history_row(self):
        self.order.transition_status(OrderStatus.PREPARING, changed_by=self.farmer_user)
        self.order.transition_status(OrderStatus.READY_FOR_PICKUP, changed_by=self.farmer_user)
        self.assertEqual(OrderStatusHistory.objects.filter(order=self.order).count(), 2)

    # ── Valid transitions via API ─────────────────────────────────────────────

    def test_farmer_can_move_placed_to_preparing(self):
        response = self._update_status(self.farmer_user, "preparing")
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.PREPARING)

    def test_driver_can_move_to_out_for_delivery_when_assigned(self):
        self.order.driver = self.driver_profile
        self.order.status = OrderStatus.READY_FOR_PICKUP
        self.order.save(update_fields=["driver", "status"])

        response = self._update_status(self.driver_user, "out_for_delivery")
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.OUT_FOR_DELIVERY)

    def test_admin_can_cancel_order(self):
        response = self._update_status(self.admin_user, "cancelled")
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.CANCELLED)

    # ── Invalid transitions ───────────────────────────────────────────────────

    def test_cannot_skip_status_steps(self):
        # placed → out_for_delivery is not a valid transition
        with self.assertRaises(ValidationError):
            self.order.transition_status(OrderStatus.OUT_FOR_DELIVERY, changed_by=self.admin_user)

    def test_cannot_revert_delivered_order(self):
        self.order.status = OrderStatus.DELIVERED
        self.order.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            self.order.transition_status(OrderStatus.PLACED, changed_by=self.admin_user)

    def test_customer_cannot_change_status(self):
        response = self._update_status(self.buyer_user, "preparing")
        self.assertEqual(response.status_code, 400)

    # ── Role enforcement ──────────────────────────────────────────────────────

    def test_farmer_cannot_move_to_out_for_delivery(self):
        self.order.status = OrderStatus.READY_FOR_PICKUP
        self.order.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            self.order.transition_status(OrderStatus.OUT_FOR_DELIVERY, changed_by=self.farmer_user)

    def test_driver_cannot_move_to_preparing(self):
        with self.assertRaises(ValidationError):
            self.order.transition_status(OrderStatus.PREPARING, changed_by=self.driver_user)

    def test_unassigned_driver_cannot_move_order(self):
        self.order.status = OrderStatus.READY_FOR_PICKUP
        self.order.save(update_fields=["status"])
        # driver_profile is not assigned to this order
        with self.assertRaises(ValidationError):
            self.order.transition_status(OrderStatus.OUT_FOR_DELIVERY, changed_by=self.driver_user)

    def test_farmer_without_items_in_order_cannot_move_status(self):
        _, other_farmer_profile = make_farmer("other_farmer@test.com", farm_name="Other Farm")
        with self.assertRaises(ValidationError):
            self.order.transition_status(OrderStatus.PREPARING, changed_by=other_farmer_profile.user)


class OrderReleaseTests(TestCase):
    """A prepaid order reaches farmers only once its payment is confirmed."""

    def setUp(self):
        _, self.buyer_profile, self.address = make_buyer("customer@test.com")
        self.farmer_user, self.farmer_profile = make_farmer("farmer@test.com")
        self.admin_user = make_admin("admin@test.com")
        product = make_product(self.farmer_profile, price="15.00")
        self.order = Order.objects.create(
            buyer=self.buyer_profile, delivery_address=self.address,
            subtotal=Decimal("15.00"), total=Decimal("15.00"),
        )
        OrderItem.objects.create(
            order=self.order, product=product, farmer=self.farmer_profile,
            quantity=1, price_at_purchase=Decimal("15.00"),
        )

    def _farmer_order_ids(self):
        client = APIClient()
        client.force_authenticate(user=self.farmer_user)
        return [o["id"] for o in client.get("/api/v1/orders/").data["results"]]

    def test_unpaid_order_hidden_from_farmer(self):
        self.assertNotIn(self.order.id, self._farmer_order_ids())

    def test_unpaid_order_cannot_be_prepared_even_by_admin(self):
        for user in (self.farmer_user, self.admin_user):
            with self.assertRaises(ValidationError):
                self.order.transition_status(OrderStatus.PREPARING, changed_by=user)

    def test_payment_awaiting_verification_does_not_release(self):
        from apps.payments.models import Transaction
        Transaction.objects.create(
            order=self.order, user=self.buyer_profile.user, provider="direct_deposit",
            type="payment", amount=self.order.total, status="awaiting_verification",
        )
        self.assertFalse(self.order.is_released)
        self.assertNotIn(self.order.id, self._farmer_order_ids())

    def test_confirmed_payment_releases_order(self):
        mark_paid(self.order)
        self.assertIn(self.order.id, self._farmer_order_ids())
        self.order.transition_status(OrderStatus.PREPARING, changed_by=self.farmer_user)
        self.assertEqual(self.order.status, OrderStatus.PREPARING)

    def test_credit_terms_order_released_without_payment(self):
        self.order.payment_terms = "net_30"
        self.order.save()
        self.assertIn(self.order.id, self._farmer_order_ids())
        self.order.transition_status(OrderStatus.PREPARING, changed_by=self.farmer_user)
        self.assertEqual(self.order.status, OrderStatus.PREPARING)
