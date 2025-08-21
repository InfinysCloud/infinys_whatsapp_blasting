import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class WhatsappSentMessage(models.Model):
    _name = 'infinys.whatsapp.sent'
    _description = 'Whatsapp Sent / Outgoing'
    _order = 'create_date desc'

    name = fields.Char(string="From", store=True)
    from_number = fields.Char(string="Sender Number", required=True, index=True)
    to_number = fields.Char(string="Receiver Number", required=True, index=True)

    body = fields.Text(string="Message", help="The main content of the message.")
    json_message = fields.Text(string="JSON Message", help="The main content of the message.")
    json_contact = fields.Text(string="JSON Contact")
    is_queued = fields.Boolean(string="Is Queued", default=True)
    quotedMsgId = fields.Char(string="Quoted Message ID")

    config_id = fields.Many2one('infinys.whatsapp.config', string="Whatsapp Config", required=True, ondelete='cascade')
    contact_id = fields.Many2one('infinys.whatsapp.contact', string="Whatsapp Contact", ondelete='cascade')
    mailing_id = fields.Many2one('infinys.whatsapp.mailing', string="Mailing", ondelete='cascade')
    mailing_list_id = fields.Many2one('infinys.whatsapp.mailinglist', string="Mailing List", ondelete='cascade')
    error_msg = fields.Text(string="Error Message", help="Error message if sending fails.")
    
    hasmedia = fields.Boolean(string="Has Media", default=False)
    mime_type = fields.Char(string="MIME Type", default='text/plain')
   
    create_date = fields.Datetime(string="Received At", default=fields.Datetime.now, readonly=True) 
    file_media = fields.Binary(string="Media File")
            

    mailing_log_id = fields.Many2one(
        'infinys.whatsapp.mailing.log',
        string="Mailing Log",
        ondelete='set null',
        help="Reference to the mailing log for this sent message."
    )

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

    def action_mark_as_read(self):
        self.write({'state': 'read'})

    def action_mark_as_unread(self):
        self.write({'state': 'unread'})
    
