"""
chat bot app api urls
"""

from django.urls import path

from . import views

app_name = 'chatbot-api'

urlpatterns = [
    path('gemini/', views.GeminiAPIView.as_view(), name='gemini_chat_bot'),
    path('summarize/', views.SummarizeTextAPIView.as_view(), name='summarize_text'),
]
