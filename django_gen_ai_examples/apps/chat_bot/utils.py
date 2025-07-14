"""
All Utility functions for the Chat Bot application.
"""

from typing import List, Optional

from django.core.cache import cache
from django.urls import reverse
from openai import OpenAI

from .const import GeminiAPIConstants, SidebarMenuChoices


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
        with open(prompt_file_path, 'r', encoding='utf-8') as file:
            messages = [{"role": "user", "content": file.read()}]
    else:
        messages = [{"role": "user", "content": prompt}]

    messages.extend(additional_messages or [])

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
    )

    return completion.choices[0].message.content
