"""
chat bot app api views
"""

from typing import Dict, Optional

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from chat_bot.utils import gemini_completion_request


def retrieve_request_message(request_data: Dict) -> str:
    """
    Retrieve the 'message' from the request data.
    Args:
        request_data (Dict): The request data dict sent to API.
    Returns:
        str: The message if present, otherwise raise error.
    """
    message = request_data.get("message", None)
    if not message:
        return Response({"error": "Missing message"}, status=status.HTTP_400_BAD_REQUEST)
    return message


def standard_response(
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


class SinglePromptAPIView(APIView):
    "Sends a single prompt chat input to Google Gemini API for response"

    def post(self, request, *_, **__):
        "Handel API request to Gemini API"

        request_message = retrieve_request_message(request.data)
        api_response = gemini_completion_request(
            prompt=request_message,
            additional_messages=[{"role": "developer", "content": "You are a helpful assistant."}],
        )
        return standard_response(message_str=api_response)


class SummarizeTextAPIView(APIView):
    "Summarizes the provided text using Gemini API"

    def post(self, request, *_, **__):
        "Handle API request to summarize text"
        request_message = retrieve_request_message(request.data)

        prompt: str = (
            "Your task is to generate a summary of the user written input text, "
            "delimited by triple backticks. "
            f"""\nText: ```{request_message}```"""
        )
        api_response = gemini_completion_request(
            prompt=prompt,
        )

        return standard_response(message_str=api_response)


class SentimentAnalysisAPIView(APIView):
    "Performs sentiment analysis on the provided text using Gemini API"

    def post(self, request, *_, **__):
        "Handle API request to analyze sentiment"
        request_message = retrieve_request_message(request.data)

        prompt: str = (
            "Your task is to analyze the sentiment of the user written input text, "
            "delimited by triple backticks. "
            f"""\nText: ```{request_message}```"""
        )
        api_response = gemini_completion_request(
            prompt=prompt,
        )

        return standard_response(message_str=api_response)
