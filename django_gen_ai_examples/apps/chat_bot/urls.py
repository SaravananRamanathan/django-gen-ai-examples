"""
# chat_bot/urls.py
"""
from django.urls import path

from . import views

app_name = "chat_bot"

urlpatterns = [
    path("home/", views.ChatWindowView.as_view(), name="chat_window"),
]
