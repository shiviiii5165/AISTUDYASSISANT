"""Quick test for the JSON repair utility."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SUPABASE_URL", "x")
os.environ.setdefault("SUPABASE_KEY", "x")
os.environ.setdefault("SUPABASE_JWT_SECRET", "x")
os.environ.setdefault("GEMINI_API_KEY", "x")
os.environ.setdefault("GROQ_API_KEY", "x")
os.environ.setdefault("CASHFREE_APP_ID", "x")
os.environ.setdefault("CASHFREE_SECRET_KEY", "x")

from app.services.llm_service import safe_json_loads

tests = [
    ("Normal JSON", '{"a": 1}'),
    ("Markdown fenced", '```json\n{"a": 1}\n```'),
    ("Trailing comma obj", '{"a": 1, "b": 2,}'),
    ("Trailing comma array", '{"items": [1, 2, 3,]}'),
    ("Preamble text", 'Here is the JSON output:\n{"ok": true}'),
    ("Double fenced", '```\n{"x": [1,2]}\n```'),
]

all_pass = True
for name, input_str in tests:
    try:
        result = safe_json_loads(input_str)
        print(f"  [PASS] {name}: {result}")
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        all_pass = False

if all_pass:
    print("\nAll tests passed!")
else:
    print("\nSome tests FAILED.")
    sys.exit(1)
