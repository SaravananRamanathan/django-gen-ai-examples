"""
chat bot app api views
"""
import os

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from openai import OpenAI


class GeminiAPIView(APIView):
    "Sends chat input to Google Gemini API for response"

    def post(self, request, *_, **__):
        "Handel API request to Gemini API"
        user_message = request.data.get("message")
        if not user_message:
            return Response(
                {"error": "Missing message"},
                status=status.HTTP_400_BAD_REQUEST
            )

        api_key = os.getenv('GEMINI_API_KEY')
        client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

        completion = client.chat.completions.create(
          model="gemini-2.5-flash",
          messages=[
            {"role": "developer", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message}
          ]
        )
        response = completion.choices[0].message.content
        bot_response_text = f"{response}"

        return Response(
            {"message": bot_response_text},
            status=status.HTTP_200_OK
        )
