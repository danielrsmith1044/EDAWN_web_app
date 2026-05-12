import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Test Salesforce connection and Case creation'

    def handle(self, *args, **options):
        client_id = getattr(settings, 'SF_CLIENT_ID', '')
        client_secret = getattr(settings, 'SF_CLIENT_SECRET', '')
        login_url = (getattr(settings, 'SF_LOGIN_URL', '') or 'https://login.salesforce.com').rstrip('/')

        self.stdout.write(f"SF_CLIENT_ID set:     {'YES' if client_id else 'NO - MISSING'}")
        self.stdout.write(f"SF_CLIENT_SECRET set: {'YES' if client_secret else 'NO - MISSING'}")
        self.stdout.write(f"Login URL:            {login_url}")

        if not client_id or not client_secret:
            self.stderr.write("Cannot continue without credentials.")
            return

        # Step 1: get token
        self.stdout.write("\n--- Step 1: OAuth token ---")
        token_url = f"{login_url}/services/oauth2/token"
        data = urllib.parse.urlencode({
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
        }).encode()
        req = urllib.request.Request(token_url, data=data, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read())
            token = body['access_token']
            instance_url = body['instance_url']
            self.stdout.write(f"Token OK. Instance: {instance_url}")
        except urllib.error.HTTPError as exc:
            self.stderr.write(f"Token FAILED ({exc.code}): {exc.read().decode()}")
            return
        except Exception as exc:
            self.stderr.write(f"Token FAILED: {exc}")
            return

        # Step 2: create a test Case
        self.stdout.write("\n--- Step 2: Create test Case ---")
        case = {
            'Subject': 'TEST - Business Builder Visit Integration Check',
            'Type': 'Visit',
            'Reason': 'Visit',
            'Origin': 'Visit',
            'Status': 'Closed',
            'Visit__c': True,
            'SuppliedCompany': 'TEST COMPANY',
        }
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        url = f"{instance_url}/services/data/v59.0/sobjects/Case/"
        req = urllib.request.Request(url, data=json.dumps(case).encode(), headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
            self.stdout.write(self.style.SUCCESS(f"Case created! Id: {result.get('id')}"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode()
            self.stderr.write(f"Case creation FAILED ({exc.code}): {body}")
        except Exception as exc:
            self.stderr.write(f"Case creation FAILED: {exc}")
