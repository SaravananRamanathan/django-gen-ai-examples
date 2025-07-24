"""
chat bot app api views
"""

from typing import TYPE_CHECKING, Dict, Optional

from django.shortcuts import get_object_or_404
from django.template import Context, Template
from django.utils.html import strip_tags
from langchain.prompts import ChatPromptTemplate

# from langchain.memory.chat_message_histories import ChatMessageHistory # Deprecated.
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage

# from langchain.chat_models import ChatGooglePalm # Deprecated.
# from langchain_community.chat_models import ChatGooglePalm # Deprecated
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from chat_bot.const import GeminiAPIConstants
from chat_bot.models import DictionaryWord, PromptTemplate
from chat_bot.utils import (
    LCConversationalAgent,
    gemini_completion_request,
    get_gemini_api_key,
    get_youtube_transcript_snippets,
)

from .filters import DictionaryWordFilter
from .serializers import DictionaryWordSerializer

if TYPE_CHECKING:
    from langchain_core.chat_history import BaseChatMessageHistory


class PromptBasedAPIView(APIView):
    """
    Base class for prompt-based API views.
    Provides common functionality for handling prompts and responses.
    """

    prompt_lookup_key: Optional[str] = None

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

    def prompt_render_engine(self, context):
        "By default use Django Template to render prompt"
        template = Template(self._get_prompt_tempate_str())

        return template.render(Context(context))

    def _get_prompt_tempate_str(self) -> str:
        if not self.prompt_lookup_key:
            raise NotImplementedError("Subclasses must define 'prompt_lookup_key.'")

        prompt_obj = get_object_or_404(PromptTemplate, lookup_key=self.prompt_lookup_key)
        # NOTE: convert Rich formated [with html tags.] Prompts from TinyMCE into simple text.
        return strip_tags(prompt_obj.prompt_template or "")

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
            prompt = self.prompt_render_engine(context={"request_message": request_message})
            api_response = self.make_llm_request(prompt=prompt)
        except FileNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return self.standard_response(message_str=api_response)


class SinglePromptAPIView(PromptBasedAPIView):
    "Sends a single prompt chat input to Google Gemini API for response"

    prompt_lookup_key = "single-prompt"

    def make_llm_request(self, prompt: str) -> str:
        "Overrided to add additional context to the prompt."
        additional_messages = [{"role": "developer", "content": "You are a helpful assistant."}]
        return gemini_completion_request(
            prompt=prompt,
            additional_messages=additional_messages,
        )


class SummarizeTextAPIView(PromptBasedAPIView):
    "Summarizes the provided text using Gemini API"

    prompt_lookup_key = "summarize-text-prompt"


class SentimentAnalysisAPIView(PromptBasedAPIView):
    "Performs sentiment analysis on the provided text using Gemini API"

    prompt_lookup_key = "sentiment-prompt"


class LCTranslateAPIView(PromptBasedAPIView):
    """
    LangChain: translate using prompt template [ChatPromptTemplate].
    """

    prompt_lookup_key = "langchain-prompt-template-translate"

    def prompt_render_engine(self, context: dict):
        "Overridden to use ChatPromptTemplate Engine."
        prompt_template = ChatPromptTemplate.from_template(
            self._get_prompt_tempate_str(),
        )

        language = self.request.data.get("language", "Tamil")
        tone = self.request.data.get("tone", "Sweet")
        return prompt_template.format_messages(
            language=language,
            tone=tone,
            text=context.get("request_message"),
        )

    def make_llm_request(self, prompt: str):
        "Overridden to use LangChain"

        chat = ChatGoogleGenerativeAI(
            temperature=0.3,
            model=GeminiAPIConstants.MODEL,
            google_api_key=get_gemini_api_key(),
        )

        return chat.invoke(prompt).content


class LCConversationAPIView(PromptBasedAPIView):
    """
    Handles stateful conversations using a LangChain Agent.
    [Limited]Conversation history is stored in the Django session.
    """

    def post(self, request, *_, **__):
        user_message = request.data.get("message")
        if not user_message:
            return Response({"error": "Missing message"}, status=status.HTTP_400_BAD_REQUEST)

        # Load conversation history from the session (or start a new one)
        raw_history = request.session.get('conversation_history', [])

        # Find old Conversations, save them as LangChain message objects
        # NOTE: These are later on passed to the Agent, thats how it gets the hisotric context
        messages = []
        for msg in raw_history:
            if msg.get('type') == 'human':
                messages.append(HumanMessage(content=msg.get('content')))
            elif msg.get('type') == 'ai':
                messages.append(AIMessage(content=msg.get('content')))

        session_memory = ChatMessageHistory(messages=messages)

        # init agent with the session history:
        engine = LCConversationalAgent(session_memory=session_memory)

        # Now we run the agent with latest user message:
        # NOTE: At this point it already has access to our previous convos!
        bot_response_text = engine.run_agent(user_message=user_message)

        # Update/Append session history [conversation_history]:
        updated_raw_history = []
        chat_memory: "BaseChatMessageHistory" = engine.memory.chat_memory
        for msg in chat_memory.messages:
            updated_raw_history.append({'type': msg.type, 'content': msg.content})
        request.session['conversation_history'] = updated_raw_history

        # TODO handel errors.

        return Response({"message": bot_response_text}, status=status.HTTP_200_OK)


class LCYouTubeTranscriptAPIView(PromptBasedAPIView):
    """
    Handles YouTube transcript generation using LangChain.
    Since LangChain wrapper is broken, using YouTubeTranscriptApi directly.
    """

    def post(self, request, *_, **__):
        # youtube_url = "https://www.youtube.com/watch?v=cw0cF7icqWA" # COD Mission briefing sample
        # video_id = "_3Yvg7mP44M" # random fox news sample

        video_id = request.data.get("message")
        if not video_id:
            return Response({"error": "Missing video ID"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            transcript_snippets = get_youtube_transcript_snippets(video_id)
        except Exception as e:
            # NOTE: FE is not capable of handling/displaying errors at the moment, so we return a message.
            return Response({"message": str(e)}, status=status.HTTP_200_OK)

        if not transcript_snippets:
            return Response(
                {"message": "No transcript found for the provided YouTube video."}, status=status.HTTP_200_OK
            )

        full_transcript = " ".join(item.text for item in transcript_snippets)

        formatted_message = (
            f"<h4>Transcript for Video ID: {video_id}</h4>"
            f"<div style='max-height: 400px; overflow-y: auto; border: 1px solid #444; padding: 10px; border-radius: 5px;'>"
            f"<p>{full_transcript}</p>"
            f"</div>"
        )

        return Response({"message": formatted_message}, status=status.HTTP_200_OK)


class DictionarySearchAPIView(ListAPIView):
    """
    DictionaryWord List API View.
    """

    serializer_class = DictionaryWordSerializer
    queryset = DictionaryWord.objects.all().prefetch_related("meanings")
    # search_fields = ["^term"] # Not feasible for semantic search.
    filterset_class = DictionaryWordFilter
