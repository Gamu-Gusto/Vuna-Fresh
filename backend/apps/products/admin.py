from django import forms
from django.contrib import admin, messages
from django.core.files.storage import default_storage
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.html import format_html

from .category_import import CategoryImportError, import_categories
from .models import Category, Product, SurplusListing, WastageMetric
from .utils import InvalidImageError, store_product_image, validate_product_image


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent_category"]
    list_filter = ["parent_category"]
    search_fields = ["name"]
    change_list_template = "admin/products/category/change_list.html"

    def get_urls(self):
        return [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="products_category_import_csv",
            ),
            *super().get_urls(),
        ]

    def import_csv_view(self, request):
        if not self.has_add_permission(request):
            return redirect("admin:products_category_changelist")

        form = CategoryCSVImportForm(request.POST or None, request.FILES or None)
        errors = []
        if request.method == "POST" and form.is_valid():
            try:
                created, skipped = import_categories(form.cleaned_data["csv_file"])
            except CategoryImportError as e:
                errors = e.errors
            else:
                if created:
                    noun = "category" if len(created) == 1 else "categories"
                    messages.success(request, f"Imported {len(created)} {noun}: {', '.join(created)}.")
                if skipped:
                    verb = "exists" if len(skipped) == 1 else "exist"
                    messages.info(request, f"Skipped {len(skipped)} that already {verb}: {', '.join(skipped)}.")
                return redirect("admin:products_category_changelist")

        return TemplateResponse(request, "admin/products/category/import_csv.html", {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Import categories from CSV",
            "form": form,
            "errors": errors,
        })


class CategoryCSVImportForm(forms.Form):
    csv_file = forms.FileField(label="CSV file")


class ProductAdminForm(forms.ModelForm):
    # Plain FileField, not ImageField — ImageField needs Pillow to validate the
    # file, which isn't a project dependency. validate_product_image() below
    # checks content-type and size instead.
    image_upload = forms.FileField(
        required=False,
        label="Upload image",
        help_text="JPEG, PNG, WebP or GIF, max 5 MB. Leave blank to keep the current image.",
    )

    class Meta:
        model = Product
        fields = "__all__"
        widgets = {"image_url": forms.TextInput(attrs={"readonly": "readonly"})}

    def clean_image_upload(self):
        image_file = self.cleaned_data.get("image_upload")
        if image_file:
            try:
                validate_product_image(image_file)
            except InvalidImageError as e:
                raise forms.ValidationError(str(e))
        return image_file


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ["name", "farmer", "category", "price", "unit", "stock_quantity", "is_available"]
    list_filter = ["is_available", "category"]
    search_fields = ["name", "farmer__farm_name"]
    readonly_fields = ["created_at", "updated_at", "image_preview"]
    fields = [
        "farmer", "category", "name", "description",
        "price", "unit", "stock_quantity", "low_stock_threshold", "is_available",
        "image_preview", "image_upload", "image_url",
        "created_at", "updated_at",
    ]

    def image_preview(self, obj):
        if not obj.image_url:
            return "(no image)"
        return format_html('<img src="{}" style="max-height:150px;border-radius:6px;" />', obj.image_url)
    image_preview.short_description = "Current image"

    def save_model(self, request, obj, form, change):
        # Uses request.build_absolute_uri here (not in the form) because the form
        # has no access to the request — without it, dev's local FileSystemStorage
        # would save a relative "/media/..." path that the frontend (a different
        # origin) can't resolve, producing a broken image.
        image_file = form.cleaned_data.get("image_upload")
        if image_file:
            saved_path = store_product_image(image_file)
            obj.image_url = request.build_absolute_uri(default_storage.url(saved_path))
        super().save_model(request, obj, form, change)


@admin.register(SurplusListing)
class SurplusListingAdmin(admin.ModelAdmin):
    list_display = ["product", "farmer", "quantity_available", "discount_percentage", "reason", "status", "expires_at"]
    list_filter = ["status", "reason"]
    search_fields = ["product__name", "farmer__farm_name"]
    readonly_fields = ["created_at"]


@admin.register(WastageMetric)
class WastageMetricAdmin(admin.ModelAdmin):
    list_display = ["farmer", "product", "period_start", "period_end", "quantity_listed", "quantity_sold", "quantity_expired_unsold"]
    list_filter = ["period_start"]
    search_fields = ["farmer__farm_name", "product__name"]
