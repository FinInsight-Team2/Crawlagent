"""UC3 Discovery Test Script"""
from src.workflow.master_crawl_workflow import build_master_graph
import time

# Build master graph
start = time.time()
app = build_master_graph()

# Test with a new site that doesn't exist in DB
initial_state = {
    'url': 'https://www.hani.co.kr/arti/politics/politics_general/1177087.html',
    'site_name': 'hani',  # New site not in DB
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

print("\n=== UC3 DISCOVERY TEST RESULT ===")
print(f"Duration: {duration:.2f}s")
print(f"Workflow History: {result.get('workflow_history')}")
print(f"UC3 Triggered: {'uc3' in str(result.get('workflow_history'))}")

if result.get('uc3_discovery_result'):
    uc3_result = result['uc3_discovery_result']
    print(f"Selectors Discovered: {uc3_result.get('selectors_discovered') is not None}")
    print(f"Confidence: {uc3_result.get('confidence')}")
    if uc3_result.get('selectors_discovered'):
        selectors = uc3_result['selectors_discovered']
        print(f"Title Selector: {selectors.get('title') or selectors.get('title_selector')}")
        print(f"Body Selector: {selectors.get('body') or selectors.get('body_selector')}")
        print(f"Date Selector: {selectors.get('date') or selectors.get('date_selector')}")

print(f"Error Message: {result.get('error_message')}")

# Check if selector was saved to DB
from src.storage.database import get_db
from src.storage.models import Selector

db = next(get_db())
selector = db.query(Selector).filter(Selector.site_name == 'hani').first()
if selector:
    print("\n✅ Selector saved to DB:")
    print(f"  Title: {selector.title_selector}")
    print(f"  Body: {selector.body_selector}")
    print(f"  Date: {selector.date_selector}")
else:
    print("\n❌ Selector NOT saved to DB")
