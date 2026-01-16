"""Test the problematic chemistry query"""
import os
from dotenv import load_dotenv
from chatbot import FacultyPulseChatbot

load_dotenv()

chatbot = FacultyPulseChatbot(api_key=os.environ.get('ANTHROPIC_API_KEY'))

print("="*80)
print("TESTING: 'who would be the best for a talk in chemistry'")
print("="*80)

try:
    result = chatbot.chat(
        user_query="who would be the best for a talk in chemistry",
        n_results=5
    )

    print(f"\nResponse received:")
    print(f"  Length: {len(result['response'])} characters")
    print(f"  Num results: {result['num_results']}")
    print(f"\nResponse content:")
    print(result['response'])

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
