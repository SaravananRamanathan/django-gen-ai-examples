"""
chat bot app api urls
"""

from django.urls import path

from . import views

app_name = 'chatbot-api'

urlpatterns = [
    path('single-prompt/', views.SinglePromptAPIView.as_view(), name='single_prompt'),
    path('summarize/', views.SummarizeTextAPIView.as_view(), name='summarize_text'),
    path('sentiment/', views.SentimentAnalysisAPIView.as_view(), name='sentiment_analysis'),
    path('lc-prompt-template/', views.LCPromptTemplateAPIView.as_view(), name="prompt_template"),
]
