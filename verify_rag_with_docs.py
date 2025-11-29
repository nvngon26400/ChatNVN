import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from mock_project.chatbot import CustomerSupportChatbot

def test_hybrid_rag_with_docs():
    print("--- Testing Hybrid RAG (with docs present) ---")
    
    # Ensure docs exist
    docs_dir = Path("data/docs")
    docs_dir.mkdir(parents=True, exist_ok=True)
    dummy_file = docs_dir / "dummy.txt"
    if not dummy_file.exists():
        with open(dummy_file, "w", encoding="utf-8") as f:
            f.write("Đây là tài liệu nội bộ về chính sách hoàn tiền. Không có thông tin về địa lý.")
    
    bot = CustomerSupportChatbot()
    
    # Check if docs_exist is True
    print(f"Docs exist: {bot.settings.docs_exist}")
    
    # 1. Ask a general question (should be answered by OpenAI knowledge despite docs existing)
    question = "Thủ đô của nước Pháp là gì?"
    print(f"Question: {question}")
    answer = bot.ask(question)
    print(f"Answer: {answer}")
    
    if "Paris" in answer:
        print("SUCCESS: Bot answered general knowledge question even with docs present.")
    else:
        print("FAILURE: Bot failed to answer general knowledge question when docs are present.")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    test_hybrid_rag_with_docs()
