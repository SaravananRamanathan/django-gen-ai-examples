"""
Google LLM service for generating RAG responses.
Usage:
    from chat_bot.services.llm_service import google_llm_service
    response = google_llm_service.generate_calendar_response(
        user_email="user@example.com",
        query="What are my events for today?"
    )
old method: generate_calendar_response_old. # Deprecated, use new method.
new method: generate_calendar_response.
"""

import json
import logging
import re
from typing import Optional

import google.genai as genai
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.template import Context, Template
from django.utils.html import strip_tags

from chat_bot.models import PromptTemplate
from chat_bot.services.rag_service import calendar_rag_service

logger = logging.getLogger(__name__)


class GoogleLLMService:
    """
    Service for generating responses using Google's Generative AI models.
    """

    def __init__(self):
        # Configure Google Generative AI
        api_key = getattr(settings, "GOOGLE_GENERATIVE_AI_API_KEY", None)
        if not api_key:
            raise ValueError("GOOGLE_GENERATIVE_AI_API_KEY not found in settings")

        # Initialize the new google-genai client
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-pro"
        self.prompt_lookup_key = "calendar-rag-prompt"

    def generate_calendar_response(
        self,
        user_email: str,
        query: str,
        rag_query_str: Optional[str] = None,
        include_attachments: bool = True,
        date_range_days: Optional[int] = 90,
    ) -> dict:
        """
        Generate a response to a calendar-related query using RAG with self-querying logic.

        Args:
            user_email: Email of the user making the query
            query: Natural language query about calendar events
            include_attachments: Whether to include attachment content
            date_range_days: Limit search to events within N days

        Returns:
            Dictionary with response and metadata
        """
        # Use self-querying to determine RAG query and parameters
        query_analysis = {}
        if not rag_query_str:
            query_analysis = self._analyze_user_query(query)
            rag_query_str = query_analysis.get("rag_query", query)

            include_attachments = query_analysis.get("include_attachments", include_attachments)
            date_range_days = query_analysis.get("date_range_days", date_range_days)

            logger.info(f"Self-querying analysis: {query_analysis}")
            logger.info(f"Using RAG query: '{rag_query_str}' instead of original: '{query}'")

        start_time = self._get_current_time_ms()

        # Retrieve relevant calendar events using the LLM optimized RAG query
        events, scores, rag_query = calendar_rag_service.query_calendar_events(
            user_email=user_email,
            query_text=rag_query_str or query,  # use user query if LLM Query gen fails.
            include_attachments=include_attachments,
            date_range_days=date_range_days,
            time_focus=query_analysis.get("time_focus"),
            entities=query_analysis.get("entities"),
        )

        if not events:
            response = "I couldn't find any relevant calendar events for your query. Please try rephrasing your question or check if you have events in your calendar for the specified time period."

            if rag_query:
                rag_query.generated_response = response
                rag_query.model_used = self.model_name
                rag_query.response_time_ms = self._get_current_time_ms() - start_time
                rag_query.save()

            return {
                "response": response,
                "events_found": 0,
                "model_used": self.model_name,
                "response_time_ms": self._get_current_time_ms() - start_time,
            }

        # Prepare context for LLM
        context = calendar_rag_service.get_context_for_llm(events, scores)

        # Generate response using Google's LLM
        response = self._generate_response_with_context(query, context)

        # Update RAG query record
        if rag_query:
            rag_query.generated_response = response
            rag_query.model_used = self.model_name
            rag_query.response_time_ms = self._get_current_time_ms() - start_time
            rag_query.save()

        return {
            "response": response,
            "events_found": len(events),
            "model_used": self.model_name,
            "response_time_ms": self._get_current_time_ms() - start_time,
            "events": events,
            "similarity_scores": scores,
            "query_analysis": query_analysis,  # Include analysis for debugging/transparency
        }

    def _analyze_user_query(self, query: str) -> dict:
        """
        Analyze the initial user query to generate a focused RAG query.

        Args:
            query: The initial user query

        Returns:
            LLM Generated Dictionary containing optimized search parameters and RAG query
        """
        try:
            prompt_obj = get_object_or_404(PromptTemplate, lookup_key="calendar-query-analysis-prompt")
            prompt_template_str = strip_tags(prompt_obj.prompt_template or "")
            prompt_template = Template(prompt_template_str)
            analysis_prompt = prompt_template.render(Context({"query": query}))

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[{"role": "user", "parts": [{"text": analysis_prompt}]}],
            )

            if response and response.text:
                json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())

                    # Validate LLM Results and set defaults
                    result = {
                        "rag_query": analysis.get("rag_query", query),
                        "include_attachments": analysis.get("include_attachments", True),
                        "date_range_days": min(max(analysis.get("date_range_days", 90), 1), 365),
                        "time_focus": analysis.get("time_focus", "all"),
                        "intent": analysis.get("intent", "search"),
                        "entities": analysis.get("entities", []),
                    }

                    logger.info(f"LLM Generated Query data: {result}")
                    return result
                else:
                    logger.warning("No JSON found in LLM response")

        except Exception as e:
            logger.error(f"Error in query analysis: {e}")

        # Fallback to original query
        logger.warning("Using fallback query analysis")
        return {
            "rag_query": query,
            "include_attachments": True,
            "date_range_days": 90,
            "time_focus": "all",
            "intent": "search",
            "entities": [],
        }

    def _generate_response_with_context(self, query: str, context: str) -> str:
        """Generate response using Google's LLM with calendar context."""

        prompt_obj = get_object_or_404(PromptTemplate, lookup_key=self.prompt_lookup_key)
        prompt_template_str = strip_tags(prompt_obj.prompt_template or "")
        prompt_template = Template(prompt_template_str)
        prompt = prompt_template.render(Context({"context": context, "query": query}))

        logger.warning("using prompt = %s", prompt)

        try:
            # NOTE: using streaming for Proof Of Concept:
            logger.warning("Starting LLM streaming as a Proof Of Concept.")
            response_stream = self.client.models.generate_content_stream(
                model=self.model_name,
                # NOTE: for some reason it does not work if i pass the prompt directly.
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
            )

            response = ""
            chunk_count = 0
            for chunk in response_stream:
                if chunk.text:
                    chunk_count += 1
                    chunk_text = chunk.text
                    response += chunk_text

                    # NOTE: just for Proof of Concept, remove in production if doing it in background.
                    chunk_preview = chunk_text[:80] + "..." if len(chunk_text) > 80 else chunk_text
                    logger.info(f"Chunk {chunk_count}: {chunk_preview}")

            logger.info(f"Streaming complete! Received {chunk_count} chunks, total length: {len(response)} characters")
            return response.strip() if response else "No response generated"

        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return f"I found {len(context.split('---')) - 1} relevant calendar events for your query, but I'm having trouble generating a detailed response right now. Please try again or rephrase your question."

    def generate_calendar_summary(self, user_email: str, time_period: str = "today") -> dict:
        """
        Generate a summary of calendar events for a specific time period.

        Args:
            user_email: Email of the user
            time_period: "today", "tomorrow", "this_week", "next_week"

        Returns:
            Dictionary with summary and metadata
        """
        # Map time periods to queries
        period_queries = {
            "today": "What are my events for today?",
            "tomorrow": "What are my events for tomorrow?",
            "this_week": "What are my events for this week?",
            "next_week": "What are my events for next week?",
            "this_month": "What are my events for this month?",
        }

        query = period_queries.get(time_period, f"What are my events for {time_period}?")

        return self.generate_calendar_response(
            user_email=user_email,
            query=query,
            include_attachments=False,
            date_range_days=30 if time_period in ["this_month"] else 7,
        )

    def answer_meeting_question(self, user_email: str, meeting_topic: str) -> dict:
        """
        Answer questions about specific meetings or topics.

        Args:
            user_email: Email of the user
            meeting_topic: Topic or keyword to search for

        Returns:
            Dictionary with response and metadata
        """
        query = f"Tell me about meetings or events related to {meeting_topic}"

        return self.generate_calendar_response(
            user_email=user_email,
            query=query,
            include_attachments=True,  # Include attachment content for detailed questions
            date_range_days=90,
        )

    def find_free_time(self, user_email: str, duration_minutes: int = 60, date_range_days: int = 7) -> dict:
        """
        Find free time slots in the user's calendar.

        Args:
            user_email: Email of the user
            duration_minutes: Required duration in minutes
            date_range_days: Number of days to look ahead

        Returns:
            Dictionary with free time suggestions
        """
        query = f"When do I have free time in the next {date_range_days} days for a {duration_minutes}-minute meeting?"

        return self.generate_calendar_response(
            user_email=user_email, query=query, include_attachments=False, date_range_days=date_range_days
        )

    def _get_current_time_ms(self) -> int:
        """Get current time in milliseconds."""
        import time

        return int(time.time() * 1000)

    def generate_calendar_response_old(
        self,
        user_email: str,
        query: str,
        include_attachments: bool = True,
        date_range_days: Optional[int] = 90,
    ) -> dict:
        """
        NOTE: Deprecated. ref to new method: generate_calendar_response
        Generate response using the same query for both RAG and LLM.
        The reason this failed: RAG was unable to find matches based on user query written for llm.
        """
        start_time = self._get_current_time_ms()

        events, scores, rag_query = calendar_rag_service.query_calendar_events(
            user_email=user_email,
            query_text=query,
            include_attachments=include_attachments,
            date_range_days=date_range_days,
        )

        if not events:
            response = "I couldn't find any relevant calendar events for your query. Please try rephrasing your question or check if you have events in your calendar for the specified time period."

            if rag_query:
                rag_query.generated_response = response
                rag_query.model_used = self.model_name
                rag_query.response_time_ms = self._get_current_time_ms() - start_time
                rag_query.save()

            return {
                "response": response,
                "events_found": 0,
                "model_used": self.model_name,
                "response_time_ms": self._get_current_time_ms() - start_time,
            }

        # Prepare context for LLM
        context = calendar_rag_service.get_context_for_llm(events, scores)

        # Generate response using Google's LLM with original query
        response = self._generate_response_with_context(query, context)

        # Update RAG query record
        if rag_query:
            rag_query.generated_response = response
            rag_query.model_used = self.model_name
            rag_query.response_time_ms = self._get_current_time_ms() - start_time
            rag_query.save()

        return {
            "response": response,
            "events_found": len(events),
            "model_used": self.model_name,
            "response_time_ms": self._get_current_time_ms() - start_time,
            "events": events,
            "similarity_scores": scores,
        }


# import google_llm_service to use in other modules.
google_llm_service = GoogleLLMService()
