"""
chat bot app api urls
"""

from django.urls import path

from . import views

app_name = "chatbot-api"

urlpatterns = [
    path("single-prompt/", views.SinglePromptAPIView.as_view(), name="single_prompt"),
    path("summarize/", views.SummarizeTextAPIView.as_view(), name="summarize_text"),
    path("sentiment/", views.SentimentAnalysisAPIView.as_view(), name="sentiment_analysis"),
    path("lc/translate/", views.LCTranslateAPIView.as_view(), name="lc_translate"),
    path("lc/conversation/", views.LCConversationAPIView.as_view(), name="lc_conversation"),
    path("lc/youtube_transcript/", views.LCYouTubeTranscriptAPIView.as_view(), name="lc_youtube_transcript"),
    path("dictionary/search/", views.DictionarySearchAPIView.as_view(), name="dictionary_search"),
    path("calendar/rag/", views.CalendarRAGAPIView.as_view(), name="calendar_rag"),
    path("calendar/llm-rag/", views.CalendarLLMRAGAPIView.as_view(), name="calendar_llm_rag"),
]
