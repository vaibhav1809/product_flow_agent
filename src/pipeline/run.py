import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from src.schemas.product import AppFeaturesParser

SYSTEM_PROMPT = (
    "You are a product analyst extracting structured app information from a demo "
    "video transcript. Use only the provided context and avoid assumptions. "
    "{format_instructions}"
)

HUMAN_PROMPT = (
    "Context from the demo video:\n"
    "{context}\n\n"
    "Extract the app details and all features discussed."
)


def _get_google_api_key() -> str:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Missing GOOGLE_API_KEY or GEMINI_API_KEY in the environment.")
    return api_key


def build_extraction_chain():
    parser = AppFeaturesParser()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", HUMAN_PROMPT),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    model = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        temperature=0,
        google_api_key=_get_google_api_key(),
    )

    return prompt | model | parser


def extract_app_and_features(context: str):
    chain = build_extraction_chain()
    return chain.invoke({"context": context})
