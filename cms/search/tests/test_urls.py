from django.urls import include, path

urlpatterns = [
    path("", include("cms.search.urls")),
]
