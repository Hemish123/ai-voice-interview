from django.urls import path
from core import views
from django.http import HttpResponse

def favicon(request):
    return HttpResponse(status=204)

urlpatterns = [

    path("", views.index),

    # predefined dropdown
    path("api/start/", views.api_start),
    path("api/domains/", views.api_domains),
    path("api/roles/<str:domain_id>/", views.api_roles),

    # JD auto
    path("api/start-auto/", views.api_start_auto),
    path("api/next/", views.api_next),
    path("favicon.ico", favicon),


]