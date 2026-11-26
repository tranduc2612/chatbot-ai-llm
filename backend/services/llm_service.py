import logging

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from core.config import settings


logger = logging.getLogger(__name__)


class LLMService:

    def __init__(self):
        self.llm = self._initialize_model()

    def _initialize_model(self):

        provider = settings.LLM_PROVIDER.lower()

        if provider == "cloudflare":

            if not settings.CF_ACCOUNT_ID:
                raise ValueError("CF_ACCOUNT_ID is missing")

            if not settings.CF_API_TOKEN:
                raise ValueError("CF_API_TOKEN is missing")

            base_url = (
                "https://api.cloudflare.com/client/v4/accounts/"
                f"{settings.CF_ACCOUNT_ID}/ai/v1"
            )

            return ChatOpenAI(
                model=settings.CF_MODEL,
                api_key=settings.CF_API_TOKEN,
                base_url=base_url,
                temperature=0.7,
                timeout=60,
                max_retries=1,
            )

        elif provider == "ollama":

            return ChatOllama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0.7,
            )

        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider}"
            )

    async def generate_response(self, message: str) -> str:

        try:
            response = await self.llm.ainvoke(message)

            return str(response.content)

        except Exception as e:
            logger.exception("LLM generation failed")
            print("ERROR TYPE:", type(e).__name__)
            print("ERROR DETAIL:", str(e))
            raise


llm_service = LLMService()