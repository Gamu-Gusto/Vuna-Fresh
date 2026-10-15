"""
Tests for removing and restoring products.

Covers:
- Removing a product that was never ordered deletes it; one that was ordered
  is archived, keeping past orders intact
- Either way it leaves the shop: hidden from buyers, out of carts, surplus
  offers withdrawn, subscriptions cancelled with the buyer notified
- Archived products are listed only on request (the farmer's Archived tab)
- Restoring brings it back hidden; it can't go on sale while archived
- The product's farmer and admins can remove/restore; other farmers can't
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.notifications.models import Notification
from apps.orders.models import Cart, CartItem, Order, OrderItem
from apps.orders.tests import make_admin, make_buyer, make_farmer, make_product
from apps.subscriptions.models import Subscription

from .models import CatalogueItem, Product, SurplusListing


def client_for(user=None):
    client = APIClient()
    if user:
        client.force_authenticate(user=user)
    return client


class ProductRemovalTests(TestCase):
    def setUp(self):
        self.farmer_user, self.farmer = make_farmer("farmer@test.com")
        self.buyer_user, self.buyer, self.address = make_buyer("buyer@test.com")
        self.product = make_product(self.farmer, name="Spinach", price="18.00")
        self.farmer_client = client_for(self.farmer_user)

    def order_it(self):
        order = Order.objects.create(
            buyer=self.buyer, delivery_address=self.address, subtotal=Decimal("18.00"), total=Decimal("18.00"),
        )
        OrderItem.objects.create(
            order=order, product=self.product, farmer=self.farmer, quantity=1, price_at_purchase=Decimal("18.00"),
        )
        return order

    def subscribe(self):
        return Subscription.objects.create(
            buyer=self.buyer, product=self.product, quantity=2, frequency="weekly",
            next_delivery_date=timezone.localdate() + timedelta(days=3),
        )

    def remove(self, client=None):
        return (client or self.farmer_client).delete(f"/api/v1/products/{self.product.id}/")

    def test_never_ordered_is_deleted_and_subscribers_told(self):
        self.subscribe()
        res = self.remove()
        self.assertEqual((res.status_code, res.data["result"]), (200, "deleted"))
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())
        note = Notification.objects.get(user=self.buyer_user, type="subscription_cancelled")
        self.assertIn("Spinach", note.message)

    def test_ordered_is_archived_and_leaves_the_shop(self):
        order = self.order_it()
        subscription = self.subscribe()
        cart = Cart.objects.create(buyer=self.buyer)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1, price_at_add=Decimal("18.00"))
        surplus = SurplusListing.objects.create(
            product=self.product, farmer=self.farmer, quantity_available=5, discount_percentage=Decimal("20"),
            reason="excess_harvest", expires_at=timezone.now() + timedelta(days=2),
        )

        res = self.remove()
        self.assertEqual(res.data["result"], "archived")
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_archived)
        self.assertFalse(self.product.is_available)

        # Out of the shop, carts, surplus offers and subscriptions
        self.assertEqual(client_for().get(f"/api/v1/products/{self.product.id}/").status_code, 404)
        self.assertNotIn(self.product.id, [p["id"] for p in client_for().get("/api/v1/products/").data["results"]])
        self.assertFalse(CartItem.objects.exists())
        surplus.refresh_from_db()
        subscription.refresh_from_db()
        self.assertEqual((surplus.status, subscription.status), ("withdrawn", "cancelled"))
        self.assertTrue(Notification.objects.filter(user=self.buyer_user, type="subscription_cancelled").exists())

        # Past orders are untouched
        order_data = client_for(self.buyer_user).get(f"/api/v1/orders/{order.id}/").data
        self.assertEqual(order_data["items"][0]["product_name"], "Spinach")

    def test_archived_tab_and_restore(self):
        self.order_it()
        self.remove()
        mine = lambda q="": [p["id"] for p in self.farmer_client.get(f"/api/v1/products/?farmer={self.farmer.id}{q}").data["results"]]  # noqa: E731
        self.assertEqual(mine(), [])
        self.assertEqual(mine("&archived=true"), [self.product.id])

        # Can't go back on sale without restoring
        res = self.farmer_client.patch(f"/api/v1/products/{self.product.id}/", {"is_available": True}, format="json")
        self.assertEqual(res.status_code, 400)

        res = self.farmer_client.post(f"/api/v1/products/{self.product.id}/restore/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.data["is_archived"], res.data["is_available"]), (False, False))
        self.assertEqual(mine(), [self.product.id])
        # Restored: the farmer lists it again when ready
        res = self.farmer_client.patch(f"/api/v1/products/{self.product.id}/", {"is_available": True}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_restore_rules(self):
        res = self.farmer_client.post(f"/api/v1/products/{self.product.id}/restore/")
        self.assertEqual(res.status_code, 400)  # not archived

        item = CatalogueItem.objects.create(code="SA0001", name="Spinach", category=self.product.category, default_unit="kg")
        Product.objects.filter(pk=self.product.pk).update(catalogue_item=item)
        self.order_it()
        self.remove()
        CatalogueItem.objects.filter(pk=item.pk).update(is_active=False)
        res = self.farmer_client.post(f"/api/v1/products/{self.product.id}/restore/")
        self.assertEqual(res.status_code, 400)
        self.assertIn("no longer in the catalogue", res.data["error"]["message"])

    def test_admin_can_remove_and_restore_any_product(self):
        self.order_it()
        admin = client_for(make_admin("admin@test.com"))
        self.assertEqual(self.remove(admin).data["result"], "archived")
        self.assertEqual(admin.post(f"/api/v1/products/{self.product.id}/restore/").status_code, 200)

    def test_other_farmers_cannot_remove_or_restore(self):
        other_user, _ = make_farmer("other@test.com", farm_name="Other Farm")
        other = client_for(other_user)
        self.assertEqual(self.remove(other).status_code, 403)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())
        self.order_it()
        self.remove()
        self.assertEqual(other.post(f"/api/v1/products/{self.product.id}/restore/").status_code, 403)
        self.assertEqual(client_for(self.buyer_user).delete(f"/api/v1/products/{self.product.id}/").status_code, 403)

    # Admin pages need the built static manifest otherwise; plain storage is enough here
    @override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
    def test_django_admin_remove_and_restore_actions(self):
        from django.test import Client

        self.order_it()
        admin_user = make_admin("admin@test.com")
        admin_user.is_superuser = True
        admin_user.save()
        browser = Client()
        browser.force_login(admin_user)
        url = "/admin/products/product/"
        res = browser.post(url, {"action": "remove_products", "_selected_action": [self.product.id]}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_archived)
        browser.post(url, {"action": "restore_products", "_selected_action": [self.product.id]}, follow=True)
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_archived)
        # Plain delete is not offered
        self.assertEqual(browser.get(f"{url}{self.product.id}/delete/").status_code, 403)
