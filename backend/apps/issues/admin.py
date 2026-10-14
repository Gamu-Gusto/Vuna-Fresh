from django.contrib import admin
from .models import Issue, IssueAttachment, IssueMessage, IssueRating


class IssueAttachmentInline(admin.TabularInline):
    model = IssueAttachment
    extra = 0
    readonly_fields = ["file_url", "uploaded_at"]


class IssueMessageInline(admin.TabularInline):
    model = IssueMessage
    extra = 0
    readonly_fields = ["sender", "message", "sent_at"]


class IssueRatingInline(admin.StackedInline):
    model = IssueRating
    extra = 0
    readonly_fields = ["rating", "comment", "created_at"]
    can_delete = False


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ["id", "reported_by", "category", "status", "resolution_type", "created_at"]
    list_filter = ["status", "category", "resolution_type"]
    search_fields = ["reported_by__email", "description"]
    readonly_fields = ["created_at"]
    inlines = [IssueAttachmentInline, IssueMessageInline, IssueRatingInline]
