# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, send_file
import requests
import json
import re
import os
from datetime import datetime, timedelta

app = Flask(__name__)

AIRIA_API_KEY = os.environ.get('AIRIA_API_KEY', '')
RECRUITER_EMAIL = os.environ.get('RECRUITER_EMAIL', '')
CANDIDATE_EMAIL = os.environ.get('CANDIDATE_EMAIL', '')

def get_google_creds():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    elif os.environ.get('GOOGLE_TOKEN_JSON'):
        import tempfile
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        tmp.write(os.environ.get('GOOGLE_TOKEN_JSON'))
        tmp.close()
        creds = Credentials.from_authorized_user_file(tmp.name, SCOPES)
        os.unlink(tmp.name)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

def create_meet_event(candidate_name):
    try:
        from googleapiclient.discovery import build
        creds = get_google_creds()
        if not creds:
            print('No Google credentials available')
            return ''
        service = build('calendar', 'v3', credentials=creds)
        start = datetime.utcnow() + timedelta(days=3)
        start = start.replace(hour=10, minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)
        event = {
            'summary': 'HireOS Interview - ' + candidate_name,
            'description': 'Technical interview scheduled via HireOS automated pipeline.',
            'start': {'dateTime': start.isoformat() + 'Z', 'timeZone': 'UTC'},
            'end': {'dateTime': end.isoformat() + 'Z', 'timeZone': 'UTC'},
            'attendees': [{'email': RECRUITER_EMAIL}, {'email': CANDIDATE_EMAIL}],
            'conferenceData': {'createRequest': {'requestId': 'hireos-' + str(int(datetime.utcnow().timestamp())), 'conferenceSolutionKey': {'type': 'hangoutsMeet'}}},
            'reminders': {'useDefault': True}
        }
        event = service.events().insert(calendarId='primary', body=event, conferenceDataVersion=1, sendUpdates='all').execute()
        meet_link = event.get('hangoutLink', '')
        print('Meeting created: ' + meet_link)
        return meet_link
    except Exception as e:
        print('Calendar error: ' + str(e))
        return ''

def get_scorecard(result):
    """Get scorecard from OutputStep in StepsExecutionContext."""
    steps = result.get('StepsExecutionContext', {})
    # Try OutputStep first
    for step_id, step in steps.items():
        if step.get('StepType') == 'OutputStep':
            val = step.get('Result', {}).get('Value', '')
            if val and 'decision' in str(val).lower():
                return val
    # Fallback: top-level result field
    return result.get('result', '')

def parse_json(raw):
    if not raw:
        return None
    try:
        s = re.sub(r'^```json\s*', '', str(raw).strip())
        s = re.sub(r'\s*```$', '', s).strip()
        m = re.search(r'\{[\s\S]*\}', s)
        if m:
            s = m.group(0)
        return json.loads(s)
    except Exception as e:
        print('Parse error: ' + str(e))
        return None

@app.route('/')
def index():
    return send_file('hireos.html')

@app.route('/agent/<agent_id>', methods=['POST'])
def proxy(agent_id):
    data = request.json
    url = 'https://api.airia.ai/v2/PipelineExecution/' + agent_id
    res = requests.post(url, json=data, headers={
        'X-API-KEY': AIRIA_API_KEY,
        'Content-Type': 'application/json'
    }, timeout=300)

    try:
        result = res.json()
    except Exception as e:
        print('Failed to parse Airia response: ' + str(e))
        return jsonify({'error': 'Invalid response from Airia'}), 500

    agent2_id = 'd493f84d-91ad-4805-916d-08ee67232dec'
    if agent_id == agent2_id:
        try:
            raw = get_scorecard(result)
            parsed = parse_json(raw)
            if parsed and parsed.get('decision'):
                print('Scorecard: ' + str(parsed.get('candidate_name')) + ' ' + str(parsed.get('decision')))
                if parsed.get('decision') == 'SHORTLIST':
                    meet_link = create_meet_event(parsed.get('candidate_name', 'Candidate'))
                    if meet_link:
                        parsed['meet_link'] = meet_link
                result['result'] = json.dumps(parsed)
            else:
                print('No scorecard found, raw: ' + str(raw)[:100])
        except Exception as e:
            print('Scorecard error: ' + str(e))

    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5500))
    app.run(host='0.0.0.0', port=port, debug=False)
