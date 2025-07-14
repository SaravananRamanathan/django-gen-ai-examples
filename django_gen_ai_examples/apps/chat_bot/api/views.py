"""
chat bot app api views
"""

from typing import Dict, Optional

from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from chat_bot.utils import gemini_completion_request


class PromptBasedAPIView(APIView):
    """
    Base class for prompt-based API views.
    Provides common functionality for handling prompts and responses.
    """

    prompt_template_name: Optional[str] = None

    def standard_response(
        self,
        message_str: Optional[str] = None,
        message_data: Optional[Dict] = None,
        status_code: int = status.HTTP_200_OK,
    ) -> Response:
        """
        Standard response format for API responses.
        Args:
            message_str (str): The message to return.
            message_data (Optional[Dict]): Additional data to include in the response.
            status_code (int): HTTP status code for the response.
        Returns:
            Response: A DRF Response object with the specified message and data.
        """
        response_data = {"message": message_str}
        if message_data:
            response_data.update(message_data)
        return Response(response_data, status=status_code)

    def _get_rendered_prompt(self, context):
        "Loads and renders the specified prompt template."
        if not self.prompt_template_name:
            raise NotImplementedError("Subclasses must define 'prompt_template_name.'")

        try:
            return render_to_string(self.prompt_template_name, context)
        except TemplateDoesNotExist as e:
            raise FileNotFoundError(
                f"Prompt template '{self.prompt_template_name}' not found. "
                "Ensure it exists in a directory registered in settings.TEMPLATES['DIRS']."
            ) from e

    def make_llm_request(self, prompt: str) -> str:
        """
        Make a request to the LLM with the provided prompt.
        Args:
            prompt (str): The prompt to send to the LLM.
        Returns:
            str: The response from the LLM.
        Child calss can override this method to implement specific LLM requests.
        """
        return gemini_completion_request(prompt=prompt)

    def post(self, request, *_, **__):
        "Defautl post method for all PromptBasedAPIView."
        request_message = request.data.get("message")
        if not request_message:
            return Response({"error": "Missing message"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            prompt = self._get_rendered_prompt(context={"request_message": request_message})
            api_response = self.make_llm_request(prompt=prompt)
        except FileNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return self.standard_response(message_str=api_response)


class SinglePromptAPIView(PromptBasedAPIView):
    "Sends a single prompt chat input to Google Gemini API for response"

    prompt_template_name = "single_prompt.txt"

    def make_llm_request(self, prompt: str) -> str:
        "Overrided to add additional context to the prompt."
        additional_messages = [{"role": "developer", "content": "You are a helpful assistant."}]
        return gemini_completion_request(
            prompt=prompt,
            additional_messages=additional_messages,
        )


class SummarizeTextAPIView(PromptBasedAPIView):
    "Summarizes the provided text using Gemini API"

    prompt_template_name = "summarize_text_prompt.txt"


class SentimentAnalysisAPIView(PromptBasedAPIView):
    "Performs sentiment analysis on the provided text using Gemini API"

    prompt_template_name = "sentiment_prompt.txt"
