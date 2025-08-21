import logging
from odoo import api, fields, models
from odoo.exceptions import UserError 
from ..utils import waha_utils

_logger = logging.getLogger(__name__)
_waha_utils = waha_utils
    
class InfinysWhatsappConfig(models.Model):
    _name = 'infinys.whatsapp.config'
    _description = 'WhatsApp API Configuration'
    _order = 'name'

    # Adding a name field is a best practice for easy identification
    name = fields.Char(string="Configuration Name", required=True, default="Default Configuration", size=60)
    provider = fields.Selection([
        ('waha', 'WAHA (WhatsApp API by Infinys)'),
        ('meta', 'Meta Cloud API (Facebook)')
    ], string="Provider", required=True, default='waha', 
       help="Select your WhatsApp service provider. The required API payload will change based on this selection.")

    whatsapp_number = fields.Char(string='Phone Number ID', required=True, help="The WhatsApp phone number associated with this configuration.")
    token = fields.Char(string='Access Token / Session Key', help="Authentication token or session key for the API.")
    webhook_url = fields.Char(string='Webhook URL N8n', required=True, help="The URL where WhatsApp will send incoming messages and notifications.")
    authentication_user = fields.Char(string='Auth User/App ID', help="Username for basic authentication, if required by the API.")
    authentication_password = fields.Char(string='Auth Password/App Secret', help="Password for basic authentication, if required by the API.")
    active = fields.Boolean(default=True, help="Set active to false to hide this configuration without removing it.")
    whatsapp_api_url = fields.Char(string='WhatsApp API URL', 
                                   help="The base URL for the WhatsApp API, used for sending messages and other operations.",
                                   required=True)
    
    ir_deployment  = fields.Char(
        string='Deployment',
        compute='_compute_ir_deployment'
    )

    invisible_trial = fields.Boolean(
        string='Invisible Trial',
     )

    welcome_message = fields.Html(string='Welcome Message', help="The welcome message when a user sends a message",  sanitize=False)

    _sql_constraints = [
        ('unique_whatsapp_number', 'UNIQUE(whatsapp_number)', 'The WhatsApp number must be unique across configurations.'),
        ('unique_provide', 'UNIQUE(provider)', 'The Provider must be unique across configurations.')
    ]
    
    def btn_test_credential(self):
        """Test the API connection using the configured settings."""
        _logger.info("btn_test_api")
        data = {}
        status = 'success'

        if (self.provider=='waha'):
            message = "Testing WAHA API connection : "

            data = _waha_utils.test_connection(
               whatapp_api_url=self.whatsapp_api_url,
               username=self.authentication_user,
               password=self.authentication_password,
               token=self.token,
               whatsapp_number=self.whatsapp_number
            )
    
            if (data.get('status') == 'success'):
                message += "Connection successful."
            else:
                status = 'warning'
                message += "Connection failed." + f" Error: {data.get('message', 'Unknown error')}"

        elif (self.provider == 'meta'):
            message = "Testing Meta API connection with the following settings: "
            message += f"API URL: {self.api_url}, Token: {self.token}, Webhook URL: {self.webhook_url}"
            message += f"Auth User: {self.authentication_user}, Auth Password: {self.authentication_password}"
            message += "Currently, not yet implemented for Meta API (Comming soon)."
        else:
            message = "Currently, not yet implemented for Meta API (Comming soon)."
        
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Connection Successful",
                'message': message,
                'type': f'{status}',  # 'success' for green, 'warning' for orange
                'sticky': False,  # Keep the notification until the user clicks it away
            }
        }

    def _compute_ir_deployment(self):
        ir_deployment = self.env['ir.config_parameter'].sudo().get_param('infinys_whatsapp_blasting.deployment')
        for rec in self:
            self.ir_deployment= ir_deployment
            if ir_deployment.lower() == 'trial' or ir_deployment == 'Trial':
                rec.invisible_trial = True
            else:
                rec.invisible_trial = False

        