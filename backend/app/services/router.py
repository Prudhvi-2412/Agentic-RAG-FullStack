from google import genai
from google.genai import types

class QueryRouter:
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        Initializes the QueryRouter with the new google-genai Client.
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=self.api_key)
        # Strip models/ prefix if present to conform to new SDK standards
        self.model_name = model_name.replace("models/", "")

    async def classify_query(self, query: str) -> str:
        """
        Classifies the incoming user query.
        Returns:
            "DOCUMENT_QUERY" if the user is asking about uploaded document files.
            "GENERAL_CHAT" if the user is asking general questions or conversing.
        """
        prompt = f"""You are an intelligent routing agent for a document assistant.
Your task is to analyze the user's query and classify it into one of two routing paths:

1. DOCUMENT_QUERY: Use this path if the query asks about, refers to, or requests information from an uploaded document, file, book, report, or specific sections (e.g. "summarize the report", "what does this doc say about revenue", "explain page 5").
2. GENERAL_CHAT: Use this path if the query is a general knowledge question, greetings, standard chatbot conversation, coding questions, math, or explanation of general concepts not requiring context from uploaded documents (e.g. "what is FastAPI?", "how does photosynthesis work?", "hello!", "tell me a joke").

Respond with exactly one of these two strings (no quotes, no explanation, no formatting):
DOCUMENT_QUERY
GENERAL_CHAT

User Query: "{query}"

Classification:"""

        try:
            from app.core.retry import retry_with_backoff
            # Generate classification response using zero-shot prompt under temperature 0.0 with retry backoff
            response = retry_with_backoff(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0)
            )
            classification = response.text.strip().upper()
            
            # Simple substring check to guarantee valid category returns
            if "DOCUMENT_QUERY" in classification:
                return "DOCUMENT_QUERY"
            return "GENERAL_CHAT"
            
        except Exception as e:
            # Fallback to DOCUMENT_QUERY as a safe default under error conditions
            print(f"Routing classification failed, falling back to DOCUMENT_QUERY. Error: {e}")
            return "DOCUMENT_QUERY"

    async def condense_query(self, query: str, history: list) -> str:
        """
        Condenses a user follow-up query and the recent conversation history into a standalone query.
        """
        if not history:
            return query
            
        # Format the last 4 messages of history to keep context clean
        recent_history = history[-4:]
        history_str = ""
        for msg in recent_history:
            role_label = "User" if getattr(msg, "role", "user") == "user" else "Assistant"
            text_val = getattr(msg, "text", "")
            history_str += f"{role_label}: {text_val}\n"
            
        prompt = f"""Given the following conversation history and a follow-up question, rephrase the follow-up question to be a standalone question that can be understood without the conversation history. Do not change the core subject or intent of the follow-up question.
        
Conversation History:
{history_str}

Follow-up Question: {query}

Standalone Question (Respond with ONLY the standalone question, no explanation, no formatting):"""

        try:
            from app.core.retry import retry_with_backoff
            response = retry_with_backoff(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0)
            )
            condensed = response.text.strip()
            if condensed:
                return condensed
            return query
        except Exception as e:
            print(f"Query condensation failed: {e}. Using raw query.")
            return query

