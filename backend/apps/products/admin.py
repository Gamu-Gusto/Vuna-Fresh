from django import forms
from django.contrib import admin, messages
from django.core.files.storage import default_storage
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .catalogue_import import import_catalogue
from .category_import import import_categories
from .csv_import import CSVImportError
from .models import CatalogueItem, Category, Product, SurplusListing, WastageMetric
from .utils import InvalidImageError, store_product_image, validate_product_image


class CSVImportForm(forms.Form):
    csv_file = forms.FileField(label="CSV file")


def _listed(count, singular, plural, names):
    return f"{count} {singular if count == 1 else plural}: {', '.join(names)}."


class CSVImportAdminMixin:
    """
    Adds an "Import from CSV" button and page to a ModelAdmin. Subclasses set
    import_title, import_help (HTML), import_example, and implement
    run_import(file), returning [(messages_level, text), ...].
    """
    change_list_template = "admin/products/change_list_with_import.html"

    def get_urls(self):
        opts = self.model._meta
        return [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name=f"{opts.app_label}_{opts.model_name}_import_csv",
            ),
            *super().get_urls(),
        ]

    def import_csv_view(self, request):
        opts = self.model._meta
        changelist = f"admin:{opts.app_label}_{opts.model_name}_changelist"
        if not self.has_add_permission(request):
            return redirect(changelist)

        form = CSVImportForm(request.POST or None, request.FILES or None)
        errors = []
        if request.method == "POST" and form.is_valid():
            try:
                results = self.run_import(form.cleaned_data["csv_file"])
            except CSVImportError as e:
                errors = e.errors
            else:
                for level, text in results:
                    messages.add_message(request, level, text)
                return redirect(changelist)

        return TemplateResponse(request, "admin/products/csv_import.html", {
            **self.admin_site.each_context(request),
            "opts": opts,
            "title": self.import_title,
            "import_help": mark_safe(self.import_help),  # fixed text set in code, not user input
            "import_example": self.import_example,
            "form": form,
            "errors": errors,
        })


@admin.register(Category)
class CategoryAdmin(CSVImportAdminMixin, admin.ModelAdmin):
    list_display = ["name", "parent_category"]
    list_filter = ["parent_category"]
    search_fields = ["name"]

    import_title = "Import categories from CSV"
    import_help = (
        "One category per row, with a header row. <strong>parent</strong> is optional: it names a category "
        "that already exists or is elsewhere in the same file. Categories that already exist are skipped."
    )
    import_example = "\n".join([
        "name,parent",
        "Vegetables,",
        "Leafy Greens,Vegetables",
        "Root Vegetables,Vegetables",
        "Fruit,",
        "Citrus,Fruit",
    ])

    def run_import(self, csv_file):
        created, skipped = import_categories(csv_file)
        results = []
        if created:
            results.append((messages.SUCCESS, "Imported " + _listed(len(created), "category", "categories", created)))
        if skipped:
            results.append((messages.INFO, "Skipped " + _listed(len(skipped), "category that already exists", "categories that already exist", skipped)))
        return results


@admin.register(CatalogueItem)
class CatalogueItemAdmin(CSVImportAdminMixin, admin.ModelAdmin):
    list_display = ["code", "name", "category", "default_unit", "is_active"]
    list_filter = ["is_active", "category__parent_category", "category"]
    search_fields = ["code", "name"]
    list_select_related = ["category"]
    readonly_fields = ["created_at", "updated_at"]

    import_title = "Import product catalogue from CSV"
    import_help = (
        "One product per row, with a header row. <strong>Subcategory</strong> is optional. Missing categories "
        "and subcategories are created. Products whose Product_ID already exists are skipped; edit those here "
        "in admin. Renaming a product or changing its category here also updates every farmer's listing of it."
    )
    import_example = "\n".join([
        "Product_ID,Category,Subcategory,Product_Name,Typical_Sales_Unit",
        "SA0001,Vegetables,Root vegetables,Carrot,kg",
        "SA0029,Vegetables,Leafy greens,Spinach,kg",
        "SA0109,Fruits,Citrus,Orange,kg",
    ])

    def run_import(self, csv_file):
        created, new_categories, skipped = import_catalogue(csv_file)
        results = []
        if created:
            results.append((messages.SUCCESS, f"Imported {len(created)} product{'' if len(created) == 1 else 's'} into the catalogue."))
        if new_categories:
            results.append((messages.SUCCESS, "Created " + _listed(len(new_categories), "category", "categories", new_categories)))
        if skipped:
            results.append((messages.INFO, "Skipped " + _listed(len(skipped), "product whose Product_ID already exists", "products whose Product_ID already exists", skipped)))
        return results


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Name and category are copied from the catalogue item (see Product.save).
        # The model allows null only for listings that predate the catalogue.
        self.fields["catalogue_item"].required = True

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
    list_display = ["name", "farmer", "category", "price", "unit", "stock_quantity", "is_available", "is_archived"]
    list_filter = ["is_available", "is_archived", "category"]
    actions = ["remove_products", "restore_products"]

    # Plain deletion would skip the cart, subscription and notification steps
    # (and fail for ordered products); "Remove" below does it properly.
    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Remove (archive if ordered, otherwise delete)")
    def remove_products(self, request, queryset):
        from .archiving import remove_product

        results = [remove_product(p) for p in list(queryset)]
        self.message_user(
            request,
            f"Archived {results.count('archived')}, deleted {results.count('deleted')}. "
            "Subscribed buyers have been told.",
            messages.SUCCESS,
        )

    @admin.action(description="Restore archived products (hidden until the farmer lists them)")
    def restore_products(self, request, queryset):
        from .archiving import RestoreError, restore_product

        restored, problems = 0, []
        for product in queryset:
            try:
                restore_product(product)
                restored += 1
            except RestoreError as e:
                problems.append(f"{product.name}: {e}")
        if restored:
            self.message_user(request, f"Restored {restored} product(s).", messages.SUCCESS)
        for problem in problems:
            self.message_user(request, problem, messages.WARNING)
    search_fields = ["name", "farmer__farm_name"]
    autocomplete_fields = ["catalogue_item"]
    readonly_fields = ["name", "category", "is_archived", "archived_at", "created_at", "updated_at", "image_preview"]
    fields = [
        "farmer", "catalogue_item", "name", "category", "description",
        "price", "unit", "stock_quantity", "low_stock_threshold", "is_available", "is_archived", "archived_at",
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
