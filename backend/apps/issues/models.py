from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class IssueCategory(models.TextChoices):
    MISSING_ITEM = "missing_item", "Missing Item"
    DAMAGED_ITEM = "damaged_item", "Damaged Item"
    LATE_DELIVERY = "late_delivery", "Late Delivery"
    WRONG_ORDER = "wrong_order", "Wrong Order"
    APP_BUG = "app_bug", "App Bug"
    PAYMENT_ISSUE = "payment_issue", "Payment Issue"
    ACCOUNT_ISSUE = "account_issue", "Account Issue"


class IssueStatus(models.TextChoices):
    OPEN = "open", "Open"
    IN_PROGRESS = "in_progress", "In Progress"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"


class ResolutionType(models.TextChoices):
    REFUND = "refund", "Refund"
    REPLACEMENT = "replacement", "Replacement"
    DISCOUNT = "discount", "Discount"
    NONE = "none", "None"


class Issue(models.Model):
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="issues",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issues",
        help_text="Left blank for platform-level issues (e.g. app bugs) that aren't tied to an order.",
    )
    category = models.CharField(max_length=20, choices=IssueCategory.choices)
    description = models.TextField()
    status = models.CharField(max_length=15, choices=IssueStatus.choices, default=IssueStatus.OPEN)
    resolution_type = models.CharField(max_length=15, choices=ResolutionType.choices, default=ResolutionType.NONE)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "issues"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Issue({self.pk}, {self.category}, {self.status})"


class IssueAttachment(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="attachments")
    file_url = models.URLField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "issue_attachments"
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"IssueAttachment(issue={self.issue_id})"


class IssueMessage(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="issue_messages",
    )
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "issue_messages"
        ordering = ["sent_at"]

    def __str__(self):
        return f"IssueMessage(issue={self.issue_id}, sender={self.sender_id})"


class IssueRating(models.Model):
    issue = models.OneToOneField(Issue, on_delete=models.CASCADE, related_name="rating")
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "issue_ratings"

    def __str__(self):
        return f"IssueRating(issue={self.issue_id}, {self.rating}★)"
