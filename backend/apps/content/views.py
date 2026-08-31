from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from .models import Skill
from .selectors import active_task_types, published_versions
from .serializers import ContentCatalogSerializer, PublicContentSerializer, TaskTypeSerializer


class TaskTypeListView(ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    serializer_class = TaskTypeSerializer
    pagination_class = None

    def get_queryset(self):
        skill = self.request.query_params.get("skill", Skill.READING)
        if skill not in Skill.values:
            return active_task_types(Skill.READING).none()
        return active_task_types(skill)


class ContentCatalogView(ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    serializer_class = ContentCatalogSerializer
    skill = Skill.READING

    def get_queryset(self):
        # ContentCatalogSerializer exposes only item-level fields, so the
        # question/choice prefetch that published_versions() sets up for the
        # detail view is pure overhead here — two extra queries plus the model
        # instantiation for every question and choice on the page.
        queryset = published_versions(self.skill).prefetch_related(None)
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
    skill = Skill.READING

    def get_queryset(self):
        return published_versions(self.skill)


class ListeningCatalogView(ContentCatalogView):
    skill = Skill.LISTENING


class ListeningDetailView(ContentDetailView):
    skill = Skill.LISTENING


class WritingCatalogView(ContentCatalogView):
    skill = Skill.WRITING


class WritingDetailView(ContentDetailView):
    skill = Skill.WRITING


class SpeakingCatalogView(ContentCatalogView):
    skill = Skill.SPEAKING


class SpeakingDetailView(ContentDetailView):
    skill = Skill.SPEAKING
