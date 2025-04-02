from django.urls import path

from .views import ResourceListView

urlpatterns = [
    path("v1/resources", ResourceListView.as_view(), name="resources-list"),
]
