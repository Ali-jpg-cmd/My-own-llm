#!/usr/bin/env python3
"""
Test script for the AI API
"""

import requests
import json
import time
from typing import Dict, Any

class LLMAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_key = None
        self.session = requests.Session()
    
    def test_health(self) -> bool:
        """Test health endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            print(f"Health check: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {response.json()}")
                return True
            return False
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
    
    def register_user(self, email: str, username: str, password: str) -> bool:
        """Register a new user"""
        try:
            data = {
                "email": email,
                "username": username,
                "password": password
            }
            
            response = self.session.post(f"{self.base_url}/auth/register", json=data)
            print(f"Register: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                self.api_key = result.get("api_key")
                print(f"API Key: {self.api_key[:20]}...")
                return True
            else:
                print(f"Register failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"Register failed: {e}")
            return False
    
    def login_user(self, email: str, password: str) -> bool:
        """Login user"""
        try:
            data = {
                "email": email,
                "password": password
            }
            
            response = self.session.post(f"{self.base_url}/auth/login", json=data)
            print(f"Login: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                self.api_key = result.get("api_key")
                print(f"API Key: {self.api_key[:20]}...")
                return True
            else:
                print(f"Login failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"Login failed: {e}")
            return False
    
    def generate_text(self, prompt: str, max_tokens: int = 100) -> Dict[str, Any]:
        """Generate text using the API"""
        if not self.api_key:
            print("No API key available. Please register or login first.")
            return {}
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/generate",
                headers=headers,
                json=data
            )
            
            print(f"Generate: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Generated text: {result.get('text', '')[:100]}...")
                print(f"Usage: {result.get('usage', {})}")
                return result
            else:
                print(f"Generation failed: {response.text}")
                return {}
                
        except Exception as e:
            print(f"Generation failed: {e}")
            return {}
    
    def get_models(self) -> list:
        """Get available models"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/models")
            print(f"Get models: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Available models: {result.get('models', [])}")
                return result.get('models', [])
            else:
                print(f"Get models failed: {response.text}")
                return []
                
        except Exception as e:
            print(f"Get models failed: {e}")
            return []
    
    def get_usage(self) -> Dict[str, Any]:
        """Get usage statistics"""
        if not self.api_key:
            print("No API key available. Please register or login first.")
            return {}
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = self.session.get(
                f"{self.base_url}/api/v1/usage",
                headers=headers
            )
            
            print(f"Get usage: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Usage stats: {result}")
                return result
            else:
                print(f"Get usage failed: {response.text}")
                return {}
                
        except Exception as e:
            print(f"Get usage failed: {e}")
            return {}
    
    def test_rate_limiting(self) -> bool:
        """Test rate limiting by making multiple requests"""
        if not self.api_key:
            print("No API key available. Please register or login first.")
            return False
        
        print("Testing rate limiting...")
        
        for i in range(5):
            result = self.generate_text(f"Test request {i+1}", max_tokens=10)
            if not result:
                print(f"Rate limit hit at request {i+1}")
                return True
            time.sleep(0.1)  # Small delay between requests
        
        print("Rate limiting test completed")
        return True
    
    def run_full_test(self):
        """Run a complete test suite"""
        print("=" * 50)
        print("Starting AI API Test Suite")
        print("=" * 50)
        
        # Test 1: Health check
        print("\n1. Testing health endpoint...")
        if not self.test_health():
            print("Health check failed. Is the API running?")
            return
        
        # Test 2: Get available models
        print("\n2. Testing models endpoint...")
        self.get_models()
        
        # Test 3: Register new user
        print("\n3. Testing user registration...")
        email = f"test_{int(time.time())}@example.com"
        username = f"testuser_{int(time.time())}"
        password = "testpassword123"
        
        if not self.register_user(email, username, password):
            print("Registration failed. Trying login...")
            if not self.login_user(email, password):
                print("Both registration and login failed.")
                return
        
        # Test 4: Generate text
        print("\n4. Testing text generation...")
        test_prompts = [
            "Explain quantum computing in one sentence.",
            "Write a haiku about artificial intelligence.",
            "What is the capital of France?"
        ]
        
        for prompt in test_prompts:
            print(f"\nPrompt: {prompt}")
            result = self.generate_text(prompt, max_tokens=50)
            if result:
                print(f"Response: {result.get('text', '')}")
        
        # Test 5: Get usage statistics
        print("\n5. Testing usage statistics...")
        self.get_usage()
        
        # Test 6: Rate limiting
        print("\n6. Testing rate limiting...")
        self.test_rate_limiting()
        
        print("\n" + "=" * 50)
        print("Test suite completed!")
        print("=" * 50)


def main():
    """Main function"""
    # Create tester instance
    tester = LLMAPITester()
    
    # Run full test suite
    tester.run_full_test()


if __name__ == "__main__":
    main()
