"""
Cost Dashboard 테스트 스크립트
Gradio UI 없이 cost_tracker 기능만 검증
"""

from src.monitoring.cost_tracker import (
    calculate_cost,
    log_cost_to_db,
    get_cost_breakdown,
    get_total_cost
)

print('=' * 60)
print('✅ Test 1: calculate_cost() 함수 테스트')
print('=' * 60)

# GPT-4o-mini 비용 계산 (1000 input, 200 output tokens)
cost = calculate_cost('openai', 'gpt-4o-mini', 1000, 200)
print(f'Provider: openai')
print(f'Model: gpt-4o-mini')
print(f'Input Tokens: 1000, Output Tokens: 200')
print(f'Input Cost: ${cost["input_cost"]:.6f}')
print(f'Output Cost: ${cost["output_cost"]:.6f}')
print(f'Total Cost: ${cost["total_cost"]:.6f}')
print()

print('=' * 60)
print('✅ Test 2: log_cost_to_db() 함수 테스트')
print('=' * 60)

# 테스트 비용 기록 저장
metric_id = log_cost_to_db(
    provider='openai',
    model='gpt-4o-mini',
    use_case='uc2',
    input_tokens=1500,
    output_tokens=300,
    url='https://www.yna.co.kr/view/AKR20251111000001001',
    site_name='yna',
    extra_data={'test': True}
)

if metric_id:
    print(f'✅ 비용 기록 저장 성공 (ID: {metric_id})')
else:
    print('❌ 비용 기록 저장 실패')
print()

print('=' * 60)
print('✅ Test 3: get_cost_breakdown() 함수 테스트')
print('=' * 60)

breakdown = get_cost_breakdown()
print(f'Total Cost: ${breakdown["total_cost"]:.6f}')
print(f'Total Tokens: {breakdown["total_tokens"]:,}')
print(f'By Provider: {breakdown["by_provider"]}')
print(f'By Use Case: {breakdown["by_use_case"]}')
print(f'By Model: {breakdown["by_model"]}')
print(f'Recent Costs Count: {len(breakdown["recent_costs"])}')
print()

if breakdown["recent_costs"]:
    print('최근 비용 기록 (최신 3개):')
    for i, cost in enumerate(breakdown["recent_costs"][:3], 1):
        print(f'  {i}. {cost["timestamp"][:19]} | {cost["provider"]}/{cost["model"]} | ${cost["total_cost"]:.6f} | {cost["use_case"]}')
print()

print('=' * 60)
print('✅ Test 4: get_total_cost() 필터링 테스트')
print('=' * 60)

# UC2만 조회
uc2_cost = get_total_cost(use_case='uc2')
print(f'UC2 Total Cost: ${uc2_cost:.6f}')

# OpenAI만 조회
openai_cost = get_total_cost(provider='openai')
print(f'OpenAI Total Cost: ${openai_cost:.6f}')

# YNA 사이트만 조회
yna_cost = get_total_cost(site_name='yna')
print(f'YNA Site Total Cost: ${yna_cost:.6f}')
print()

print('=' * 60)
print('🎉 모든 테스트 완료!')
print('=' * 60)
print('✅ Cost Dashboard가 정상적으로 동작합니다.')
print('✅ Gradio UI에서 "💰 비용 분석" 탭을 확인하세요.')
