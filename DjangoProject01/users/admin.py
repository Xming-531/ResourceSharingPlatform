from django.contrib import admin

from users.models import HomeMarqueeSlide


@admin.register(HomeMarqueeSlide)
class HomeMarqueeSlideAdmin(admin.ModelAdmin):
    list_display = (
        "slide_id",
        "title",
        "subtitle",
        "track",
        "sort_order",
        "enabled",
        "image_url",
    )
    list_filter = ("track", "enabled")
    search_fields = ("title", "subtitle", "image_url")
    ordering = ("track", "sort_order", "slide_id")
    list_editable = ("sort_order", "enabled")
