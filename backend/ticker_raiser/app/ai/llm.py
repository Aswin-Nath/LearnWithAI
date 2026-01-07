import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
load_dotenv()
GROQ_KEY = os.getenv("GROQ_API_KEY")
llm = ChatGroq(api_key=GROQ_KEY, model_name="llama-3.1-8b-instant", temperature=0)
