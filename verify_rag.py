import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from mock_project.chatbot import CustomerSupportChatbot

def test_hybrid_rag():
    print("--- Testing Hybrid RAG ---")
    bot = CustomerSupportChatbot()
    
    # 1. Ask a general question (should be answered by OpenAI knowledge)
    question = "Thủ đô của nước Pháp là gì?"
    print(f"Question: {question}")
    answer = bot.ask(question)
    print(f"Answer: {answer}")
    
    if "Paris" in answer:
        print("SUCCESS: Bot answered general knowledge question.")
    else:
        print("FAILURE: Bot failed to answer general knowledge question.")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    test_hybrid_rag()
