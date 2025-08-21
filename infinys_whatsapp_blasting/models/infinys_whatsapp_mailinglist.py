from odoo import api, fields, models
from odoo.exceptions import UserError
import logging  

_logger = logging.getLogger(__name__)

class WhatsappMailingList(models.Model):
    _name = 'infinys.whatsapp.mailinglist'
    _description = 'WhatsApp Mailing List'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char(string='Name', required=True, index=True)
    description = fields.Char(string='Description', help='A brief description of the mailing list.')
    
    total_contacts = fields.Integer(string='Total Contacts', compute='_compute_total_contacts', store=True)
    
    contact_ids = fields.Many2many(
        comodel_name='infinys.whatsapp.contact',
        relation='infinys_whatsapp_contact_mailinglist_rel',
        column1='mailinglist_id',
        column2='contact_id',
        string='Contact List',
        help='Select contacts to include in this mailing list.'
    )

    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string='Status', default='active', index=True)

    status_colored = fields.Html(string="Status", compute="_compute_status_colored", sanitize=False)

    _sql_constraints = [
            ('name_uniq', 'unique(name)', 'This Mailing List Name must be unique!')
        ]
    
    @api.depends('name', 'description','status', 'contact_ids')
    def _compute_total_contacts(self):
        for record in self:
            record.total_contacts = len(record.contact_ids)
    
    @api.depends('status')
    def _compute_status_colored(self):
        for rec in self:
            color = {
                'active': 'green',
                'inactive': 'red',
                'pending': 'orange',
            }.get(rec.status, 'black')
            label = dict(self._fields['status'].selection).get(rec.status, '')
            rec.status_colored = f'<span style="color:{color};">{label}</span>'
    
    #@api.onchange('contact_ids')
    #def _onchange_contact_ids(self):
    #     for record in self:
    #         for contact in record.contact_ids:
    #             self.env['infinys.whatsapp.contact'].browse(contact.id).write({'mailinglist_ids': [(4, record.id)]})
