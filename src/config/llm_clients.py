from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI


class LLMClients:
    # models for creating repo
    FEATURE_EXTRACTOR_MODEL = ChatGoogleGenerativeAI(model="gemini-3-pro-preview", temperature=0)
    FLOW_EXTRACTOR_MODEL = ChatGoogleGenerativeAI(model="gemini-3-pro-preview", temperature=0)
    SCREEN_EXTRACTOR_MODEL = ChatGoogleGenerativeAI(model="gemini-3-pro-preview", temperature=0)
    INTERACTION_EXTRACTOR_MODEL = ChatGoogleGenerativeAI(
        model="gemini-3-pro-preview", temperature=0)

    # models for quering
    QUERY_PLANNER_MODEL = ChatGoogleGenerativeAI(model="gemini-3-pro-preview", temperature=0)
    QUERY_SEARCH_MODEL = ChatGoogleGenerativeAI(model="gemini-3-pro-preview", temperature=0)
