from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI


class LLMClients:
    FEATURE_EXTRACTOR_MODEL = ChatGoogleGenerativeAI(model="gemini-3-pro-preview", temperature=0)
    FLOW_EXTRACTOR_MODEL = ChatGoogleGenerativeAI(model="gemini-3-pro-preview", temperature=0)
