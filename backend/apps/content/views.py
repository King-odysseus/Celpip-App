from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from .selectors import active_reading_task_types, published_reading_versions
from .serializers import ContentCatalogSerializer, PublicContentSerializer, TaskTypeSerializer


class TaskTypeListView(ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    serializer_class = TaskTypeSerializer
    pagination_class = None

    def get_queryset(self):
        return active_reading_task_types()


class ContentCatalogView(ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    serializer_class = ContentCatalogSerializer

    def get_queryset(self):
        queryset = published_reading_versions()
        task_type = self.request.query_params.get("task_type")
        difficulty = self.request.query_params.get("difficulty")
        if task_type:
            queryset = queryset.filter(item__task_type_id=task_type)
        if difficulty and difficulty.isdigit():
            queryset = queryset.filter(item__difficulty=int(difficulty))
        return queryset


class ContentDetailView(RetrieveAPIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    serializer_class = PublicContentSerializer
    lookup_field = "item__slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return published_reading_versions()
