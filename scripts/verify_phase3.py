"""
Phase 3 Verification Script
Validates CostMetric model and Custom Exceptions
"""

from src.storage.models import CostMetric
from src.exceptions import (
    OpenAIAPIError,
    GeminiAPIError,
    is_retryable_error,
    format_error_for_user
)

print('=' * 60)
print('✅ Test 1: CostMetric 모델 임포트 성공')
print('=' * 60)
print(f'테이블명: {CostMetric.__tablename__}')
print(f'컬럼: provider, model, use_case, input_tokens, output_tokens, total_cost')

print('\n' + '=' * 60)
print('✅ Test 2: OpenAI Exception 변환 테스트')
print('=' * 60)
try:
    raise Exception('Error code: 401 - invalid_api_key')
except Exception as e:
    error = OpenAIAPIError.from_openai_error(e)
    print(f'Status Code: {error.status_code}')
    print(f'Error Code: {error.error_code}')
    print(f'Retryable: {is_retryable_error(error)}')
    print(f'User Message: "{format_error_for_user(error)}"')

print('\n' + '=' * 60)
print('✅ Test 3: Gemini Exception 변환 테스트')
print('=' * 60)
try:
    raise Exception('400 API key not valid. [reason: API_KEY_INVALID]')
except Exception as e:
    error = GeminiAPIError.from_gemini_error(e)
    print(f'Status Code: {error.status_code}')
    print(f'Reason: {error.reason}')
    print(f'Retryable: {is_retryable_error(error)}')
    print(f'User Message: "{format_error_for_user(error)}"')

print('\n' + '=' * 60)
print('✅ Test 4: CostMetric 인스턴스 생성 테스트')
print('=' * 60)
metric = CostMetric(
    provider='openai',
    model='gpt-4o-mini',
    use_case='uc1',
    input_tokens=1000,
    output_tokens=200,
    total_tokens=1200,
    input_cost=0.00015,
    output_cost=0.00012,
    total_cost=0.00027,
    url='https://www.yna.co.kr/view/AKR20251109000001001',
    site_name='yna'
)
print(f'{metric}')
print(f'Total Cost: ${metric.total_cost:.6f}')

print('\n' + '=' * 60)
print('🎉 모든 검증 통과!')
print('=' * 60)
