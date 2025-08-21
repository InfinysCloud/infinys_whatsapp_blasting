import logging
from odoo import api, fields, models
from odoo.exceptions import UserError
#from odoo.addons.phone_validation.tools import phone_validation

_logger = logging.getLogger(__name__)

class WhatsappContact(models.Model):
    _name = 'infinys.whatsapp.contact'
    _description = 'WhatsApp Contact'
    _rec_name = 'name'
    _order = 'name asc, company_name asc'

    name = fields.Char(string='Name', required=True, index=True)
    full_name = fields.Char(string='Full Name', compute='_compute_full_name', readonly=True)
    title_id = fields.Many2one('res.partner.title', string='Title')
    whatsapp_number = fields.Char(string='WhatsApp Number', required=True, index=True)
    company_name = fields.Char(string='Company Name')
    job_position = fields.Char(string='Job Position')
    description = fields.Char(string='Description')

    
    country_id = fields.Many2one('res.country', string='Country', 
                                 required=True,
                                 default=lambda self: self.env['res.country'].search([('code', '=', 'ID')], limit=1))
    
    email = fields.Char(string='Email')
    is_active = fields.Boolean(string='Active', default=True)
    is_manual = fields.Boolean(string='Manual Entry', default=True, help="Indicates if this contact was added manually.")
    tags_id = fields.Many2many('res.partner.category', string='Tags')
    last_sent_date = fields.Datetime(string='Last Sent Date', readonly=True)
    
    mailinglist_ids = fields.Many2many(
        comodel_name='infinys.whatsapp.mailinglist',
        relation='infinys_whatsapp_contact_mailinglist_rel',
        column1='contact_id',
        column2='mailinglist_id',
        string='Mailing Lists'
    )
    
    is_new_user = fields.Boolean(
        string='New User', 
        default=True,
        help="Indicates if this contact is a new user who has not been previously contacted."
    )

    total_messages_sent = fields.Integer(string='Messages Sent', default=0)
    total_received_messages = fields.Integer(string='Received Messages', default=0)
    
    incoming_message_ids = fields.One2many(
        comodel_name='infinys.whatsapp.incoming',
        inverse_name='contact_id', 
        string='Incoming Messages', 
        readonly=True
    )

    outgoing_message_ids = fields.One2many(
        comodel_name='infinys.whatsapp.sent',
        inverse_name='contact_id', 
        string='Outgoing Messages', 
        readonly=True
    )
    
    opt_out = fields.Boolean(
        string='Opt-Out', default=False,
        help="If checked, this contact will not receive any mass messages."
    )

    _sql_constraints = [
        ('whatsapp_number_uniq', 'unique (whatsapp_number)', "This WhatsApp number already exists!")
    ]

    @api.depends('whatsapp_number')
    def get_total_messages_sent(self):
       for record in self:
           record.total_messages_sent = 0 #self.env['infinys.whatsapp.message'].search_count([('from_contact_id', '=', record.id)])
           _logger.debug(f"Total messages sent for {record.name} ({record.whatsapp_number}): {record.total_messages_sent}")

    @api.depends('whatsapp_number')
    def get_total_received_messages(self):
       for record in self:
           record.total_received_messages = self.env['infinys.whatsapp.incoming'].search_count([('contact_id', '=', record.id)])
           _logger.debug(f"Total messages received for {record.name} ({record.whatsapp_number}): {record.total_received_messages}")

    @api.onchange('whatsapp_number')
    def _check_whatsapp_number(self):
        for record in self:
            if record.whatsapp_number :
                number_str = str(record.whatsapp_number)
                number_str = number_str.replace(" ", "").replace("-", "").replace("+", "")
                record.whatsapp_number = number_str.strip()

                record.company_name = record.company_name
                record.job_position = record.job_position
                record.description = record.description
            
    @api.depends('name', 'title_id')
    def _compute_full_name(self):
        for record in self:
            record.full_name = f"{record.title_id.shortcut} {record.name}" if record.title_id else record.name
