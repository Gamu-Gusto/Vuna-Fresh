"""
Shared helpers for letting a business account's members transact on the
account's shared BuyerProfile, not just their own individual one.

Previously, Cart/Order/reviews/subscriptions resolved "the buyer" purely as
request.user.buyer_profile — which only ever works for the literal owner of
that one-to-one profile. These helpers extend that: a user's *own* profile is
always the default, but a member of a business account (see
BuyerAccountMember) can instead act on that account's behalf by sending an
`X-Buyer-Account: <buyer_profile_id>` header. 'viewer' members are read-only —
anywhere a write is being attempted, pass require_write=True to reject them.
"""
from .models import BuyerAccountMember, BuyerAccountMemberRole


def get_accessible_buyer_profiles(user):
    """Every BuyerProfile this user can act as: their own, plus any business
    accounts they're a member of. Used to scope read (list/retrieve) access."""
    profiles = {}
    own = getattr(user, "buyer_profile", None)
    if own is not None:
        profiles[own.id] = own
    for membership in BuyerAccountMember.objects.filter(user=user).select_related("buyer_profile"):
        profiles[membership.buyer_profile_id] = membership.buyer_profile
    return list(profiles.values())


def user_can_act_for_buyer_profile(user, buyer_profile, require_write=False):
    """Whether `user` may act on behalf of `buyer_profile` — either it's their
    own profile, or they're a member of it ('viewer' members only when
    require_write is False)."""
    if buyer_profile is None:
        return False
    own = getattr(user, "buyer_profile", None)
    if own is not None and own.id == buyer_profile.id:
        return True
    try:
        membership = BuyerAccountMember.objects.get(buyer_profile=buyer_profile, user=user)
    except BuyerAccountMember.DoesNotExist:
        return False
    if require_write and membership.role == BuyerAccountMemberRole.VIEWER:
        return False
    return True


def resolve_active_buyer_profile(request, require_write=False):
    """
    The single BuyerProfile a buyer-scoped action (cart, checkout, reorder,
    subscribe) should act on behalf of for this request.

    Defaults to the user's own BuyerProfile. Sending `X-Buyer-Account: <id>`
    switches to that business account instead, if the user is authorized for
    it (own profile, or a non-viewer membership when require_write=True).

    Returns None if there's no authorized profile for this request/action —
    callers should treat that as a 403.
    """
    user = request.user
    own = getattr(user, "buyer_profile", None)

    header_value = request.headers.get("X-Buyer-Account")
    if not header_value:
        return own

    try:
        target_id = int(header_value)
    except (TypeError, ValueError):
        return None

    if own is not None and own.id == target_id:
        return own

    try:
        membership = BuyerAccountMember.objects.select_related("buyer_profile").get(
            buyer_profile_id=target_id, user=user
        )
    except BuyerAccountMember.DoesNotExist:
        return None

    if require_write and membership.role == BuyerAccountMemberRole.VIEWER:
        return None

    return membership.buyer_profile
