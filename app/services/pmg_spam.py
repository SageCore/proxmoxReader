# app/services/pmg_spam.py
import time
from typing import List, Dict, Any
from . import pmg_api
from app.services.client_domains import get_domains_for_client
import time
from typing import Optional
from fastapi import Query

def normalize_user_email(u: Any) -> str | None:
    """
    Normalize the 'user' entry returned by PMG to an email string.
    Handles cases where PMG returns strings or dicts with keys like
    'address', 'email', or 'pmail'.
    """
    if isinstance(u, str):
        return u.lower()
    if isinstance(u, dict):
        for k in ("address", "mail", "pmail"):
            v = u.get(k)
            if v:
                return v.lower()
    return None

def email_matches_domains(email: str, domains: List[str]) -> bool:
    if not email or "@" not in email:
        return False
    domain = email.split("@", 1)[1].lower()
    return domain in domains

def get_spam_quarantine(client_id: int, starttime: int = None, endtime: int = None) -> List[Dict]:
    """
    Fetch spam quarantine messages only for the domains the client owns.
    Returns a flat list of message dicts, each augmented with _pmg_host and _pmg_email.
    """

    # now = int(time.time())

    # starttime: Optional[int] = Query(None, description="Unix epoch start time for spam query")
    # endtime: Optional[int] = Query(None, description="Unix epoch end time for spam query")

    # if starttime is None or starttime < 0:
    #     starttime = now - 86400  # 1 day ago
    # if endtime is None or endtime < 0:
    #     endtime = now
    # if starttime is None:
    #     starttime = int(time.time()) - 86400000000
    # if endtime is None:
    #     endtime = int(time.time())

    # obtain allowed domains for this client
    allowed_domains = get_domains_for_client(client_id)
    allowed_domains = [d.lower() for d in allowed_domains]
    print("CLIENT DOMAINS:", allowed_domains)

    all_spam: List[Dict] = []

    for host in pmg_api.PMG_HOSTS:
        try:
            sess_info = pmg_api.login_and_get_session(host)
            session = sess_info["session"]
            csrf = sess_info.get("csrf")

            headers = {}
            if csrf:
                headers["CSRFPreventionToken"] = csrf

            # STEP 1: fetch spam users
            resp_users = session.get(
                f"https://{host}/api2/json/quarantine/spamusers",
                params={
                    "starttime": starttime,
                    "endtime": endtime,
                    "quarantine-type": "spam"
                },
                headers=headers,
                timeout=pmg_api.REQUEST_TIMEOUT
            )
            resp_users.raise_for_status()
            raw_users = resp_users.json()
            print(f"RAW USERS FROM {host}:", raw_users)
            users = raw_users.get("data", []) if isinstance(raw_users, dict) else raw_users

            # normalize to list of email strings
            normalized_users: List[str] = []
            for u in users:
                em = normalize_user_email(u)
                if em:
                    normalized_users.append(em)
            print(f"NORMALIZED USERS FROM {host}:", normalized_users)

            # filter by allowed domains
            filtered_users = [em for em in normalized_users if email_matches_domains(em, allowed_domains)]
            print(f"FILTERED USERS FOR CLIENT ON {host}:", filtered_users)

            # STEP 2: fetch messages for each allowed email
            for user_email in filtered_users:
                try:
                    resp_spam = session.get(
                        f"https://{host}/api2/json/quarantine/spam",
                        params={
                            "starttime": starttime,
                            "endtime": endtime,
                            "pmail": user_email
                        },
                        headers=headers,
                        timeout=pmg_api.REQUEST_TIMEOUT
                    )
                    resp_spam.raise_for_status()
                    j = resp_spam.json()
                    messages = j.get("data", []) if isinstance(j, dict) else j

                    for m in messages:
                        # annotate for traceability
                        m["_pmg_host"] = host
                        m["_pmg_email"] = user_email
                        all_spam.append(m)

                except Exception as e_inner:
                    print(f"Error fetching spam for {user_email} on host {host}: {e_inner}")
                    # continue to next email
                    continue

            # small throttle so we don't hammer PMG across nodes/hosts
            time.sleep(0.05)

        except Exception as e:
            print(f"Error fetching spam for host {host}: {e}")
            continue

    return all_spam
