"""Verify FastAPI /predictions/sessions endpoint against real Postgres DB."""
import json
from fastapi.testclient import TestClient
from services.api.main import app

client = TestClient(app)

symbols = ["AAPL", "MSFT", "NVDA", "RELIANCE.NS", "TCS.NS", "BTC-USD"]

for sym in symbols:
    resp = client.get(f"/predictions/sessions?symbol={sym}")
    print(f"=== Symbol: {sym} (Status: {resp.status_code}) ===")
    if resp.status_code == 200:
        data = resp.json()
        print(f"  Target Date Today: {data.get('target_date_today')} | Has Today: {data.get('today') is not None}")
        if data.get('today'):
            t = data['today']
            print(f"    Today: target_session={t['target_session']}, prob_up={t['probability_up']}, pred={t['predicted_direction']}, status={t['session_status']}, realized={t['realized_direction']}")
        print(f"  Target Date Tomorrow: {data.get('target_date_tomorrow')} | Has Tomorrow: {data.get('tomorrow') is not None}")
        if data.get('tomorrow'):
            tm = data['tomorrow']
            print(f"    Tomorrow: target_session={tm['target_session']}, prob_up={tm['probability_up']}, pred={tm['predicted_direction']}, status={tm['session_status']}, realized={tm['realized_direction']}")
        if data.get('pending_reason'):
            print(f"  Pending reason: {data.get('pending_reason')}")
    else:
        print(f"  Error: {resp.text}")
