"""
CrawlAgent - UC1 Quality Gate Unit Tests
Created: 2025-11-15

Tests for LLM-based content quality validation.
Target Coverage: 80%+
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from src.agents.uc1_quality_gate import (
    validate_quality,
    get_news_validation_prompt,
    get_openai_client
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response for successful validation"""
    def _create_response(decision="pass", confidence=95, category_match=True):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "decision": decision,
            "confidence": confidence,
            "category_match": category_match,
            "content_type_detected": "news",
            "body_complete": True,
            "date_present": True,
            "reasoning": "Test reasoning"
        })
        return mock_response
    return _create_response


@pytest.fixture
def sample_news_article():
    """Sample news article data for testing"""
    return {
        "content_type": "news",
        "title": "삼성전자, 반도체 매출 30% 증가 발표",
        "body": """삼성전자가 13일 서울 본사에서 기자회견을 열고 3분기 반도체 매출이 전년 대비 30% 증가했다고 밝혔다.
        이번 실적은 AI 반도체 수요 증가와 메모리 가격 상승에 힘입은 것으로 분석된다.
        업계 전문가들은 4분기에도 이러한 흐름이 지속될 것으로 전망하고 있다. """ * 5,  # 500자 이상
        "date": "2025-11-15",
        "category": "economy",
        "category_kr": "경제",
        "url": "https://www.example.com/news/economy/123"
    }


# ============================================================================
# Test: validate_quality() - Success Cases
# ============================================================================

@patch('src.agents.uc1_quality_gate.get_openai_client')
def test_validate_quality_pass(mock_get_client, mock_openai_response, sample_news_article):
    """완벽한 뉴스 기사는 pass 결정"""
    # Arrange
    mock_client = Mock()
    mock_client.chat.completions.create.return_value = mock_openai_response(
        decision="pass",
        confidence=95,
        category_match=True
    )
    mock_get_client.return_value = mock_client

    # Act
    result = validate_quality(**sample_news_article)

    # Assert
    assert result["decision"] == "pass"
    assert result["confidence"] == 95
    assert result["category_match"] is True
    assert result["content_type_detected"] == "news"
    assert result["body_complete"] is True
    assert result["date_present"] is True

    # Verify OpenAI was called with correct parameters
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["temperature"] == 0.1
    assert call_kwargs["response_format"] == {"type": "json_object"}


@patch('src.agents.uc1_quality_gate.get_openai_client')
def test_validate_quality_reject_ad(mock_get_client, mock_openai_response):
    """광고성 콘텐츠는 reject 결정"""
    # Arrange
    mock_client = Mock()
    mock_client.chat.completions.create.return_value = mock_openai_response(
        decision="reject",
        confidence=98,
        category_match=False
    )
    mock_get_client.return_value = mock_client

    ad_article = {
        "content_type": "news",
        "title": "특가 세일! 지금 바로 구매하세요",
        "body": "이번 주말 특별 할인 이벤트를 진행합니다. " * 50,
        "date": "2025-11-15",
        "category": "economy",
        "category_kr": "경제",
        "url": "https://www.example.com/ad/123"
    }

    # Act
    result = validate_quality(**ad_article)

    # Assert
    assert result["decision"] == "reject"
    assert result["confidence"] == 98


@patch('src.agents.uc1_quality_gate.get_openai_client')
def test_validate_quality_uncertain_category_mismatch(mock_get_client, mock_openai_response):
    """카테고리 불일치 시 uncertain 반환"""
    # Arrange
    mock_client = Mock()
    mock_client.chat.completions.create.return_value = mock_openai_response(
        decision="uncertain",
        confidence=75,
        category_match=False
    )
    mock_get_client.return_value = mock_client

    mismatched_article = {
        "content_type": "news",
        "title": "BTS 신곡 발매, 빌보드 1위 기록",
        "body": "방탄소년단이 새로운 앨범을 발표했다. " * 50,
        "date": "2025-11-15",
        "category": "economy",  # 실제로는 엔터테인먼트
        "category_kr": "경제",
        "url": "https://www.example.com/news/123"
    }

    # Act
    result = validate_quality(**mismatched_article)

    # Assert
    assert result["decision"] == "uncertain"
    assert result["confidence"] == 75
    assert result["category_match"] is False


# ============================================================================
# Test: validate_quality() - Error Handling
# ============================================================================

@patch('src.agents.uc1_quality_gate.get_openai_client')
def test_validate_quality_json_parsing_error(mock_get_client, sample_news_article):
    """JSON 파싱 실패 시 uncertain 반환"""
    # Arrange
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Invalid JSON {this is not valid"
    mock_client.chat.completions.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    # Act
    result = validate_quality(**sample_news_article)

    # Assert
    assert result["decision"] == "uncertain"
    assert result["confidence"] == 50
    assert result["content_type_detected"] == "unknown"
    assert "JSON 파싱 실패" in result["reasoning"]


@patch('src.agents.uc1_quality_gate.get_openai_client')
@patch('src.agents.uc1_quality_gate.time.sleep')  # Mock sleep to speed up tests
def test_validate_quality_rate_limit_retry(mock_sleep, mock_get_client, mock_openai_response, sample_news_article):
    """Rate Limit 발생 시 재시도 후 성공"""
    # Arrange
    mock_client = Mock()

    # First call: Rate limit error
    # Second call: Success
    mock_client.chat.completions.create.side_effect = [
        Exception("429 rate_limit exceeded"),
        mock_openai_response(decision="pass", confidence=95)
    ]
    mock_get_client.return_value = mock_client

    # Act
    result = validate_quality(**sample_news_article)

    # Assert
    assert result["decision"] == "pass"
    assert result["confidence"] == 95
    assert mock_client.chat.completions.create.call_count == 2
    assert mock_sleep.call_count == 1  # Slept once before retry


@patch('src.agents.uc1_quality_gate.get_openai_client')
@patch('src.agents.uc1_quality_gate.time.sleep')
def test_validate_quality_rate_limit_all_retries_failed(mock_sleep, mock_get_client, sample_news_article):
    """모든 재시도 실패 시 uncertain 반환"""
    # Arrange
    mock_client = Mock()
    mock_client.chat.completions.create.side_effect = Exception("429 rate_limit exceeded")
    mock_get_client.return_value = mock_client

    # Act
    result = validate_quality(**sample_news_article)

    # Assert
    assert result["decision"] == "uncertain"
    assert result["confidence"] == 50
    assert "Rate Limit" in result["reasoning"]
    assert mock_client.chat.completions.create.call_count == 3  # max_retries = 3


@patch('src.agents.uc1_quality_gate.get_openai_client')
def test_validate_quality_unexpected_exception(mock_get_client, sample_news_article):
    """예상치 못한 예외 발생 시 uncertain 반환"""
    # Arrange
    mock_client = Mock()
    mock_client.chat.completions.create.side_effect = Exception("Unexpected error")
    mock_get_client.return_value = mock_client

    # Act
    result = validate_quality(**sample_news_article)

    # Assert
    assert result["decision"] == "uncertain"
    assert result["confidence"] == 50
    assert "예외 발생" in result["reasoning"]


# ============================================================================
# Test: validate_quality() - Content Types
# ============================================================================

@patch('src.agents.uc1_quality_gate.get_openai_client')
def test_validate_quality_blog_content(mock_get_client, mock_openai_response):
    """블로그 콘텐츠 검증"""
    # Arrange
    mock_client = Mock()
    mock_client.chat.completions.create.return_value = mock_openai_response()
    mock_get_client.return_value = mock_client

    blog_article = {
        "content_type": "blog",
        "title": "재테크 전략 5가지",
        "body": "재테크를 위한 구체적인 전략들을 소개합니다. " * 50,
        "date": None,
        "category": "finance",
        "category_kr": "금융",
        "url": "https://blog.example.com/123"
    }

    # Act
    result = validate_quality(**blog_article)

    # Assert
    assert result is not None
    # Verify blog validation prompt was used
    call_args = mock_client.chat.completions.create.call_args
    assert "블로그" in call_args[1]["messages"][1]["content"]


@patch('src.agents.uc1_quality_gate.get_openai_client')
def test_validate_quality_community_content(mock_get_client, mock_openai_response):
    """커뮤니티 콘텐츠 검증"""
    # Arrange
    mock_client = Mock()
    mock_client.chat.completions.create.return_value = mock_openai_response()
    mock_get_client.return_value = mock_client

    community_post = {
        "content_type": "community",
        "title": "요즘 주식 시장 어떻게 보시나요?",
        "body": "개인적으로는 조정이 올 것 같은데요. " * 50,
        "date": None,
        "category": None,
        "category_kr": None,
        "url": "https://community.example.com/123"
    }

    # Act
    result = validate_quality(**community_post)

    # Assert
    assert result is not None
    # Verify community validation prompt was used
    call_args = mock_client.chat.completions.create.call_args
    assert "커뮤니티" in call_args[1]["messages"][1]["content"]


def test_validate_quality_invalid_content_type():
    """잘못된 content_type은 ValueError 발생"""
    with pytest.raises(ValueError, match="Unknown content_type"):
        validate_quality(
            content_type="invalid",
            title="Test",
            body="Test body",
            date="2025-11-15",
            category="economy",
            category_kr="경제",
            url="https://example.com"
        )


# ============================================================================
# Test: get_news_validation_prompt()
# ============================================================================

def test_get_news_validation_prompt_contains_all_fields():
    """뉴스 검증 프롬프트에 모든 필수 필드 포함"""
    prompt = get_news_validation_prompt(
        title="테스트 제목",
        body_preview="테스트 본문",
        date="2025-11-15",
        category="economy",
        category_kr="경제",
        url="https://example.com/news/123"
    )

    # Assert all fields are in prompt
    assert "테스트 제목" in prompt
    assert "테스트 본문" in prompt
    assert "2025-11-15" in prompt
    assert "경제" in prompt
    assert "economy" in prompt
    assert "https://example.com/news/123" in prompt

    # Assert validation criteria are mentioned
    assert "카테고리 적합성" in prompt
    assert "콘텐츠 유형" in prompt
    assert "본문 완전성" in prompt
    assert "발행일 존재" in prompt


def test_get_news_validation_prompt_json_format():
    """프롬프트가 JSON 출력 형식 명시"""
    prompt = get_news_validation_prompt(
        title="테스트",
        body_preview="본문",
        date="2025-11-15",
        category="economy",
        category_kr="경제",
        url="https://example.com"
    )

    # Assert JSON format is specified
    assert "JSON" in prompt
    assert "decision" in prompt
    assert "confidence" in prompt
    assert "reasoning" in prompt


# ============================================================================
# Test: get_openai_client()
# ============================================================================

@patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key-123'})
@patch('src.agents.uc1_quality_gate.OpenAI')
def test_get_openai_client_initialization(mock_openai_class):
    """OpenAI 클라이언트 초기화 성공"""
    # Clear cached client
    import src.agents.uc1_quality_gate as uc1_module
    uc1_module._client = None

    # Arrange
    mock_client_instance = Mock()
    mock_openai_class.return_value = mock_client_instance

    # Act
    client = get_openai_client()

    # Assert
    assert client == mock_client_instance
    mock_openai_class.assert_called_once_with(api_key='test-key-123')


@patch.dict('os.environ', {}, clear=True)
def test_get_openai_client_no_api_key():
    """API 키 없으면 ValueError 발생"""
    # Clear cached client
    import src.agents.uc1_quality_gate as uc1_module
    uc1_module._client = None

    # Act & Assert
    with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is not set"):
        get_openai_client()


@patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key-123'})
@patch('src.agents.uc1_quality_gate.OpenAI')
def test_get_openai_client_caching(mock_openai_class):
    """OpenAI 클라이언트는 한 번만 초기화 (캐싱)"""
    # Clear cached client
    import src.agents.uc1_quality_gate as uc1_module
    uc1_module._client = None

    # Arrange
    mock_client_instance = Mock()
    mock_openai_class.return_value = mock_client_instance

    # Act
    client1 = get_openai_client()
    client2 = get_openai_client()

    # Assert
    assert client1 == client2
    assert mock_openai_class.call_count == 1  # Only called once


# ============================================================================
# Test: Edge Cases
# ============================================================================

@patch('src.agents.uc1_quality_gate.get_openai_client')
def test_validate_quality_short_body(mock_get_client, mock_openai_response):
    """짧은 본문 (500자 미만)은 body_complete=False 가능"""
    # Arrange
    mock_client = Mock()
    mock_response_data = mock_openai_response()
    # Modify body_complete to False
    response_dict = json.loads(mock_response_data.choices[0].message.content)
    response_dict["body_complete"] = False
    mock_response_data.choices[0].message.content = json.dumps(response_dict)

    mock_client.chat.completions.create.return_value = mock_response_data
    mock_get_client.return_value = mock_client

    short_article = {
        "content_type": "news",
        "title": "속보",
        "body": "짧은 속보입니다.",  # Very short body
        "date": "2025-11-15",
        "category": "society",
        "category_kr": "사회",
        "url": "https://example.com/news/123"
    }

    # Act
    result = validate_quality(**short_article)

    # Assert
    assert result["body_complete"] is False


@patch('src.agents.uc1_quality_gate.get_openai_client')
def test_validate_quality_no_date(mock_get_client, mock_openai_response):
    """날짜 없는 기사는 date_present=False"""
    # Arrange
    mock_client = Mock()
    mock_response_data = mock_openai_response()
    response_dict = json.loads(mock_response_data.choices[0].message.content)
    response_dict["date_present"] = False
    mock_response_data.choices[0].message.content = json.dumps(response_dict)

    mock_client.chat.completions.create.return_value = mock_response_data
    mock_get_client.return_value = mock_client

    no_date_article = {
        "content_type": "news",
        "title": "제목",
        "body": "본문 " * 100,
        "date": None,  # No date
        "category": "economy",
        "category_kr": "경제",
        "url": "https://example.com/news/123"
    }

    # Act
    result = validate_quality(**no_date_article)

    # Assert
    assert result["date_present"] is False


@patch('src.agents.uc1_quality_gate.get_openai_client')
def test_validate_quality_body_truncation_to_1000_chars(mock_get_client, mock_openai_response):
    """본문이 1000자로 truncate되어 전달되는지 확인"""
    # Arrange
    mock_client = Mock()
    mock_client.chat.completions.create.return_value = mock_openai_response()
    mock_get_client.return_value = mock_client

    long_body = "가" * 5000  # 5000자

    long_article = {
        "content_type": "news",
        "title": "긴 기사",
        "body": long_body,
        "date": "2025-11-15",
        "category": "economy",
        "category_kr": "경제",
        "url": "https://example.com/news/123"
    }

    # Act
    result = validate_quality(**long_article)

    # Assert
    call_args = mock_client.chat.completions.create.call_args
    prompt_content = call_args[1]["messages"][1]["content"]

    # Prompt should contain only first 1000 chars
    assert "가" * 1000 in prompt_content
    assert "가" * 1001 not in prompt_content
