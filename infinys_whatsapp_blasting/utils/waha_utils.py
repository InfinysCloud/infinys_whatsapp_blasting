import requests
import json
import base64 as basic64
import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def test_connection(whatapp_api_url, username, password, token, whatsapp_number):
  
    result = ping_server(whatapp_api_url, username, password)

    if result.get('status') == 'success':
        
        result = server_status(whatapp_api_url, token)

        return result
    else:
        _logger.error("Ping failed: %s", result)
        raise UserError(f"Failed to connect to WAHA API: {result.get('message', 'Unknown error')}")


def ping_server(whatapp_api_url, username, password):
    _logger.info("Pinging WAHA API: %s", whatapp_api_url)
    """Simulate a ping to the WAHA API to test the connection."""
    credentials = f"{username}:{password}"
    encoded_credentials = basic64.b64encode(credentials.encode()).decode()
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    payload = { }
    
    try:
        
        response = requests.get(f'{whatapp_api_url}/ping', headers=headers, data=payload)
        response.raise_for_status()
        return success_response(response.json())
    
    except requests.RequestException as e:
        _logger.error("Error pinging WAHA API: %s and header %s", e, headers)
        return {'status': 'error', 'message': str(e)}
   
def server_status(whatapp_api_url, token):
    """Check the server status of the WAHA API."""
    _logger.info("Checking server status: %s", whatapp_api_url)
   
    headers = {
        'X-Api-Key': f'{token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    payload = { }
   
    try:
        response = requests.get(f'{whatapp_api_url}/api/server/status', headers=headers, data=payload)
        response.raise_for_status()
        return success_response(response.json())
    except requests.RequestException as e:
        _logger.error("Error server_status WAHA API: %s", e)
        return error_response(e, "Failed to connect to WAHA API")
   
def test_send_message(self,idwaconfig, wanumberto, replyto, message):
    """Simulate a ping to the WAHA API to test the connection."""
    payload = { }
    
    try:
        wa_config = self.env['infinys.whatsapp.config'].sudo().search([('id','=',idwaconfig)], limit=1)

        if wa_config :
            whatapp_api_url = wa_config.whatsapp_api_url
            token = wa_config.token
            wanumbersource = replyto

            headers = {
                "X-Api-Key": f"{token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            payload = {
                "chatId": f"{wanumberto}",
                "text" : f"{message}",
                "session" : "default",
                "reply_to" : f"{wanumbersource}",
            }

            response = requests.post(f"{whatapp_api_url}/api/sendText", headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            return success_response(response.json())
        else:
            return error_response(e, "WA Config Not Found")
        
        
        return error_response(e, "Failed to Send Message")

    except requests.RequestException as e:
        _logger.error("Error send_message WAHA API: %s", e)
        return {'status': 'error', 'message': str(e)}
    
def error_response(error, msg):
    return {
        "jsonrpc": "2.0",
        "id": None,
        "status": "error",
        "error": {
            "code": 200,
            "message": msg,
            "data": {
                "name": str(error),
                "debug": "",
                "message": msg,
                "arguments": list(error.args),
                "exception_type": type(error).__name__
            }
        }
    }

def success_response(data):
    return {
        "jsonrpc": "2.0",
        "id": None,
        "status": "success",
        "result": data
    }