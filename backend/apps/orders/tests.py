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


def make_admin(email, super_admin=True):
    """The super admin by default; super_admin=False makes a manager."""
    return make_user(email, "admin", is_staff=True, is_superuser=super_admin)


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
        self.product = make_product(self.farmer_profile, price="30.00", stock=50)

        # Pre-load a cart worth exactly the R300 household minimum (10 x R30)
        cart = Cart.objects.create(buyer=self.buyer_profile, status=CartStatus.ACTIVE)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=10,
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
        self.assertEqual(item.quantity, 10)

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
        # 10 × 30.00 = 300.00
        self.assertEqual(order.subtotal, Decimal("300.00"))
        self.assertEqual(order.total, Decimal("300.00"))

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


class AdminOrderFilterTests(TestCase):
    """The admin deliveries board asks for orders by status and whether a driver is assigned."""

    def setUp(self):
        _, buyer_profile, address = make_buyer("customer@test.com")
        self.admin_user = make_admin("admin@test.com")
        _, self.driver_profile = make_driver("driver@test.com")
        make = lambda status, driver=None: Order.objects.create(
            buyer=buyer_profile, delivery_address=address, status=status, driver=driver,
            subtotal=Decimal("10.00"), total=Decimal("10.00"),
        )
        self.waiting = make(OrderStatus.READY_FOR_PICKUP)
        self.assigned = make(OrderStatus.READY_FOR_PICKUP, self.driver_profile)
        self.on_road = make(OrderStatus.OUT_FOR_DELIVERY, self.driver_profile)
        self.placed = make(OrderStatus.PLACED)

    def ids(self, query, user=None):
        client = APIClient()
        client.force_authenticate(user=user or self.admin_user)
        return {o["id"] for o in client.get(f"/api/v1/orders/{query}").data["results"]}

    def test_filter_by_status_and_driver(self):
        self.assertEqual(self.ids("?status=ready_for_pickup&has_driver=false"), {self.waiting.id})
        self.assertEqual(self.ids("?status=ready_for_pickup&has_driver=true"), {self.assigned.id})
        self.assertEqual(self.ids("?status=ready_for_pickup,out_for_delivery"), {self.waiting.id, self.assigned.id, self.on_road.id})
        self.assertEqual(len(self.ids("")), 4)

    def test_filters_do_not_widen_other_roles(self):
        # A driver still only sees their own orders, whatever they ask for
        self.assertEqual(self.ids("?status=ready_for_pickup&has_driver=false", self.driver_profile.user), {self.assigned.id, self.on_road.id})


class EarlyDriverAssignmentTests(TestCase):
    """Admins can line up a driver while the farm is packing; collection waits for 'ready'."""

    def setUp(self):
        _, buyer_profile, address = make_buyer("customer@test.com")
        self.farmer_user, farmer_profile = make_farmer("farmer@test.com")
        self.driver_user, self.driver_profile = make_driver("driver@test.com")
        self.admin = APIClient()
        self.admin.force_authenticate(make_admin("admin@test.com"))
        self.order = Order.objects.create(
            buyer=buyer_profile, delivery_address=address, status=OrderStatus.PREPARING,
            subtotal=Decimal("10.00"), total=Decimal("10.00"),
        )
        OrderItem.objects.create(
            order=self.order, product=make_product(farmer_profile), farmer=farmer_profile,
            quantity=1, price_at_purchase=Decimal("10.00"),
        )
        mark_paid(self.order)

    def assign(self):
        return self.admin.post(
            f"/api/v1/orders/{self.order.id}/assign_driver/", {"driver_id": self.driver_profile.id}, format="json",
        )

    def test_assign_while_packing_then_collect_once_ready(self):
        from apps.notifications.models import Notification

        self.assertEqual(self.assign().status_code, 200)
        self.assertIn("still packing", Notification.objects.get(user=self.driver_user, type="delivery_assigned").message)

        driver = APIClient()
        driver.force_authenticate(self.driver_user)
        self.assertEqual([o["id"] for o in driver.get("/api/v1/orders/").data["results"]], [self.order.id])
        # Can't set off before the farm has packed it
        res = driver.post(f"/api/v1/orders/{self.order.id}/update_status/", {"status": "out_for_delivery"}, format="json")
        self.assertEqual(res.status_code, 400)

        farmer = APIClient()
        farmer.force_authenticate(self.farmer_user)
        res = farmer.post(f"/api/v1/orders/{self.order.id}/update_status/", {"status": "ready_for_pickup"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Notification.objects.filter(user=self.driver_user, type="delivery_ready").exists())
        res = driver.post(f"/api/v1/orders/{self.order.id}/update_status/", {"status": "out_for_delivery"}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_cannot_assign_before_packing_or_after_setting_off(self):
        for status in (OrderStatus.PLACED, OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED):
            Order.objects.filter(pk=self.order.pk).update(status=status)
            self.assertEqual(self.assign().status_code, 400, status)


def make_business_buyer(email, commission_rate=None):
    """A business buyer account (approved), optionally with its own agreed commission."""
    from apps.buyers.models import BusinessBuyerDetails

    user, profile, address = make_buyer(email)
    profile.buyer_type = "business"
    profile.save(update_fields=["buyer_type"])
    BusinessBuyerDetails.objects.create(
        buyer=profile, business_name="Corner Bistro", business_type="restaurant", billing_address=address,
        approval_status="active", commission_rate=commission_rate,
    )
    return user, profile, address


class MinimumOrderTests(TestCase):
    """R300 of produce for household orders, R900 for businesses; delivery doesn't count."""

    def setUp(self):
        _, self.farmer_profile = make_farmer("farmer@test.com")
        self.product = make_product(self.farmer_profile, price="50.00", stock=100)

    def cart_with(self, buyer_profile, quantity):
        cart = Cart.objects.create(buyer=buyer_profile, status=CartStatus.ACTIVE)
        CartItem.objects.create(cart=cart, product=self.product, quantity=quantity, price_at_add=Decimal("50.00"))
        return cart

    def checkout(self, user, address):
        client = APIClient()
        client.force_authenticate(user=user)
        return client.post("/api/v1/orders/", {"delivery_address_id": address.id}, format="json")

    def test_household_minimum(self):
        user, profile, address = make_buyer("home@test.com")
        cart = self.cart_with(profile, 5)  # R250
        res = self.checkout(user, address)
        self.assertEqual(res.status_code, 400)
        self.assertIn("R300.00", str(res.data))
        self.assertIn("R50.00 more", str(res.data))

        client = APIClient()
        client.force_authenticate(user=user)
        minimum = client.get("/api/v1/cart/").data["minimum_order"]
        self.assertEqual((minimum["kind"], minimum["minimum"], minimum["shortfall"]), ("household", "300.00", "50.00"))

        CartItem.objects.filter(cart=cart).update(quantity=6)  # R300
        self.assertEqual(self.checkout(user, address).status_code, 201)

    def test_business_minimum(self):
        user, profile, address = make_business_buyer("bistro@test.com")
        cart = self.cart_with(profile, 12)  # R600: enough for a household, not a business
        res = self.checkout(user, address)
        self.assertEqual(res.status_code, 400)
        self.assertIn("R900.00", str(res.data))
        CartItem.objects.filter(cart=cart).update(quantity=18)  # R900
        self.assertEqual(self.checkout(user, address).status_code, 201)

    def test_subscription_must_meet_minimum_per_delivery(self):
        from datetime import timedelta

        from django.utils import timezone

        user, _, _ = make_buyer("home@test.com")
        client = APIClient()
        client.force_authenticate(user=user)
        body = {
            "product": self.product.id, "frequency": "weekly",
            "next_delivery_date": (timezone.localdate() + timedelta(days=2)).isoformat(),
        }
        res = client.post("/api/v1/subscriptions/", {**body, "quantity": 2}, format="json")  # R100
        self.assertEqual(res.status_code, 400)
        self.assertIn("at least R300.00", str(res.data))
        self.assertEqual(client.post("/api/v1/subscriptions/", {**body, "quantity": 6}, format="json").status_code, 201)


class CommissionTests(TestCase):
    """
    Vuna Fresh keeps the commission and pays the farmer the rest: household 10%,
    business 8% (or the account's agreed 5-8%), surplus 5%. Each item records its
    rate when ordered.
    """

    def setUp(self):
        _, self.farmer_profile = make_farmer("farmer@test.com")
        self.product = make_product(self.farmer_profile, price="100.00", stock=100)

    def order_for(self, buyer_profile, address, quantity=3, surplus_listing=None):
        order = Order.objects.create(
            buyer=buyer_profile, delivery_address=address,
            subtotal=Decimal("100.00") * quantity, total=Decimal("100.00") * quantity,
        )
        item = OrderItem.objects.create(
            order=order, product=self.product, farmer=self.farmer_profile, quantity=quantity,
            price_at_purchase=Decimal("100.00"), surplus_listing=surplus_listing,
        )
        return order, item

    def payout_for(self, order):
        from apps.payments.services.payouts import calculate_and_create_payouts
        return calculate_and_create_payouts(mark_paid(order))[0]

    def test_household_pays_10_percent(self):
        _, profile, address = make_buyer("home@test.com")
        order, item = self.order_for(profile, address)
        self.assertEqual(item.commission_rate, Decimal("10.00"))
        payout = self.payout_for(order)
        self.assertEqual((payout.gross_amount, payout.commission_amount, payout.net_amount),
                         (Decimal("300.00"), Decimal("30.00"), Decimal("270.00")))

    def test_business_default_and_agreed_rates(self):
        _, standard, address = make_business_buyer("bistro@test.com")
        self.assertEqual(self.order_for(standard, address)[1].commission_rate, Decimal("8.00"))
        _, agreed, address2 = make_business_buyer("hotel@test.com", commission_rate=Decimal("6.00"))
        order, item = self.order_for(agreed, address2)
        self.assertEqual(item.commission_rate, Decimal("6.00"))
        self.assertEqual(self.payout_for(order).commission_amount, Decimal("18.00"))

    def test_surplus_pays_5_percent(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.products.models import SurplusListing

        listing = SurplusListing.objects.create(
            product=self.product, farmer=self.farmer_profile, quantity_available=10,
            discount_percentage=Decimal("30"), reason="excess_harvest", expires_at=timezone.now() + timedelta(days=1),
        )
        _, profile, address = make_buyer("home@test.com")
        _, item = self.order_for(profile, address, surplus_listing=listing)
        self.assertEqual(item.commission_rate, Decimal("5.00"))

    def test_rates_follow_settings_but_past_orders_keep_theirs(self):
        from django.utils import timezone

        from apps.payments.models import CommissionSettings

        _, profile, address = make_buyer("home@test.com")
        old_order, old_item = self.order_for(profile, address)
        CommissionSettings.objects.create(
            commission_rate=Decimal("12.00"), business_rate=Decimal("7.00"), surplus_rate=Decimal("4.00"),
            effective_from=timezone.now(),
        )
        _, new_item = self.order_for(profile, address)
        self.assertEqual((old_item.commission_rate, new_item.commission_rate), (Decimal("10.00"), Decimal("12.00")))
        # Paid after the change: still the rate recorded when it was ordered
        self.assertEqual(self.payout_for(old_order).commission_amount, Decimal("30.00"))

    def test_older_items_without_a_rate_still_pay_out(self):
        _, profile, address = make_buyer("home@test.com")
        order, item = self.order_for(profile, address)
        OrderItem.objects.filter(pk=item.pk).update(commission_rate=None)
        self.assertEqual(self.payout_for(order).commission_amount, Decimal("30.00"))

    def test_business_rate_set_on_approval_must_be_5_to_8(self):
        from apps.buyers.models import BusinessBuyerDetails

        _, profile, _ = make_business_buyer("bistro@test.com")
        details = BusinessBuyerDetails.objects.get(buyer=profile)
        details.approval_status = "pending"
        details.save()
        admin = APIClient()
        admin.force_authenticate(make_admin("admin@test.com"))
        url = f"/api/v1/buyers/admin/business/{details.id}/review/"
        self.assertEqual(admin.post(url, {"action": "approve", "commission_rate": "9.00"}, format="json").status_code, 400)
        res = admin.post(url, {"action": "approve", "commission_rate": "6.50"}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["commission_rate"], "6.50")
