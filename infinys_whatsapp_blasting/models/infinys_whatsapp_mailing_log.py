import logging
import re
import json
from odoo import models, fields, api, tools
import werkzeug.urls
from odoo.tools import html_sanitize, html_escape
from odoo.tools.safe_eval import safe_eval
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError
import requests
from ..utils import waha_utils
from ..utils import texttohtml_utils    
from ..utils import n8n_utils

_logger = logging.getLogger(__name__)
_waha_utils = waha_utils
_texttohtml_utils = texttohtml_utils    
_n8n_utils = n8n_utils

class WhatsappMailingLog(models.Model):
    _name = 'infinys.whatsapp.mailing.log'
    _description = 'WhatsApp Mass Mailing Log   '
    _order = 'sent_date desc'

    name = fields.Char(string='Subject')
    mailing_id = fields.Many2one(
        'infinys.whatsapp.mailing', 
        string='WhatsApp Mailing'
    )

    mailing_list_id = fields.Many2one(
        'infinys.whatsapp.mailinglist', 
        string='Mailing List'
        )

    
    mailing_sent_ids = fields.One2many(
        comodel_name='infinys.whatsapp.sent',
        inverse_name='mailing_log_id', 
        string='Mailing Sent Lists', 
        readonly=True
    )
    
    total_contact = fields.Integer(string="Total Contacts", default=0)
    sent_count = fields.Integer(string="Total Sent", default=0)
    state = fields.Char(string='Status', default='draft', copy=False)
    error_msg = fields.Char(string="Error Message")
    sent_date = fields.Datetime(string='Sent Date')

