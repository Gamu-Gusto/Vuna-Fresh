"""
Tests for delivery, farmer payouts after delivery, and driver ratings.

Covers:
- The full journey: payment confirmed -> farmer prepares -> admin assigns an
  approved driver -> driver sees and delivers the order -> farmer payout can be
  paid -> buyer rates the driver and reviews the products
- Payouts can't be paid before the order is delivered
- Driver ratings: delivered orders with a driver only, once per order, by the
  order's own buyer; drivers see their ratings without the buyer's identity;
  admins can hide a rating, which drops it from the driver's average
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.orders.models import Order, OrderItem, OrderStatus
from apps.orders.tests import make_admin, make_buyer, make_driver, make_farmer, make_product, mark_paid
from apps.payments.models import FarmerPayout, FarmerPayoutStatus
from apps.payments.services.payouts import calculate_and_create_payouts

from .models import DriverReview


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class DeliveryJourneyTests(TestCase):
    def setUp(self):
        self.buyer_user, self.buyer_profile, self.address = make_buyer("buyer@test.com")
        self.farmer_user, self.farmer_profile = make_farmer("farmer@test.com")
        self.driver_user, self.driver_profile = make_driver("driver@test.com")
        self.admin_user = make_admin("admin@test.com")
        self.product = make_product(self.farmer_profile, price="50.00")
        self.order = Order.objects.create(
            buyer=self.buyer_profile, delivery_address=self.address,
            subtotal=Decimal("100.00"), total=Decimal("100.00"),
        )
        OrderItem.objects.create(
            order=self.order, product=self.product, farmer=self.farmer_profile,
            quantity=2, price_at_purchase=Decimal("50.00"),
        )
        self.payout = calculate_and_create_payouts(mark_paid(self.order))[0]

    def set_status(self, user, new_status):
        return client_for(user).post(
            f"/api/v1/orders/{self.order.id}/update_status/", {"status": new_status}, format="json",
        )

    def pay_farmer(self):
        return client_for(self.admin_user).post(f"/api/v1/payments/payouts/{self.payout.id}/mark_paid/")

    def deliver(self):
        self.set_status(self.farmer_user, "preparing")
        self.set_status(self.farmer_user, "ready_for_pickup")
        client_for(self.admin_user).post(
            f"/api/v1/orders/{self.order.id}/assign_driver/", {"driver_id": self.driver_profile.id}, format="json",
        )
        self.set_status(self.driver_user, "out_for_delivery")
        self.set_status(self.driver_user, "delivered")

    def test_full_journey(self):
        self.assertEqual(self.set_status(self.farmer_user, "preparing").status_code, 200)
        self.assertEqual(self.set_status(self.farmer_user, "ready_for_pickup").status_code, 200)

        # Driver has nothing until assigned
        driver = client_for(self.driver_user)
        self.assertEqual(driver.get("/api/v1/orders/").data["results"], [])

        res = client_for(self.admin_user).post(
            f"/api/v1/orders/{self.order.id}/assign_driver/", {"driver_id": self.driver_profile.id}, format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual([o["id"] for o in driver.get("/api/v1/orders/").data["results"]], [self.order.id])

        # Not delivered yet: the farmer can't be paid
        self.assertEqual(self.set_status(self.driver_user, "out_for_delivery").status_code, 200)
        res = self.pay_farmer()
        self.assertEqual(res.status_code, 400)
        self.assertIn("hasn't been delivered", res.data["error"]["message"])

        # Driver confirms delivery: now the payout can be paid
        self.assertEqual(self.set_status(self.driver_user, "delivered").status_code, 200)
        self.assertEqual(self.pay_farmer().status_code, 200)
        self.payout.refresh_from_db()
        self.assertEqual(self.payout.status, FarmerPayoutStatus.PAID)

        # Buyer rates the driver and reviews the product
        buyer = client_for(self.buyer_user)
        order_data = buyer.get(f"/api/v1/orders/{self.order.id}/").data
        self.assertEqual(order_data["driver_name"], "Test")
        self.assertIsNone(order_data["driver_review"])

        res = buyer.post("/api/v1/driver-reviews/", {"order": self.order.id, "rating": 5, "comment": "Friendly and on time"}, format="json")
        self.assertEqual(res.status_code, 201)
        res = buyer.post("/api/v1/reviews/", {"product": self.product.id, "order": self.order.id, "rating": 4}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(buyer.get(f"/api/v1/orders/{self.order.id}/").data["driver_review"], {"rating": 5})

    def test_payout_blocked_for_every_status_before_delivery(self):
        for new_status, user in [("preparing", self.farmer_user), ("ready_for_pickup", self.farmer_user)]:
            self.assertEqual(self.pay_farmer().status_code, 400)
            self.set_status(user, new_status)
        self.assertEqual(self.pay_farmer().status_code, 400)

    def test_payout_list_shows_readiness(self):
        admin = client_for(self.admin_user)
        row = admin.get("/api/v1/payments/payouts/?status=pending").data["results"][0]
        self.assertEqual((row["order_status"], row["ready_to_pay"]), ("placed", False))
        self.deliver()
        row = admin.get("/api/v1/payments/payouts/?status=pending").data["results"][0]
        self.assertEqual((row["order_status"], row["ready_to_pay"]), ("delivered", True))

    def test_payout_cannot_be_paid_twice(self):
        self.deliver()
        self.assertEqual(self.pay_farmer().status_code, 200)
        self.assertEqual(self.pay_farmer().status_code, 400)
        self.assertEqual(FarmerPayout.objects.get().status, FarmerPayoutStatus.PAID)

    def test_driver_cannot_be_rated_before_delivery(self):
        self.set_status(self.farmer_user, "preparing")
        self.set_status(self.farmer_user, "ready_for_pickup")
        client_for(self.admin_user).post(
            f"/api/v1/orders/{self.order.id}/assign_driver/", {"driver_id": self.driver_profile.id}, format="json",
        )
        res = client_for(self.buyer_user).post("/api/v1/driver-reviews/", {"order": self.order.id, "rating": 5}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_driver_rated_once_by_own_buyer_only(self):
        self.deliver()
        other_user, _, _ = make_buyer("other@test.com")
        res = client_for(other_user).post("/api/v1/driver-reviews/", {"order": self.order.id, "rating": 1}, format="json")
        self.assertEqual(res.status_code, 400)

        buyer = client_for(self.buyer_user)
        self.assertEqual(buyer.post("/api/v1/driver-reviews/", {"order": self.order.id, "rating": 4}, format="json").status_code, 201)
        self.assertEqual(buyer.post("/api/v1/driver-reviews/", {"order": self.order.id, "rating": 2}, format="json").status_code, 400)
        self.assertEqual(buyer.post("/api/v1/driver-reviews/", {"order": self.order.id, "rating": 6}, format="json").status_code, 400)
        self.assertEqual(DriverReview.objects.get().driver, self.driver_profile)

    def test_delivered_order_without_driver_cannot_be_rated(self):
        Order.objects.filter(pk=self.order.pk).update(status=OrderStatus.DELIVERED)
        res = client_for(self.buyer_user).post("/api/v1/driver-reviews/", {"order": self.order.id, "rating": 5}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_driver_sees_ratings_without_buyer_identity(self):
        self.deliver()
        client_for(self.buyer_user).post("/api/v1/driver-reviews/", {"order": self.order.id, "rating": 4, "comment": "Great"}, format="json")

        driver = client_for(self.driver_user)
        rows = driver.get("/api/v1/driver-reviews/").data["results"]
        self.assertEqual([(r["rating"], r["comment"]) for r in rows], [(4, "Great")])
        self.assertNotIn("buyer_email", rows[0])
        self.assertEqual(driver.get("/api/v1/driver-reviews/summary/").data, {"average": 4.0, "count": 1})

        other_driver_user, _ = make_driver("driver2@test.com")
        self.assertEqual(client_for(other_driver_user).get("/api/v1/driver-reviews/").data["results"], [])

        admin_rows = client_for(self.admin_user).get("/api/v1/driver-reviews/").data["results"]
        self.assertEqual(admin_rows[0]["buyer_email"], "buyer@test.com")

    def test_admin_hiding_a_rating_removes_it_from_driver_average(self):
        self.deliver()
        client_for(self.buyer_user).post("/api/v1/driver-reviews/", {"order": self.order.id, "rating": 1, "comment": "abusive"}, format="json")
        review = DriverReview.objects.get()

        admin = client_for(self.admin_user)
        self.assertEqual(admin.post(f"/api/v1/driver-reviews/{review.id}/set_status/", {"status": "removed"}, format="json").status_code, 200)

        driver = client_for(self.driver_user)
        self.assertEqual(driver.get("/api/v1/driver-reviews/").data["results"], [])
        self.assertEqual(driver.get("/api/v1/driver-reviews/summary/").data, {"average": None, "count": 0})
        drivers = admin.get("/api/v1/admin/drivers/").data
        self.assertEqual(drivers[0]["rating_count"], 0)

    def test_admin_driver_list_includes_average_rating(self):
        self.deliver()
        client_for(self.buyer_user).post("/api/v1/driver-reviews/", {"order": self.order.id, "rating": 4}, format="json")
        drivers = client_for(self.admin_user).get("/api/v1/admin/drivers/").data
        self.assertEqual((drivers[0]["average_rating"], drivers[0]["rating_count"]), (4.0, 1))

    def test_buyer_cannot_set_review_status(self):
        self.deliver()
        client_for(self.buyer_user).post("/api/v1/driver-reviews/", {"order": self.order.id, "rating": 4}, format="json")
        review = DriverReview.objects.get()
        res = client_for(self.buyer_user).post(f"/api/v1/driver-reviews/{review.id}/set_status/", {"status": "removed"}, format="json")
        self.assertEqual(res.status_code, 403)
