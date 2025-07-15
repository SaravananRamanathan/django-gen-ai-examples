"""
URL configuration for django_gen_ai_examples project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from debug_toolbar.toolbar import debug_toolbar_urls
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView

api_patterns = [
    path(r'chat_bot/', include('chat_bot.api.urls', namespace='chatbot-api')),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="chat_bot:chat_window", permanent=True)),
    path("", include("chat_bot.urls")),
    re_path(r'^api/', include(api_patterns)),
    path("tinymce/", include("tinymce.urls")),
] + debug_toolbar_urls()
