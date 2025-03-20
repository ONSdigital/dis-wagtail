from django.urls import path

from .views.add_to_bundle import AddToBundleView

app_name = "bundles"
urlpatterns = [
    path("add/<int:page_to_add_id>/", AddToBundleView.as_view(), name="add_to_bundle"),
]
