from odoo import models, fields

class WhatsappMailingRecipient(models.Model):
    _name = 'infinys.whatsapp.mailing.recipient'
    _description = 'Recipient Line for WhatsApp Mailing'
    _order = 'id'

    mailing_id = fields.Many2one('infinys.whatsapp.mailing', string="Mailing", required=True, ondelete='cascade')
    contact_id = fields.Many2one('infinys.whatsapp.contact', string="Contact", required=True, ondelete='cascade')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ], string='Status', default='draft', required=True, readonly=True)

    failure_reason = fields.Text(string="Failure Reason", readonly=True)

    _sql_constraints = [
        ('mailing_contact_uniq', 'unique (mailing_id, contact_id)', "This contact is already in the recipient list.")
    ]

