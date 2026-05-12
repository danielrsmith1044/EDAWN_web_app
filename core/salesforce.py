import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

_DEFAULT_LOGIN_URL = 'https://login.salesforce.com'
_API_VERSION = 'v59.0'


def _soql_escape(value):
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _get_access_token():
    client_id = getattr(settings, 'SF_CLIENT_ID', '')
    client_secret = getattr(settings, 'SF_CLIENT_SECRET', '')
    if not client_id or not client_secret:
        return None, None

    login_url = (getattr(settings, 'SF_LOGIN_URL', '') or _DEFAULT_LOGIN_URL).rstrip('/')
    token_url = f"{login_url}/services/oauth2/token"
    logger.warning("Salesforce token request to: %s", login_url)

    data = urllib.parse.urlencode({
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
    }).encode()

    req = urllib.request.Request(token_url, data=data, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f"Salesforce token request failed ({exc.code}): {error_body}") from exc
    return body['access_token'], body['instance_url']


def _api_request(method, url, token, payload=None):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Salesforce API {method} {url} returned {exc.code}: {exc.read()}") from exc


def _lookup_account_id(instance_url, token, company_name):
    soql = f"SELECT Id FROM Account WHERE Name = '{_soql_escape(company_name)}' LIMIT 1"
    url = f"{instance_url}/services/data/{_API_VERSION}/query?q={urllib.parse.quote(soql)}"
    result = _api_request('GET', url, token)
    records = result.get('records', [])
    return records[0]['Id'] if records else None


def sync_visit_to_salesforce(visit_note):
    """Create a Salesforce Case for a completed volunteer visit. Fails silently if unconfigured."""
    if not getattr(settings, 'SF_CLIENT_ID', ''):
        return

    try:
        token, instance_url = _get_access_token()
        if not token:
            return

        company = visit_note.assignment.company
        volunteer = visit_note.visited_by
        volunteer_name = (volunteer.get_full_name() or volunteer.username)[:100]

        account_id = _lookup_account_id(instance_url, token, company.name)

        hiring_to_turnover = {
            'hiring':  'Increasing',
            'layoffs': 'Decreasing',
            'stable':  'Stable',
        }

        expansion_flags = []
        if visit_note.expansion_adding_sq_footage:
            expansion_flags.append('Adding square footage')
        if visit_note.expansion_new_building:
            expansion_flags.append('Looking for / moving to new building')
        if visit_note.expansion_adding_equipment:
            expansion_flags.append('Adding equipment')
        if visit_note.expansion_capex_planned:
            expansion_flags.append('Capital expenditure planned')
        if visit_note.expansion_notes:
            expansion_flags.append(visit_note.expansion_notes)

        case = {
            'Subject':                          f'Business Builder Visit – {company.name}',
            'Type':                             'Visit',
            'Reason':                           'Visit',
            'Origin':                           'Visit',
            'Status':                           'Closed',
            'Visit__c':                         True,
            'Visit_Date__c':                    visit_note.visit_date.date().isoformat(),
            'Business_Builders_Volunteer_Name__c': volunteer_name,
            'Company_Contact_Name__c':          (visit_note.contact_name or '')[:50],
            'Case_Notes__c':                    (visit_note.notes or '')[:1000],
            'Assistance_Provided__c':           visit_note.volunteer_helped,
            'Assistance_Provided_Description__c': (visit_note.volunteer_helped_notes or '')[:1500],
            'At_Capacity__c':                   visit_note.at_capacity == 'yes',
            'Looking_For_A_New_Location__c':    visit_note.expansion_new_building,
            'Expanding__c':                     any([
                visit_note.expansion_adding_sq_footage,
                visit_note.expansion_new_building,
                visit_note.expansion_adding_equipment,
                visit_note.expansion_capex_planned,
            ]),
            'Follow_Up_Action_Items__c': (
                (visit_note.follow_up_notes or '')[:1000] if visit_note.follow_up_needed else ''
            ),
        }

        if account_id:
            case['AccountId'] = account_id
        case['SuppliedCompany'] = company.name[:80]

        if visit_note.employee_count is not None:
            case['Current_Number_of_Employees__c'] = visit_note.employee_count
        if visit_note.jobs_added_last_year is not None:
            case['of_Jobs_Added_in_the_last_12_months__c'] = visit_note.jobs_added_last_year
        if visit_note.jobs_added_expected is not None:
            case['Full_Time_Jobs_to_Add_This_Year__c'] = visit_note.jobs_added_expected
        if visit_note.building_size_sqft is not None:
            case['Building_Size__c'] = str(visit_note.building_size_sqft)
        if visit_note.hiring_status in hiring_to_turnover:
            case['Turnover__c'] = hiring_to_turnover[visit_note.hiring_status]
        if visit_note.additional_contact_name:
            case['X2nd_Contact__c'] = visit_note.additional_contact_name[:50]
        if visit_note.additional_contact_title:
            case['X2nd_Contact_Title__c'] = visit_note.additional_contact_title[:50]
        if visit_note.additional_contact_phone:
            case['X2nd_Contact_Phone__c'] = visit_note.additional_contact_phone[:40]
        if visit_note.additional_contact_email:
            case['X2nd_Contact_Email__c'] = visit_note.additional_contact_email[:80]
        if expansion_flags:
            case['Current_Issues__c'] = '\n'.join(expansion_flags)

        case_url = f"{instance_url}/services/data/{_API_VERSION}/sobjects/Case/"
        try:
            _api_request('POST', case_url, token, case)
        except RuntimeError as exc:
            if 'AccountId' in str(exc) and 'INVALID_FIELD_FOR_INSERT_UPDATE' in str(exc):
                # Run As user lacks FLS edit on AccountId — retry without it.
                # Fix: Setup → Object Manager → Case → Fields → Account ID → Set Field-Level Security
                logger.warning("AccountId FLS not set; creating Case without account link")
                case.pop('AccountId', None)
                _api_request('POST', case_url, token, case)
            else:
                raise

    except Exception:
        logger.exception("Failed to sync visit note %s to Salesforce", visit_note.pk)
