from django.urls import path

from inspection import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.list_view, name="list"),
    path("inspections/new/", views.create_view, name="create"),
    path("inspections/<int:pk>/", views.detail_view, name="detail"),
    path("comparisons/", views.comparison_list_view, name="comparison_list"),
    path("comparisons/<int:pk>/", views.comparison_detail_view, name="comparison_detail"),
    path("comparisons/new/", views.comparison_create_view, name="comparison_create"),
]
