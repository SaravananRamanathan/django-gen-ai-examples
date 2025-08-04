"""
All Utility functions for the Chat Bot application.
"""

from typing import TYPE_CHECKING, List, Optional

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from langchain.agents import AgentExecutor, create_react_agent
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_openai import ChatOpenAI
from openai import OpenAI

# from langchain_community.document_loaders import YoutubeLoader # Broken. use youtube_transcript_api directly.
# Why bother using LangChain wrappers when we can use the original library directly? This is dumb.
from youtube_transcript_api._api import YouTubeTranscriptApi

from .const import GeminiAPIConstants, SidebarMenuChoices

if TYPE_CHECKING:
    from youtube_transcript_api._transcripts import FetchedTranscript, FetchedTranscriptSnippet, TranscriptList


def get_sidebar_menu_choices():
    """
    Process sidebar menu choices to reverse API Url's.
    Returns:
        list: Processed list with API URLs.
    """
    choices = SidebarMenuChoices.choices()
    for choice in choices:
        sub_items = choice.get(SidebarMenuChoices.SUB_ITEMS_KEY, [])
        if not sub_items and SidebarMenuChoices.API_URL_NAME_KEY in choice:
            choice[SidebarMenuChoices.API_URL_KEY] = reverse(choice[SidebarMenuChoices.API_URL_NAME_KEY])
            continue
        for sub_item in sub_items:
            if SidebarMenuChoices.API_URL_NAME_KEY in sub_item:
                sub_item[SidebarMenuChoices.API_URL_KEY] = reverse(sub_item[SidebarMenuChoices.API_URL_NAME_KEY])
    return choices


def get_gemini_api_key() -> str:
    """
    Retrieve the Gemini API key from cache or ENV.
    Returns:
        str: The Gemini API key.
    """
    gemini_api_key = cache.get(GeminiAPIConstants.GEMINI_API_KEY_CACHE)
    if not gemini_api_key:
        gemini_api_key = GeminiAPIConstants.get_api_key()
        cache.set(
            GeminiAPIConstants.GEMINI_API_KEY_CACHE,
            gemini_api_key,
            GeminiAPIConstants.CACHE_TIMEOUT,
        )
    return gemini_api_key


def gemini_completion_request(
    prompt: str,
    prompt_file_path: Optional[str] = None,
    additional_messages: Optional[List] = None,
    model: str = "gemini-2.5-flash",
) -> str:
    """
    Make a Gemini API completion request. and return the response.
    Args:
        prompt (str): The prompt to send to the Gemini API.
        prompt_file_path (Optional[str]): Optional file path for the prompt.
        model (str): The model to use for the completion request.
    """
    api_key = get_gemini_api_key()
    client = OpenAI(
        api_key=api_key,
        base_url=GeminiAPIConstants.BASE_URL,
    )

    if prompt_file_path:
        # TODO: Need to figure out how to handel dynamic variables in prompt files.
        with open(prompt_file_path, "r", encoding="utf-8") as file:
            messages = [{"role": "user", "content": file.read()}]
    else:
        messages = [{"role": "user", "content": prompt}]

    messages.extend(additional_messages or [])

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
    )

    return completion.choices[0].message.content


class LCConversationalAgent:
    """
    Manages LangChain ReAct [It's not React:)] agent.
    Re-Act: Reasoning and Acting!
    with a Tavily search tool and conversational memory.
    """

    def __init__(self, session_memory):
        llm = ChatOpenAI(
            model_name=GeminiAPIConstants.MODEL,
            openai_api_base="https://generativelanguage.googleapis.com/v1beta/",
            openai_api_key=get_gemini_api_key(),
            temperature=0.7,
        )

        search_tool = TavilySearchResults(max_results=2, tavily_api_key=settings.TAVILY_API_KEY)
        tools = [search_tool]

        # Set up memory, using the history passed from the Django session "conversation_history"
        self.memory = ConversationBufferWindowMemory(
            # Remember the last x interactions.
            # (1 user msg + 1 ai msg = 1 interaction)
            k=5,  # interactions count
            memory_key="chat_history",
            input_key="input",
            output_key="output",
            chat_memory=session_memory,
        )

        # ReAct Agent Prompt Template:
        # NOTE: agent_scratchpad is like Agent Rough Work.
        # agent_scratchpad contains previous agent actions
        template = """
            You are a helpful conversational assistant. Your goal is to be helpful, friendly, and engaging.
            You have access to the following tools: {tools}
            Use the following format:
            Question: the input question you must answer
            Thought: you should always think about what to do
            Action: the action to take, should be one of [{tool_names}]
            Action Input: the input to the action
            Observation: the result of the action
            ... (this Thought/Action/Action Input/Observation can repeat N times)
            Thought: I now know the final answer
            Final Answer: the final answer to the original input question
            Begin!
            Previous conversation history:
            {chat_history}
            New question: {input}
            {agent_scratchpad}
        """
        prompt = PromptTemplate.from_template(template)

        agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
        # NOTE: Executor - runs agent loop.
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
        )

    def run_agent(self, user_message):
        """
        Process user's input and returns the response.
        """
        response = self.agent_executor.invoke({"input": user_message})
        return response.get("output", "Sorry, error happened :(")


def get_youtube_transcript_snippets(video_id: str) -> List["FetchedTranscriptSnippet"]:
    """
    Fetch YouTube transcript snippets for a given video ID.
    Args:
        video_id (str): The ID of the YouTube video.
    Returns:
        List[FetchedTranscriptSnippet]: List of transcript snippets.
        @dataclass
        class FetchedTranscriptSnippet:
            text: str
            start: float
            duration: float
    """
    # video_id = "_3Yvg7mP44M" # random fox news sample to test with.

    # TODO: Pass http_client to bypass YT IP bans.
    # NOTE: YT bans ip -- I have not not idea on the limit, but I just made about 3-4 req and alreayd got banned:(
    # NOTE: Even after IP ban normal YT still works, so this is not a real ban, just a YT API ban of sorts..
    YTTranscriptAPI = YouTubeTranscriptApi()
    transcript_list: "TranscriptList" = YTTranscriptAPI.list(video_id)

    transcript_snippets: List["FetchedTranscriptSnippet"] = []
    for transcript in transcript_list:
        fetched_transcript: "FetchedTranscript" = transcript.fetch(preserve_formatting=True)
        transcript_snippets.extend(fetched_transcript.snippets)

    return transcript_snippets
