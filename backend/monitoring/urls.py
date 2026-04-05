from django.urls import path

from monitoring import views

urlpatterns = [
    path("health", views.HealthView.as_view()),
    path("patients", views.PatientsListView.as_view()),
    path("infrastructure", views.InfrastructureView.as_view()),
    path("departments", views.DepartmentListCreateView.as_view()),
    path("departments/<str:pk>", views.DepartmentDetailView.as_view()),
    path("rooms", views.RoomListCreateView.as_view()),
    path("rooms/<str:pk>", views.RoomDetailView.as_view()),
    path("beds", views.BedListCreateView.as_view()),
    path("beds/<str:pk>", views.BedDetailView.as_view()),
    path("devices", views.DeviceListCreateView.as_view()),
    path("devices/<str:pk>/vitals", views.DeviceVitalsByIdView.as_view()),
    path("devices/<str:pk>", views.DeviceDetailView.as_view()),
    path("device/<str:ip>/vitals", views.DeviceVitalsIngestView.as_view()),
]
