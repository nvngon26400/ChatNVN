import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from mock_project.chatbot import CustomerSupportChatbot

try:
    print("Initializing Chatbot...")
    bot = CustomerSupportChatbot()
    print("Chatbot initialized. Asking question...")
    answer = bot.ask("Hello")
    print("Answer:", answer)
except Exception as e:
    print("Error occurred:")
    print(e)
    import traceback
    traceback.print_exc()
