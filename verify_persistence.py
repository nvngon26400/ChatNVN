import sys
import os
import time

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from mock_project.chatbot import CustomerSupportChatbot

def test_persistence():
    session_id = "test-session-persistence"
    
    print(f"--- Session ID: {session_id} ---")
    
    # Instance 1
    print("\n[Instance 1] Initializing...")
    bot1 = CustomerSupportChatbot()
    q1 = "My name is Alice."
    print(f"User: {q1}")
    a1 = bot1.ask(q1, session_id=session_id)
    print(f"Bot: {a1}")
    
    # Simulate restart / new instance
    print("\n[Instance 2] Re-initializing (simulating restart)...")
    bot2 = CustomerSupportChatbot()
    q2 = "What is my name?"
    print(f"User: {q2}")
    a2 = bot2.ask(q2, session_id=session_id)
    print(f"Bot: {a2}")
    
    if "Alice" in a2:
        print("\nSUCCESS: Bot remembered the name!")
    else:
        print("\nFAILURE: Bot did not remember the name.")

if __name__ == "__main__":
    try:
        test_persistence()
    except Exception as e:
        print("Error:")
        print(e)
        import traceback
        traceback.print_exc()
