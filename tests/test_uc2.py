"""UC2 Self-Healing Test Script"""
from src.workflow.master_crawl_workflow import build_master_graph
import time

# Build master graph
start = time.time()
app = build_master_graph()

initial_state = {
    'url': 'https://n.news.naver.com/mnews/article/009/0005591267',
    'site_name': 'naver',
    'html_content': None,
    'current_uc': None,
    'next_action': None,
    'failure_count': 0,
    'quality_passed': None,
    'extracted_title': None,
    'extracted_body': None,
    'extracted_date': None,
    'uc1_validation_result': None,
    'uc2_consensus_result': None,
    'uc3_discovery_result': None,
    'final_result': None,
    'error_message': None,
    'workflow_history': [],
    'supervisor_reasoning': None,
    'supervisor_confidence': None,
    'routing_context': None
}

result = app.invoke(initial_state)
duration = time.time() - start

print("\n=== UC2 SELF-HEALING TEST RESULT ===")
print(f"Duration: {duration:.2f}s")
print(f"Workflow History: {result.get('workflow_history')}")
print(f"UC2 Triggered: {'uc2' in str(result.get('workflow_history'))}")

if result.get('uc2_consensus_result'):
    print(f"Consensus Reached: {result['uc2_consensus_result'].get('consensus_reached')}")
    print(f"Consensus Score: {result['uc2_consensus_result'].get('consensus_score')}")

uc1_result = result.get('uc1_validation_result', {})
print(f"Final Quality Score: {uc1_result.get('quality_score', 0)}")
print(f"Quality Passed: {result.get('quality_passed')}")
