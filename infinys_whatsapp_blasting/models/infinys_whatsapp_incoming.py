import logging
import json
from odoo import api, fields, models
from odoo.exceptions import UserError
from ..models import infinys_whatsapp_mailing
from ..utils import texttohtml_utils
from ..utils import waha_utils


_logger = logging.getLogger(__name__)
_texttohtml_utils = texttohtml_utils
_waha_utils = waha_utils

class WhatsappIncomingMessage(models.Model):
    _name = 'infinys.whatsapp.incoming'
    _description = 'Whatsapp Incoming Message (Inbox)'
    _order = 'create_date desc'

    name = fields.Char(string="From", store=True)
    from_number = fields.Char(string="Sender Number", required=True, index=True)
    to_number = fields.Char(string="Receiver Number", required=True, index=True)

    raw_data = fields.Text(string="Raw Message")
    body = fields.Text(string="Message", help="The main content of the message.")
    reply_message = fields.Html(string="Reply Message",  sanitize=False)
    state = fields.Selection([('unread', 'Unread'), ('read', 'Read')], default='unread')
    quotedMsgId = fields.Char(string="Quoted Message ID")
    
    contact_id = fields.Many2one('infinys.whatsapp.contact', string="Whatsapp Contact", ondelete='cascade')

    hasmedia = fields.Boolean(string="Has Media", default=False)
    mime_type = fields.Char(string="MIME Type", default='text/plain')
   
    create_date = fields.Datetime(string="Received At", default=fields.Datetime.now, readonly=True) 
    file_media = fields.Binary(string="Media File")
    
    order_date = fields.Date(
        string='Order Date',
        compute='_compute_order_date',
        store=True
    )

    order_month = fields.Char(
        string='Order Month',
        compute='_compute_order_month',
        store=True
    )

    def action_mark_as_read(self):
        self.write({'state': 'read'})

    def action_mark_as_unread(self):
        self.write({'state': 'unread'})
    
    @api.depends('create_date')
    def _compute_order_date(self):
        for record in self:
            if record.create_date:
                record.order_date = record.create_date.date()
            else:
                record.order_date = False

    @api.depends('create_date')
    def _compute_order_month(self):
        for record in self:
            if record.create_date:
                record.order_month = record.create_date.strftime("%Y-%b")
    
    @api.onchange('from_number')
    def _onchange_from_number(self):
        if self.from_number:
            indonesia = self.env['res.country'].sudo().search([('code', '=', 'ID')], limit=1)
            self.contact_id = self.env['infinys.whatsapp.contact'].search([('whatsapp_number', '=', self.from_number)], limit=1)
            _logger.info(f"Contact found: {self.contact_id.id} for number: {self.from_number}")
            if not self.contact_id.id:
                _logger.info(f"Creating new contact for number: {self.from_number}")
                self.contact_id = self.env['infinys.whatsapp.contact'].sudo().create({
                    'name': self.name,
                    'whatsapp_number': self.from_number,
                    'country_id': indonesia.id if indonesia else None,
                    'is_active': True,
                    'is_new_user': False,  # Set as new user
                    'is_manual': False,  # Set as not manual entry
                    'total_received_messages': 1
                })

                _logger.info(f"Creating new contact for contact_id: {self.contact_id.id}")
            else:
                self.name = self.contact_id.name 
                self.contact_id.sudo().write({
                    'is_new_user': False,  # Set as not new user
                    'total_received_messages': self.contact_id.total_received_messages + 1
                })             

    def btn_reply_queue_message(self):

        try:

            text_message = self.reply_message

            if not self.quotedMsgId:
                raise UserError("Please input reply message.")

            if not text_message:
                raise UserError("Please input message.")

            config_id = self.env['infinys.whatsapp.config'].search([('whatsapp_number', '=', self.to_number)],limit=1)
            contact_id = self.contact_id
            
            if not config_id:
                raise UserError("No WhatsApp configuration found for this number.")
            
            mailing_record = self.env['infinys.whatsapp.mailing'].search([('id', '=', 0)],limit=1)
            mailinglist = self.env['infinys.whatsapp.mailinglist'].search([('id', '=', 0)],limit=1)
            rec_mailing_log = self.env['infinys.whatsapp.mailing.log'].search([('id', '=', 0)],limit=1)

            text_message = texttohtml_utils.clean_html_for_whatsapp(self.reply_message)

            contact_data = ({
                   "sent_id" : f"{0}",
                   "contact_id" : f"{self.contact_id.id}", 
                   "contact_name" : f"{self.name}",
                   "contact_whatsapp" : f"{self.from_number}",
                   "message" : f"{text_message}",
            })
            _logger.info(f"btn_reply_queue_message contact_data: {contact_data}")

                    
            payload = {
                    "jsonrpc": "2.0",
                    "wa_config_id": f"{config_id.id}",
                    "wa_config_name": f"{config_id.name}",
                    "mailing_id": "0",
                    "mailing_list": "0",
                    "mailing_list_name": "",
                    "mailing_log_id": "0",
                    "session" : "default",
                    "reply_to": f"{self.quotedMsgId}",
                    "contact": f"{json.dumps(contact_data)}"
                }

            #create record infinys whatsapp sent
            records = self.env['infinys.whatsapp.sent'].create({
                'name': self.name,
                'config_id' : config_id.id,
                'mailing_id': mailing_record.id,
                'mailing_list_id': mailing_record.mailing_list_id.id,
                'mailing_log_id': rec_mailing_log.id,
                'contact_id': self.contact_id.id,
                'from_number': self.contact_id.whatsapp_number,
                'to_number': self.quotedMsgId,
                'quotedMsgId': self.quotedMsgId,
                'body': text_message,
                'json_message': json.dumps(payload),
                'json_contact' : json.dumps(contact_data),
                'mime_type': 'text/plain',
                'hasmedia' : False,
                'is_queued' : True
            })
            _logger.info(f"btn_reply_queue_message Sending payload: {payload}")
            
            message = f"Processing Reply message from {config_id.whatsapp_number} with to recipients : {self.from_number} on queue"
            _logger.info(f"Sending message to {config_id.whatsapp_number} ")
            
            return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': "Reply Successful",
                        'message': message,
                        'type': 'success',  # 'success' for green, 'warning' for orange
                        'sticky': False,  # Keep the notification until the user clicks it away
                    }
                }
        
        except Exception as e:
            _logger.error(f"Error in btn_reply_queue_message: {e}")
            raise UserError(f"Error in btn_reply_queue_message: {e}")
        