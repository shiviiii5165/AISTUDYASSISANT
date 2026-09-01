from fastapi.testclient import TestClient
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from app.main import app
from app.core.dependencies import get_current_user
class MockUser:
    def __init__(self, user_id):
        self.id = user_id

mock_user = MockUser(user_id="6ca14719-b196-427f-8c3d-fc42a81d7e8b")

# Override the auth dependency
app.dependency_overrides[get_current_user] = lambda: mock_user

client = TestClient(app)

payload = {
    "mode": "student",
    "source_type": "topic",
    "source_ids": [],
    "topic": "Python Programming",
    "config": {
        "question_count": 2,
        "difficulty": "easy",
        "types": ["mcq"],
        "language": "english",
        "shuffle_questions": False,
        "shuffle_options": False,
        "adaptive": False
    }
}

response = client.post("/api/quiz/quizzes", json=payload)
print(f"Status Code: {response.status_code}")
import json
print(json.dumps(response.json(), indent=2))
