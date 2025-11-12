"""
데모용 URL 검증 및 준비 스크립트
Created: 2025-11-12

목적: 데모에서 사용할 URL이 실제로 접근 가능한지 검증
"""

import requests
from loguru import logger

DEMO_URLS = {
    "cnn": [
        "https://www.cnn.com/2024/11/12/business/apple-warning-iphone-users/index.html",
        "https://www.cnn.com/2024/11/11/tech/ai-chatbot-teenagers/index.html",
        "https://edition.cnn.com/2024/11/12/business/markets-now/index.html"
    ],
    "chosun": [
        "https://www.chosun.com/economy/economy_general/2024/11/12/",
        "https://www.chosun.com/politics/politics_general/2024/11/12/"
    ],
    "reuters": [
        "https://www.reuters.com/technology/",
        "https://www.reuters.com/business/"
    ]
}


def check_url(url: str, timeout: int = 10) -> dict:
    """
    URL 접근 가능 여부 확인
    """
    try:
        response = requests.get(url, timeout=timeout, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        return {
            "url": url,
            "status": response.status_code,
            "accessible": response.status_code == 200,
            "size": len(response.text),
            "error": None
        }
    except Exception as e:
        return {
            "url": url,
            "status": None,
            "accessible": False,
            "size": 0,
            "error": str(e)
        }


def main():
    print("\n" + "="*80)
    print("🔍 데모 URL 검증")
    print("="*80 + "\n")

    valid_urls = {}

    for site_name, urls in DEMO_URLS.items():
        print(f"\n📍 {site_name.upper()}:")
        valid_urls[site_name] = []

        for url in urls:
            result = check_url(url)

            if result["accessible"]:
                logger.success(f"  ✅ {url}")
                logger.info(f"     Size: {result['size']:,} bytes")
                valid_urls[site_name].append(url)
            else:
                logger.error(f"  ❌ {url}")
                logger.error(f"     Error: {result['error'] or result['status']}")

    # 최종 추천 URL
    print("\n" + "="*80)
    print("📝 데모 추천 URL")
    print("="*80 + "\n")

    for site_name, urls in valid_urls.items():
        if urls:
            print(f"{site_name.upper()}: {urls[0]}")
        else:
            print(f"{site_name.upper()}: ⚠️  No valid URL found")

    print("\n" + "="*80)
    print("💡 Tip: 데모 직전에 다시 실행해서 URL 유효성 확인하세요!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
