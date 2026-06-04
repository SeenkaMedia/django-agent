from django.urls import path

from . import views

app_name = "django_agent"

urlpatterns = [
    path("history/", views.history, name="history"),
    path("message/", views.message, name="message"),
    path("confirm/", views.confirm, name="confirm"),
    path("reset/", views.reset, name="reset"),
]
