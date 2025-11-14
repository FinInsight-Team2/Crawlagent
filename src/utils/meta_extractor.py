"""
Meta Tag & JSON-LD Extraction Utility

XPath 기반 Meta 태그 추출 + JSON-LD Schema 파싱
CSS 셀렉터의 <head> 접근 불가 문제 해결

작성일: 2025-11-14
참고: 최신 리서치 기반 Best Practice
"""

import json
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from loguru import logger


def extract_json_ld(html: str) -> Optional[Dict[str, Any]]:
    """
    JSON-LD Schema.org 데이터 추출 (NewsArticle 우선)

    Args:
        html: HTML 문자열

    Returns:
        NewsArticle 스키마 딕셔너리 또는 None

    Examples:
        >>> html = '<script type="application/ld+json">{"@type": "NewsArticle", ...}</script>'
        >>> result = extract_json_ld(html)
        >>> print(result['headline'])
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        scripts = soup.find_all('script', type='application/ld+json')

        for script in scripts:
            try:
                data = json.loads(script.string)

                # @graph 형식 처리 (배열로 감싸진 경우)
                if isinstance(data, dict) and '@graph' in data:
                    items = data['@graph']
                elif isinstance(data, list):
                    items = data
                else:
                    items = [data]

                # NewsArticle 찾기
                for item in items:
                    if isinstance(item, dict) and item.get('@type') == 'NewsArticle':
                        logger.info(f"[Meta Extractor] ✅ JSON-LD NewsArticle found")
                        return {
                            'title': item.get('headline'),
                            'description': item.get('description'),
                            'author': _extract_author(item),
                            'date': item.get('datePublished') or item.get('dateCreated'),
                            'modified': item.get('dateModified'),
                            'image': _extract_image(item),
                            'url': item.get('url'),
                            'publisher': _extract_publisher(item),
                            'section': item.get('articleSection'),
                            'source': 'json-ld'
                        }
            except json.JSONDecodeError:
                continue

        logger.debug(f"[Meta Extractor] No NewsArticle JSON-LD found")
        return None

    except Exception as e:
        logger.error(f"[Meta Extractor] JSON-LD extraction error: {e}")
        return None


def extract_meta_tags(html: str) -> Dict[str, Optional[str]]:
    """
    XPath 기반 Meta 태그 추출 (BeautifulSoup 사용)

    CSS 셀렉터는 <head> 접근 불가하므로 BeautifulSoup 사용

    Args:
        html: HTML 문자열

    Returns:
        Meta 태그 딕셔너리

    Priority:
        1. Open Graph (og:*)
        2. Twitter Cards (twitter:*)
        3. Standard meta (name="description" 등)
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        meta = {}

        # Open Graph (우선순위 1)
        og_title = soup.find('meta', property='og:title')
        og_desc = soup.find('meta', property='og:description')
        og_image = soup.find('meta', property='og:image')
        og_url = soup.find('meta', property='og:url')
        og_type = soup.find('meta', property='og:type')
        og_site_name = soup.find('meta', property='og:site_name')

        # Twitter Cards (우선순위 2)
        tw_title = soup.find('meta', attrs={'name': 'twitter:title'})
        tw_desc = soup.find('meta', attrs={'name': 'twitter:description'})
        tw_image = soup.find('meta', attrs={'name': 'twitter:image'})

        # Standard meta (우선순위 3)
        std_desc = soup.find('meta', attrs={'name': 'description'})
        std_keywords = soup.find('meta', attrs={'name': 'keywords'})
        std_author = soup.find('meta', attrs={'name': 'author'})

        # Article meta (우선순위 4)
        article_published = soup.find('meta', property='article:published_time')
        article_modified = soup.find('meta', property='article:modified_time')
        article_author = soup.find('meta', property='article:author')
        article_section = soup.find('meta', property='article:section')

        # 우선순위에 따라 값 설정
        meta['title'] = _get_content(og_title) or _get_content(tw_title)
        meta['description'] = _get_content(og_desc) or _get_content(tw_desc) or _get_content(std_desc)
        meta['image'] = _get_content(og_image) or _get_content(tw_image)
        meta['url'] = _get_content(og_url)
        meta['type'] = _get_content(og_type)
        meta['site_name'] = _get_content(og_site_name)
        meta['keywords'] = _get_content(std_keywords)
        meta['author'] = _get_content(article_author) or _get_content(std_author)
        meta['date'] = _get_content(article_published)
        meta['modified'] = _get_content(article_modified)
        meta['section'] = _get_content(article_section)
        meta['source'] = 'meta-tags'

        logger.info(f"[Meta Extractor] ✅ Meta tags extracted: {sum(1 for v in meta.values() if v)}/12 fields")
        return meta

    except Exception as e:
        logger.error(f"[Meta Extractor] Meta tag extraction error: {e}")
        return {'source': 'meta-tags'}


def extract_metadata_smart(html: str) -> Dict[str, Optional[str]]:
    """
    Smart 메타데이터 추출: JSON-LD → Meta 태그 우선순위

    Args:
        html: HTML 문자열

    Returns:
        병합된 메타데이터 딕셔너리

    Strategy:
        1. JSON-LD 시도 (가장 구조화됨)
        2. Meta 태그 폴백
        3. 둘 다 실패 시 None 값 반환
    """
    # 1차: JSON-LD
    json_ld_data = extract_json_ld(html)
    if json_ld_data and json_ld_data.get('title'):
        logger.info(f"[Meta Extractor] 📦 Using JSON-LD (primary)")
        return json_ld_data

    # 2차: Meta 태그
    meta_data = extract_meta_tags(html)
    if meta_data.get('title'):
        logger.info(f"[Meta Extractor] 🏷️ Using Meta tags (fallback)")
        return meta_data

    # 3차: 병합 시도 (JSON-LD + Meta 조합)
    if json_ld_data or meta_data:
        merged = {}
        for key in ['title', 'description', 'author', 'date', 'modified', 'image', 'url', 'section']:
            merged[key] = (json_ld_data or {}).get(key) or (meta_data or {}).get(key)

        merged['source'] = 'merged'
        logger.info(f"[Meta Extractor] 🔀 Using merged data")
        return merged

    logger.warning(f"[Meta Extractor] ⚠️ No metadata found")
    return {'source': 'none'}


# ============================================================================
# Helper Functions
# ============================================================================

def _get_content(tag) -> Optional[str]:
    """Meta 태그에서 content 속성 추출"""
    if tag:
        return tag.get('content', '').strip() or None
    return None


def _extract_author(item: dict) -> Optional[str]:
    """JSON-LD author 추출 (다양한 형식 처리)"""
    author = item.get('author')
    if isinstance(author, dict):
        return author.get('name')
    elif isinstance(author, list):
        # 복수 저자 시 첫 번째 저자
        return author[0].get('name') if isinstance(author[0], dict) else str(author[0])
    elif isinstance(author, str):
        return author
    return None


def _extract_image(item: dict) -> Optional[str]:
    """JSON-LD image 추출 (다양한 형식 처리)"""
    image = item.get('image')
    if isinstance(image, dict):
        return image.get('url')
    elif isinstance(image, list):
        # 복수 이미지 시 첫 번째 이미지
        return image[0].get('url') if isinstance(image[0], dict) else str(image[0])
    elif isinstance(image, str):
        return image
    return None


def _extract_publisher(item: dict) -> Optional[str]:
    """JSON-LD publisher 추출"""
    publisher = item.get('publisher')
    if isinstance(publisher, dict):
        return publisher.get('name')
    elif isinstance(publisher, str):
        return publisher
    return None


# ============================================================================
# Validation
# ============================================================================

def validate_metadata(data: Dict[str, Any]) -> bool:
    """
    메타데이터 유효성 검사

    최소 요구사항: title 또는 description 존재

    Args:
        data: 메타데이터 딕셔너리

    Returns:
        유효성 여부
    """
    if not data or data.get('source') == 'none':
        return False

    # 최소 title 또는 description 필요
    has_title = bool(data.get('title'))
    has_desc = bool(data.get('description'))

    return has_title or has_desc


def get_metadata_quality_score(data: Dict[str, Any]) -> float:
    """
    메타데이터 품질 점수 계산 (0.0 - 1.0)

    점수 기준:
    - title: 0.3
    - description: 0.2
    - author: 0.1
    - date: 0.2
    - image: 0.1
    - source (json-ld): +0.1 보너스

    Args:
        data: 메타데이터 딕셔너리

    Returns:
        품질 점수 (0.0 - 1.0)
    """
    score = 0.0

    if data.get('title'):
        score += 0.3
    if data.get('description'):
        score += 0.2
    if data.get('author'):
        score += 0.1
    if data.get('date'):
        score += 0.2
    if data.get('image'):
        score += 0.1

    # JSON-LD 보너스 (더 신뢰할 수 있는 구조)
    if data.get('source') == 'json-ld':
        score += 0.1

    return min(score, 1.0)
