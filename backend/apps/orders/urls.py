from rest_framework.routers import DefaultRouter
from .views import CartViewSet, CartItemViewSet, InvoiceViewSet, OrderViewSet

router = DefaultRouter()
router.register("cart", CartViewSet, basename="cart")
router.register("cart/items", CartItemViewSet, basename="cart-item")
router.register("orders", OrderViewSet, basename="order")
router.register("invoices", InvoiceViewSet, basename="invoice")

urlpatterns = router.urls
