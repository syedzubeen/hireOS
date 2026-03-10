from flask import Flask, request, jsonify, send_file
import requests
import json
import re
import os
from datetime import datetime, timedelta

app = Flask(__name__)

AIRIA_API_KEY = os.environ.get('AIRIA_API_KEY', '')
RECRUITER_EMAIL = os.environ.get('RECRUITER_EMAIL', 'airiahackathon@gmail.com')
CANDIDATE_EMAIL = os.environ.get('CANDIDATE_EMAIL', 'zubeenqy@gmail.com')

def get_google_creds():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None

    # Try token.json file first (local dev)
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # Try environment variable (production/Render/Railway)
    elif os.environ.get('GOOGLE_TOKEN_JSON'):
        import tempfile
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        tmp.write(os.environ.get('GOOGLE_TOKEN_JSON'))
        tmp.close()
        creds = Credentials.from_authorized_user_file(tmp.name, SCOPES)
        os.unlink(tmp.name)

    # Refresh if expired
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
			'summary': f'HireOS Interview - {candidate_name}',
            'description': f'Technical interview for {candidate_name} scheduled via HireOS automated pipeline.',
            'start': {'dateTime': start.isoformat() + 'Z', 'timeZone': 'UTC'},
            'end': {'dateTime': end.isoformat() + 'Z', 'timeZone': 'UTC'},
            'attendees': [
                {'email': RECRUITER_EMAIL},
                {'email': CANDIDATE_EMAIL}
            ],
            'conferenceData': {
                'createRequest': {
                    'requestId': f'hireos-{int(datetime.utcnow().timestamp())}',
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            },
            'reminders': {'useDefault': True}
        }

        event = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1,
            sendUpdates='all'
        ).execute()

        meet_link = event.get('hangoutLink', '')
        print(f'Meeting created: {meet_link}')
        return meet_link

    except Exception as e:
        print(f'Calendar error: {e}')
        return ''

@app.route('/')
def index():
    return send_file('hireos.html')

@app.route('/agent/<agent_id>', methods=['POST'])
def proxy(agent_id):
    data = request.json
    url = f'https://api.airia.ai/v2/PipelineExecution/{agent_id}'
    res = requests.post(url, json=data, headers={
        'X-API-KEY': AIRIA_API_KEY,
        'Content-Type': 'application/json'
    }, timeout=120)

    try:
        result = res.json()
    except Exception as e:
        print(f'Failed to parse Airia response: {e}')
        print(f'Raw response: {res.text[:500]}')
        return jsonify({'error': 'Invalid response from Airia'}), 500

    # For Agent 2 — if SHORTLIST, create Google Meet
    try:
        raw = result.get('result', '')
        if raw:
            clean = re.sub(r'^```json\s*|\s*```$', '', raw.strip())
            parsed = json.loads(clean)
            if parsed.get('decision') == 'SHORTLIST':
                candidate_name = parsed.get('candidate_name', 'Candidate')
                meet_link = create_meet_event(candidate_name)
                if meet_link:
                    parsed['meet_link'] = meet_link
                    result['result'] = json.dumps(parsed)
    except Exception as e:
        print(f'Meet scheduling error: {e}')

    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5500))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)