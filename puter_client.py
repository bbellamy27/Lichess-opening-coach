import requests
import json

class PuterClient:
    """
    Client for interacting with the free Puter Llama API.
    """
    
    def __init__(self):
        self.url = "https://api.puter.com/v2/ai/chat/completions"
        self.model = "meta-llama/llama-3.1-8b-instruct"
    client = PuterClient()
    print("PuterClient initialized.")
