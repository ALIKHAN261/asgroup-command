"""Token auth: every API call must carry the shared secret.

The dashboard stores the token in the browser (localStorage) and sends it
as X-API-Token. Agents can NEVER approve their own queue items — approval
happens only through the API, by you.
"""
import ipaddress

from fastapi import Header, HTTPException, Request

_token = "CHANGE_ME"

def configure(token):
    global _token
    _token = token

def require_token(x_api_token: str = Header(default="")):
    if not x_api_token or x_api_token != _token:
        raise HTTPException(status_code=401, detail="bad or missing API token")
    return True


def require_local_client(request: Request):
    client = request.client
    try:
        is_local = client is not None and ipaddress.ip_address(client.host).is_loopback
    except ValueError:
        is_local = False
    if not is_local:
        raise HTTPException(status_code=403,
                            detail="screen access is restricted to this device")
    return True
