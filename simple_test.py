"""Simple test of key modules"""
import sys
import os
sys.path.append('ml_modules')

print("Testing imports...")

try:
    from ml_modules.spam_email.predict import SpamDetector
    print("✅ Spam Email: OK")
except Exception as e:
    print(f"❌ Spam Email: {e}")

try:
    from ml_modules.chatbot import MDFDPBot
    print("✅ Chatbot: OK")
except Exception as e:
    print(f"❌ Chatbot: {e}")

print("\nChecking CSS...")
with open('static/style.css', 'r', encoding='utf-8') as f:
    content = f.read()
    open_b = content.count('{')
    close_b = content.count('}')
    print(f"CSS Braces: {open_b} open, {close_b} close - {'✅ OK' if open_b == close_b else '❌ UNBALANCED'}")

print("\nDone!")
