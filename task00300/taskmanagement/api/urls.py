
from django.urls import path
from taskmanagement.api.views import (JobOfferListCreateAPIView, JobOfferDetailAPIview)

urlpatterns = [
    path("taskmanagement/", JobOfferListCreateAPIView.as_view(), name="job-list"),
    path("taskmanagement/<int:pk>/", JobOfferDetailAPIview.as_view(), name="job-detail"),
]