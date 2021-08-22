from rest_framework import generics
from taskmanagement.models import JobOffer
from taskmanagement.api.permissions import IsAdminUserOrReadOnly
from taskmanagement.api.serializers import JobOfferSerializer


class JobOfferListCreateAPIView(generics.ListCreateAPIView):
    queryset = JobOffer.objects.all().order_by("-id")
    serializer_class = JobOfferSerializer
    permission_classes = [IsAdminUserOrReadOnly]


class JobOfferDetailAPIview(generics.RetrieveUpdateDestroyAPIView):
    queryset = JobOffer.objects.all()
    serializer_class = JobOfferSerializer
    permission_classes = [IsAdminUserOrReadOnly]