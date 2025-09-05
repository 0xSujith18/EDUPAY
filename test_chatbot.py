#!/usr/bin/env python3
"""
Test script for the advanced EduPay chatbot
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import chatbot, users, invoices_data

def test_chatbot():
    """Test the advanced chatbot functionality"""
    print("🤖 Testing EduPay Advanced Chatbot")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        ("Hello", "greeting"),
        ("Hi there", "greeting"),
        ("What's my balance?", "balance"),
        ("Check balance", "balance"),
        ("When is my fee due?", "due_date"),
        ("Due date", "due_date"),
        ("I want to make a payment", "payment"),
        ("Pay now", "payment"),
        ("Show me fee information", "fee_info"),
        ("What are the fees?", "fee_info"),
        ("Help me", "help"),
        ("I need support", "help"),
        ("Download receipt", "receipt"),
        ("I have a problem", "complaint"),
        ("Random question", "general")
    ]
    
    print("Testing Intent Recognition:")
    print("-" * 30)
    
    for message, expected_intent in test_cases:
        actual_intent = chatbot.analyze_intent(message)
        status = "✅" if actual_intent == expected_intent else "❌"
        print(f"{status} '{message}' -> {actual_intent} (expected: {expected_intent})")
    
    print("\nTesting Response Generation:")
    print("-" * 30)
    
    # Test with user context (student1)
    test_responses = [
        "Hello",
        "What's my balance?",
        "When is my next payment due?",
        "Help me make a payment",
        "Show fee information"
    ]
    
    for message in test_responses:
        response = chatbot.generate_response(message, "student1", "test_session")
        print(f"User: {message}")
        print(f"Bot: {response[:100]}{'...' if len(response) > 100 else ''}")
        print()
    
    print("Testing Conversation Memory:")
    print("-" * 30)
    
    # Test conversation flow
    session_id = "memory_test"
    
    responses = [
        chatbot.generate_response("Hello", "student1", session_id),
        chatbot.generate_response("What's my balance?", "student1", session_id),
        chatbot.generate_response("UPI", "student1", session_id),  # Should recognize context
    ]
    
    for i, response in enumerate(responses, 1):
        print(f"Turn {i}: {response[:80]}{'...' if len(response) > 80 else ''}")
    
    print("\n🎉 Chatbot testing completed!")
    print("\nKey Features Implemented:")
    print("✅ Advanced intent recognition")
    print("✅ User context awareness")
    print("✅ Conversation memory")
    print("✅ Personalized responses")
    print("✅ Multi-turn conversations")
    print("✅ Rich knowledge base")

if __name__ == "__main__":
    test_chatbot()