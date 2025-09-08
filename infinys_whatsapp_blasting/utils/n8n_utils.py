import requests
import json
import base64 as basic64
import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def send_message(self, n8n_webhook_url, user_auth, user_password, payloads):
    url = n8n_webhook_url 

    if not n8n_webhook_url:
        raise UserError("Please configure the N8N Webhook URL, User Auth, and User Password in the system settings.")
    
    ir_deployment = self.env['ir.config_parameter'].sudo().get_param('infinys_whatsapp_blasting.deployment').lower();

    if ir_deployment not in ['development', 'production', 'trial']:
        raise UserError("Invalid deployment configuration. Please set it to 'Development' or 'Production'. 'Trial' is also a valid option.")

    if ir_deployment == 'development':
        url = n8n_webhook_url.strip().replace("/webhook/", "/webhook-test/")
        
    if ir_deployment == 'production':
        url = n8n_webhook_url 

    if ir_deployment == 'trial':
        url = n8n_webhook_url

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {basic64.b64encode(f'{user_auth}:{user_password}'.encode()).decode()}"
    }
     
    response = requests.post(url, headers=headers, data=json.dumps(payloads))
    
    return response.json()