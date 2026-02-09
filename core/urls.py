# core/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path("", views.index),
    path("api/domains/", views.list_domains),
    path("api/roles/<str:domain_id>/", views.list_roles),

    path("api/start/", views.start_interview),
    path("api/next/", views.next_question),

    path("api/tts/", views.tts_only),
]