"""
Quick script to fetch HTML from a URL for LangGraph Studio testing (UC2 HITL).
Usage: python scripts/fetch_html_for_studio.py <URL>
"""
import sys
import requests
import json

def fetch_html_for_studio(url: str) -> None:
    """Fetch HTML and output JSON format for LangGraph Studio UC2."""
    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()

        # UC2 HITLState에 맞는 입력 형식
        studio_input = {
            "url": url,
            "site_name": "yonhap",  # 연합뉴스
            "html_content": response.text,
            "gpt_proposal": None,
            "gemini_validation": None,
            "consensus_reached": False,
            "retry_count": 0,
            "final_selectors": None,
            "error_message": None,
            "next_action": None
        }

        # Print as formatted JSON
        print(json.dumps(studio_input, indent=2, ensure_ascii=False))

        # Also save to file
        output_file = "studio_input.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(studio_input, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Saved to {output_file}", file=sys.stderr)
        print(f"✓ HTML length: {len(response.text)} characters", file=sys.stderr)
        print("\nCopy the JSON above and paste it into LangGraph Studio's input field.", file=sys.stderr)

    except Exception as e:
        print(f"Error fetching URL: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/fetch_html_for_studio.py <URL>")
        print("Example: python scripts/fetch_html_for_studio.py https://example.com/article")
        sys.exit(1)

    url = sys.argv[1]
    fetch_html_for_studio(url)
