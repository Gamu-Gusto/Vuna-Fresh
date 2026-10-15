# Vuna Fresh — Project Context for Claude Code

Read this fully before starting any task. It exists so you don't have to re-explore the codebase or ask me questions I've already answered here.

## What this is

Vuna Fresh (formerly 7Colours) is a farm-to-consumer grocery delivery platform for South Africa. Buyers — individual customers and businesses (retailers, restaurants, spaza shops) — order fresh produce directly from farmers, with recipe/meal-plan integration as the key differentiator. Four user roles: customer, farmer, driver, admin.

## Current focus: Phase 1 (MVP) ONLY

Do not build recipe/meal-plan features, AI recommendations, farmer financing, or analytics dashboards yet. Those are Phase 3/4. If a task seems to need one of those, stop and ask rather than building a placeholder for it.

Phase 1 scope is: user accounts for all four roles, product browsing, cart, orders, payments (PayFast, plus manual direct deposit with proof-of-payment upload), delivery status tracking, farmer inventory management, basic admin approval flows, and required POPIA-style consent/data-privacy infrastructure.

Also in Phase 1 (added after the original plan, intentionally): business buyer accounts with credit terms and invoices (`buyers` app, bulk orders), recurring product subscriptions (`subscriptions` app), surplus listings and the `WastageMetric` schema (no write path yet), and farmer payout calculation with platform commission (payouts are marked paid manually by an admin — no payout gateway).

## Stack

- **Backend:** Django + Django REST Framework
- **Database:** PostgreSQL
- **Web frontend:** Next.js (App Router), consumes the DRF API
- **Mobile:** React Native, consumes the same DRF API
- **Payments:** PayFast online, plus manual direct deposit. Do not scaffold Yoco or PayStack integrations until explicitly asked. For now all payments are offline (EFT / direct deposit with proof upload, admin approval). PayFast code exists but is switched off with `PAYFAST_ENABLED=False` until the merchant account is live.
- **Hosting:** Render
- **File/image storage:** Supabase Storage (S3-compatible) via `django-storages`, configured with the `STORAGE_*` environment variables. Without them, production falls back to the server's disk, which Render wipes on every deploy.

## Folder structure

```
vunafresh/
├── backend/                      # Django project
│   ├── config/                   # settings, urls, wsgi/asgi
│   ├── apps/
│   │   ├── users/                # User, BuyerProfile, FarmerProfile, DriverProfile, Address
│   │   ├── buyers/               # BusinessBuyerDetails, BuyerAccountMember
│   │   ├── products/              # Product, Category, SurplusListing, WastageMetric
│   │   ├── orders/                # Cart, CartItem, Order, OrderItem, OrderStatusHistory, Invoice
│   │   ├── payments/               # PaymentMethod, Transaction, DirectDepositProof, CommissionSettings, FarmerPayout
│   │   ├── subscriptions/          # Subscription (+ process_subscriptions management command)
│   │   ├── reviews/                # ProductReview, ReviewFlag
│   │   ├── issues/                 # Issue, IssueAttachment, IssueMessage
│   │   ├── privacy/                # ConsentRecord, DataAccessRequest, DataAccessAuditLog
│   │   └── notifications/          # NotificationPreference, Notification
│   ├── manage.py
│   └── requirements.txt
├── web/                           # Next.js app
└── mobile/                        # React Native app
```

Each Django app in `apps/` should be a standard Django app (models.py, serializers.py, views.py, urls.py) — don't collapse everything into one giant app.

## Core models (Phase 1 scope — build in this order)

1. `users.User` (extends AbstractUser or custom) — email, phone, role (customer/farmer/driver/admin), status
2. `users.Address` — belongs to a user, has `is_default`
3. `users.BuyerProfile` (formerly CustomerProfile) / `FarmerProfile` / `DriverProfile` — one-to-one with User
4. `products.Category`, `products.Product` — Product belongs to a farmer and a category
5. `orders.Cart`, `orders.CartItem` — cart belongs to a buyer, snapshot price on add
6. `orders.Order`, `orders.OrderItem`, `orders.OrderStatusHistory` — order items denormalize `farmer_id` for split-order/payout logic later
7. `payments.PaymentMethod`, `payments.Transaction`, `DirectDepositProof`, `CommissionSettings`, `FarmerPayout`
8. `privacy.ConsentRecord`, `DataAccessRequest`, `DataAccessAuditLog` — required before launch, not optional
9. `issues.Issue`, `IssueAttachment`, `IssueMessage`

Full field-level detail is in the separate schema doc if you need it — ask me to paste the relevant section rather than guessing field names.

## Hard rules

- Always write a migration when a model changes. Never hand-edit migration files.
- Don't touch `payments/` logic without explicit confirmation — this handles real money and needs care, not speed.
- Don't add new third-party packages without checking with me first. Keep `requirements.txt` lean.
- Use DRF's `ModelViewSet` + routers for standard CRUD, don't hand-roll views for things DRF already solves.
- Role-based permissions: use DRF permission classes per role (customer/farmer/driver/admin), not manual `if` checks scattered through views.
- Every model that stores user data must be considered against the `privacy` app — if in doubt, ask whether a field needs a consent record before adding it.
- Keep commits small and scoped to one app/feature. Don't bundle unrelated changes.

## What NOT to do

- Don't build the recipe/meal-plan app yet (Phase 3).
- Don't integrate Yoco or PayStack yet (PayFast + direct deposit only for now).
- Don't build admin analytics dashboards yet (Phase 4).
- Don't run the full test suite or search the whole repo unless asked — work on the specific app/file given.
- Don't refactor code outside the scope of the current task, even if you spot something better. Flag it to me instead.

## Working style

Tasks will be given one app or feature at a time (e.g. "build the users app: User, Address, BuyerProfile/FarmerProfile/DriverProfile models with migrations"). Finish that scope, stop, and let me verify before moving to the next one. Don't try to build multiple apps in one session unless explicitly told to.
