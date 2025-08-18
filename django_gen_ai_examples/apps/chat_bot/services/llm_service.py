"""
Google LLM service for generating RAG responses.
Usage:
    from chat_bot.services.llm_service import google_llm_service
    response = google_llm_service.generate_calendar_response(
        user_email="user@example.com",
        query="What are my events for today?"
    )
"""

import json
import logging
import re
import time
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
    ):
        """
        Generate a streaming response to a calendar-related query using RAG with self-querying logic.
        This is now a generator that yields streaming events.

        Args:
            user_email: Email of the user making the query
            query: Natural language query about calendar events
            rag_query_str: Optional pre-optimized RAG query
            include_attachments: Whether to include attachment content
            date_range_days: Limit search to events within N days

        Yields:
            Tuples of (event_type, data) where event_type can be:
            - "status": Status updates during processing
            - "chunk": Text chunks from LLM
            - "complete": Final response data with metadata
        """
        # Use self-querying to determine RAG query and parameters
        yield ("status", {"message": "Analyzing query..."})

        query_analysis = {}
        if not rag_query_str:
            query_analysis = self._analyze_user_query(query)
            rag_query_str = query_analysis.get("rag_query", query)
            if query_analysis.get("include_attachments") is not None:
                include_attachments = query_analysis["include_attachments"]
            if query_analysis.get("date_range_days"):
                date_range_days = query_analysis["date_range_days"]

        logger.info("Self-querying analysis: %s", query_analysis)
        logger.info("Using RAG query: '%s' instead of original: '%s'", rag_query_str, query)

        yield ("status", {"message": f"Searching calendar events with query: '{rag_query_str}'..."})

        start_time = self._get_current_time_ms()

        # Retrieve relevant calendar events using the LLM optimized RAG query
        events, scores, rag_query = calendar_rag_service.query_calendar_events(
            user_email=user_email,
            query_text=rag_query_str or query,
            include_attachments=include_attachments,
            date_range_days=date_range_days,
            time_focus=query_analysis.get("time_focus"),
            entities=query_analysis.get("entities"),
        )

        if not events:
            no_events_msg = "I couldn't find any calendar events matching your query. Please try rephrasing your question or check if you have events in the specified time range."
            yield ("chunk", {"text": no_events_msg, "chunk_id": 1})
            yield (
                "complete",
                {
                    "response": no_events_msg,
                    "events_found": 0,
                    "model_used": self.model_name,
                    "response_time_ms": self._get_current_time_ms() - start_time,
                    "events": [],
                    "similarity_scores": [],
                    "query_analysis": query_analysis,
                },
            )
            return

        yield ("status", {"message": f"Found {len(events)} relevant events. Generating response..."})

        # Prepare context for LLM
        context = calendar_rag_service.get_context_for_llm(events, scores)

        # Generate streaming response using Google's LLM
        full_response = ""
        chunk_count = 0

        for chunk_type, chunk_data in self._generate_response_with_context_stream(query, context):
            if chunk_type == "chunk":
                chunk_count += 1
                chunk_text = str(chunk_data.get("text", ""))
                full_response += chunk_text
                yield ("chunk", {"text": chunk_text, "chunk_id": chunk_count})
            elif chunk_type == "error":
                error_msg = str(chunk_data.get("message", ""))
                yield ("chunk", {"text": error_msg, "chunk_id": chunk_count + 1})
                full_response = error_msg
                break

        # Update RAG query record
        if rag_query:
            rag_query.generated_response = full_response
            rag_query.model_used = self.model_name
            rag_query.response_time_ms = self._get_current_time_ms() - start_time
            rag_query.save()

        # Yield final response data
        yield (
            "complete",
            {
                "response": full_response,
                "events_found": len(events),
                "model_used": self.model_name,
                "response_time_ms": self._get_current_time_ms() - start_time,
                "events": events,
                "similarity_scores": scores,
                "query_analysis": query_analysis,
                "chunk_count": chunk_count,
            },
        )

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
            prompt = prompt_template.render(Context({"query": query}))

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
            )

            if response and response.text:
                # Try to extract JSON from the response
                json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    query_data = json.loads(json_str)
                    logger.info("LLM Generated Query data: %s", query_data)
                    return query_data

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

    def _generate_response_with_context_stream(self, query: str, context: str):
        """Generate streaming response using Google's LLM with calendar context."""

        prompt_obj = get_object_or_404(PromptTemplate, lookup_key=self.prompt_lookup_key)
        prompt_template_str = strip_tags(prompt_obj.prompt_template or "")
        prompt_template = Template(prompt_template_str)
        prompt = prompt_template.render(Context({"context": context, "query": query}))

        logger.warning("using prompt = %s", prompt)

        try:
            logger.warning("Starting LLM streaming.")
            response_stream = self.client.models.generate_content_stream(
                model=self.model_name,
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
            )

            chunk_count = 0
            for chunk in response_stream:
                if chunk.text:
                    chunk_count += 1
                    chunk_text = chunk.text

                    # Log chunk for debugging
                    chunk_preview = chunk_text[:80] + "..." if len(chunk_text) > 80 else chunk_text
                    logger.info(f"Chunk {chunk_count}: {chunk_preview}")

                    yield ("chunk", {"text": chunk_text, "chunk_id": chunk_count})

            logger.info(f"Streaming complete! Received {chunk_count} chunks")

        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            error_msg = f"I found relevant calendar events for your query, but I'm having trouble generating a detailed response right now. Please try again or rephrase your question."
            yield ("error", {"message": error_msg})

    def generate_calendar_summary(self, user_email: str, time_period: str = "today") -> str:
        """
        Generate a summary of calendar events for a specific time period.
        Returns the final response text from streaming.

        Args:
            user_email: Email of the user
            time_period: "today", "tomorrow", "this_week", "next_week"

        Returns:
            String with the summary response
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

        # Collect streaming response
        final_response = ""
        for event_type, data in self.generate_calendar_response(
            user_email=user_email,
            query=query,
            include_attachments=False,
            date_range_days=30 if time_period in ["this_month"] else 7,
        ):
            if event_type == "chunk":
                final_response += str(data.get("text", ""))
            elif event_type == "complete":
                return str(data.get("response", final_response))

        return final_response

    def answer_meeting_question(self, user_email: str, meeting_topic: str) -> str:
        """
        Answer questions about specific meetings or topics.
        Returns the final response text from streaming.

        Args:
            user_email: Email of the user
            meeting_topic: Topic or keyword to search for

        Returns:
            String with the response
        """
        query = f"Tell me about meetings or events related to {meeting_topic}"

        # Collect streaming response
        final_response = ""
        for event_type, data in self.generate_calendar_response(
            user_email=user_email,
            query=query,
            include_attachments=True,
            date_range_days=90,
        ):
            if event_type == "chunk":
                final_response += str(data.get("text", ""))
            elif event_type == "complete":
                return str(data.get("response", final_response))

        return final_response

    def find_free_time(self, user_email: str, duration_minutes: int = 60, date_range_days: int = 7) -> str:
        """
        Find free time slots in the user's calendar.
        Returns the final response text from streaming.

        Args:
            user_email: Email of the user
            duration_minutes: Required duration in minutes
            date_range_days: Number of days to look ahead

        Returns:
            String with free time suggestions
        """
        query = f"When do I have free time in the next {date_range_days} days for a {duration_minutes}-minute meeting?"

        # Collect streaming response
        final_response = ""
        for event_type, data in self.generate_calendar_response(
            user_email=user_email, query=query, include_attachments=False, date_range_days=date_range_days
        ):
            if event_type == "chunk":
                final_response += str(data.get("text", ""))
            elif event_type == "complete":
                return str(data.get("response", final_response))

        return final_response

    def _get_current_time_ms(self) -> int:
        """Get current time in milliseconds."""
        return int(time.time() * 1000)


# import google_llm_service to use in other modules.
google_llm_service = GoogleLLMService()
