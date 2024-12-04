from django.urls import path

from . import views

app_name = "bundles"
urlpatterns = [
    path("add/<int:page_to_add_id>/", views.add_to_bundle, name="add_to_bundle"),
]
