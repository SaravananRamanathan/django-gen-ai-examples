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
    path('lc/translate/', views.LCTranslateAPIView.as_view(), name='lc_translate'),
    path('lc/conversation/', views.LCConversationAPIView.as_view(), name='lc_conversation'),
]
