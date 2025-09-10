import logging
import re
import json
from odoo import models, fields, api, tools
import werkzeug.urls
import pytz
import time
from datetime import datetime, timedelta
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

class WhatsappMailing(models.Model):
    _name = 'infinys.whatsapp.mailing'
    _description = 'WhatsApp Mass Messaging'
    _order = 'id desc, state_idx asc, name asc'

    name = fields.Char(string='Subject',  required=True, store=True, index=True)
    error_msg = fields.Char(string="Error Message", default="")
    whatsapp_config_id = fields.Many2one(
        'infinys.whatsapp.config', 
        string='Whatsapp Account', 
        domain=[('active', '=', True)], 
        required=True)
    
    responsible_id = fields.Many2one(
        'res.users', 
        string='Responsible', 
        default=lambda self: self.env.user, 
    )

    mailing_list_id = fields.Many2one(
        'infinys.whatsapp.mailinglist', 
        string='Mailing List'
    )

    sent_date = fields.Datetime(string='Sent Date')
        
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submit'),
        ('done', 'Done'),
        ('failed', 'Partial Failure'),
        ('canceled', 'Cancelled')
    ], string='Status', default='draft', required=True, copy=False)

    recipients = fields.Selection([
        ('mailinglist', 'Mailing List'),
        ('mailinglistcontact',  'Mailing List Contact'),
    ], string="Recipients", default='mailinglist')
    
    message = fields.Html(string="Message",  sanitize=False)
    is_body_empty = fields.Boolean(string="Is Body Empty", compute="_compute_statistics", store=True, default=False)
    header_type = fields.Selection([
        ('none', 'None'),
        ('text', 'Text'),
       ], string="Header Type", default='none')
    
    header_text = fields.Char(string="Template Header Text", size=60)
    #header_attachment_ids = fields.Many2many(
    #    'ir.attachment', string="Template Static Header",
    #    copy=False)  # keep False to avoid linking attachments; we have to copy them instead
    footer_text = fields.Char(string="Footer Message", size=150)

    # Statistics are now computed from lines
    total_recipients = fields.Integer(string="Total")
    sent_count = fields.Integer(string="Sent")
    failed_count = fields.Integer(string="Failed")
    schedule_date = fields.Datetime(string='Schedule Date', default=fields.Datetime.now, required=True, help="If set, the mailing will be sent on this date/time.", store=True)
    create_year = fields.Integer(string="Year", compute="_compute_create_year", store=True)

    state_idx = fields.Integer(
        string='State Index',
        compute='_compute_state_idx',
        store=True,
        index=True  
    )

    contact_ids = fields.Many2many(
        'infinys.whatsapp.contact',
        string='Contact List',
        help='Select contacts to include in this mailing list.'
    )

    _sql_constraints = {
        ('name_uniq', 'unique(name)', 'The name must be unique'),
    }

    @api.constrains('schedule_date')
    def _check_schedule_date(self):
        _logger.info("Checking schedule date constraints")
        sts = True
        for rec in self:
            _logger.info(f"Schedule date: {rec.schedule_date}")
            _logger.info(f"State: {rec.state}")
            if (rec.state in ['submit','failed']):
                if rec.schedule_date and rec.schedule_date <= fields.Datetime.now(): 
                    raise UserError("Schedule date must be greater than today")
        return sts

    def _compute_statistics(self):
        for mailing in self:
            mailing.is_body_empty = tools.is_html_empty(mailing.message)

    @api.depends('create_date')
    def _compute_create_year(self):
        for rec in self:
            rec.create_year = rec.create_date.year if rec.create_date else False

    def btn_submit(self):
        _logger.info("btn_submit")

        if (self.schedule_date):
            self.state = "submit"
            if not self._check_schedule_date():
                self.state = "draft"
        else:
            raise UserError("Schedule cannot be empty if you want to send now, please set it to today")   

        return ""
    
    def btn_back_draft(self):
        _logger.info("btn_back_draft")
        self._compute_state_idx()
        self.state = "draft"
        return True

    def btn_test(self):
        _logger.info("btn_test_api")

        message = ""
        status = 'success'
        text_message = self.set_wa_messsage (self, "Testing Whatsapp", "Testing Whatsapp")
        _logger.info(text_message)
        
        data = waha_utils.test_send_message(self, 
                                              self.whatsapp_config_id.id, 
                                              self.whatsapp_config_id.whatsapp_number, 
                                              self.whatsapp_config_id.whatsapp_number, 
                                              text_message
                                            )
        
        if (data.get('status') == 'success'):
            message += "Test Whatsapp successful, to Whatsapp Number : +" + self.whatsapp_config_id.whatsapp_number
        else:
            status = 'warning'
            message += "Connection failed, to Whatsapp Number : +" + self.whatsapp_config_id.whatsapp_number + f" Error: {data.get('message', 'Unknown error')}"

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
    
    def set_wa_messsage(self, mailing_record, to_contact_name, to_contact_fullname):
        
        mailing_record = self.env["infinys.whatsapp.mailing"].browse(mailing_record.id)
        text_message = mailing_record.message

        contact_variable  = to_contact_name
        
        subject_variable = mailing_record.name
        milingList_text = mailing_record.mailing_list_id.name
        header_text = mailing_record.header_text
        footer_text = mailing_record.footer_text
       
        if header_text:
            header_text = _texttohtml_utils.safe_replace(header_text, "{{subject}}", subject_variable)
            header_text = _texttohtml_utils.safe_replace(header_text, "{{contact.name}}", contact_variable)
            header_text = _texttohtml_utils.safe_replace(header_text, "{{contact.full_name}}", to_contact_fullname)
            header_text = _texttohtml_utils.safe_replace(header_text, "{{mailingList.name}}", milingList_text)
        else:
            header_text = ""    

        if footer_text:
            footer_text = _texttohtml_utils.safe_replace(footer_text, "{{subject}}", subject_variable)
            footer_text = _texttohtml_utils.safe_replace(footer_text, "{{contact.name}}", contact_variable)
            footer_text = _texttohtml_utils.safe_replace(footer_text, "{{contact.full_name}}", to_contact_fullname)
            footer_text = _texttohtml_utils.safe_replace(footer_text, "{{mailingList.name}}", milingList_text)
        else:
            footer_text = ""

        _logger.info(f"text_message: {text_message}")
        if text_message:
            text_message = _texttohtml_utils.safe_replace(text_message, "{{subject}}", subject_variable)
            text_message = _texttohtml_utils.safe_replace(text_message, "{{contact.name}}", contact_variable)
            text_message = _texttohtml_utils.safe_replace(text_message, "{{contact.full_name}}", to_contact_fullname)
            text_message = _texttohtml_utils.safe_replace(text_message, "{{mailingList.name}}", milingList_text)
        
        ##bold
        text_message = f"*{header_text}*\n" + text_message if len(header_text) > 0 else text_message 
        
        #italic
        text_message = f"{text_message}\n" + f"_{footer_text}_" if len(footer_text) > 0 else text_message

        text_message = _texttohtml_utils.clean_html_for_whatsapp(text_message)
        
        return text_message  

    def btn_send_now(self):
        _logger.info("btn_send_now")
        record = self

        if self._check_schedule_date():
            contact_ids = []
                        
            if record.recipients == 'mailinglistcontact':
                contact_ids = record.contact_ids
            else:
                if (not record.mailing_list_id):
                    raise UserError("No selected Mailing List.")
                
                contact_ids = record.mailing_list_id.contact_ids.search([('is_active', '=', True), ['mailinglist_ids', 'in', record.mailing_list_id.id]])
            
            total_contact = len(contact_ids) if contact_ids else 0
            self.total_recipients = total_contact

            _logger.info(f"btn_send_now total contact: {total_contact}")
            
            if (self.total_recipients <= 0):
                raise UserError("No active contacts found !!.")

            status =  self.mailing_queue(record,contact_ids, 'send now') 
            message = f"Processing message from {self.whatsapp_config_id.whatsapp_number} with total recipients: {total_contact} on queue"
            _logger.info(f"Sending message to {self.whatsapp_config_id.whatsapp_number} ")
            
            return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': "Sending Message Successful",
                        'message': message,
                        'type': 'success',  # 'success' for green, 'warning' for orange
                        'sticky': False,  # Keep the notification until the user clicks it away
                    }
            }
        
        return False

    def mailing_queue(self,mailing_record, contact_ids, state):
               
        try:
            rec_mailing_log = []
            mailing_record = self.env["infinys.whatsapp.mailing"].browse(mailing_record.id)

            total_contact = len(contact_ids)

            _logger.info(f"mailing_record: {mailing_record.id}")
            _logger.info(f"total contact: {total_contact}")

            if total_contact > 0:
                
                rec_mailing_log = self.env["infinys.whatsapp.mailing.log"].create({
                    'name': mailing_record.name,
                    'mailing_id': mailing_record.id,
                    'mailing_list_id': mailing_record.mailing_list_id.id if mailing_record.mailing_list_id else 0,
                    'total_contact': total_contact,
                    'state': state,
                    'sent_date': fields.Datetime.now()
                })

                self.set_webhook_message(mailing_record, rec_mailing_log, contact_ids)

                #for contact in contact_ids:
                #    _logger.info(f"Processing contact: {contact.name} with WhatsApp number: {contact.whatsapp_number} and mailinglistid: {contact.mailinglist_ids.ids}")
                #    contact_data = ""
                #    payload = ""

                #    if not contact.whatsapp_number:
                #        _logger.warning(f"Contact {contact.whatsapp_number} does not have a WhatsApp number.")
                #        continue

                #    if not contact.is_active:
                        #_logger.warning(f"Contact {contact.name} is not active.")
                #        continue

                #    text_message = ""
                #    text_message = self.set_wa_messsage(mailing_record,contact.name, contact.full_name)

                #    if text_message:

                #        contact_data = ({
                #            "contact_id" : f"{contact.id}", 
                #            "contact_name" : f"{contact.name}",
                #            "contact_whatsapp" : f"{contact.whatsapp_number}",
                #            "message" : f"{text_message}",
                #            })
                        
                #        payload = { 
                #            "jsonrpc": "2.0",
                #            "wa_config_id": f"{mailing_record.whatsapp_config_id.id}",
                #            "wa_config_name": f"{mailing_record.whatsapp_config_id.name}",
                #            "mailing_id": f"{mailing_record.id}",
                #            "mailing_list": f"{mailing_record.mailing_list_id.id}",
                #            "mailing_list_name": f"{mailing_record.mailing_list_id.name}",
                #            "mailing_log_id": f"{rec_mailing_log.id}",
                #            "session" : "default",
                #            "reply_to": f"{mailing_record.whatsapp_config_id.whatsapp_number}",
                #            "contact": f"{json.dumps(contact_data)}"
                #        }

                         #create record infinys whatsapp sent
                #       records = self.env['infinys.whatsapp.sent'].create({
                #            'name': contact.name,
                #            'config_id' : mailing_record.whatsapp_config_id.id,
                #            'mailing_id': mailing_record.id,
                #            'mailing_list_id': mailing_record.mailing_list_id.id,
                #            'mailing_log_id': rec_mailing_log.id,
                #            'contact_id': contact.id,
                #            'from_number': contact.whatsapp_number,
                #            'to_number': mailing_record.whatsapp_config_id.whatsapp_number,
                #            'body': text_message,
                #            'json_message': json.dumps(payload),
                #            'json_contact' : json.dumps(contact_data),
                #            'mime_type': 'text/plain',
                #            'hasmedia' : False,
                #            'is_queued' : True
                #        })

                mailing_record.sent_date = fields.Datetime.now()
                mailing_record.error_msg = "" 

                time.sleep(10)
                
                if (state=="submit"):
                    mailing_record.state = "done"

        except Exception as e:
            _logger.error(f"Error in btn_send_now: {e}")
            mailing_record.error_msg = str(e)
            mailing_record.state = "failed"
            raise UserError(f"Error in Send_now: {e}")
        return True

    def set_webhook_message(self, mailing_record, rec_mailing_log, contact_ids):
        _logger.info("set_webhook_message")
        sts = False

        try:

            for contact in contact_ids:
                _logger.info(f"Processing contact: {contact.name} with WhatsApp number: {contact.whatsapp_number} and mailinglistid: {contact.mailinglist_ids.ids}")
                contact_data = ""
                payload = ""

                if not contact.whatsapp_number:
                    _logger.warning(f"Contact {contact.whatsapp_number} does not have a WhatsApp number.")
                    continue

                if not contact.is_active:
                    #_logger.warning(f"Contact {contact.name} is not active.")
                    continue

                text_message = ""
                text_message = self.set_wa_messsage(mailing_record,contact.name, contact.full_name)

                if text_message:

                    contact_data = ({
                        "contact_id" : f"{contact.id}", 
                        "contact_name" : f"{contact.name}",
                        "contact_whatsapp" : f"{contact.whatsapp_number}",
                        "message" : f"{text_message}",
                        })
                    
                    payload = { 
                        "jsonrpc": "2.0",
                        "wa_config_id": f"{mailing_record.whatsapp_config_id.id}",
                        "wa_config_name": f"{mailing_record.whatsapp_config_id.name}",
                        "mailing_id": f"{mailing_record.id}",
                        "mailing_list": f"{mailing_record.mailing_list_id.id}",
                        "mailing_list_name": f"{mailing_record.mailing_list_id.name}",
                        "mailing_log_id": f"{rec_mailing_log.id}",
                        "session" : "default",
                        "reply_to": f"{mailing_record.whatsapp_config_id.whatsapp_number}",
                        "contact": f"{json.dumps(contact_data)}"
                    }

                    #create record infinys whatsapp sent
                    records = self.env['infinys.whatsapp.sent'].create({
                        'name': contact.name,
                        'config_id' : mailing_record.whatsapp_config_id.id,
                        'mailing_id': mailing_record.id,
                        'mailing_list_id': mailing_record.mailing_list_id.id,
                        'mailing_log_id': rec_mailing_log.id,
                        'contact_id': contact.id,
                        'from_number': contact.whatsapp_number,
                        'to_number': mailing_record.whatsapp_config_id.whatsapp_number,
                        'body': text_message,
                        'json_message': json.dumps(payload),
                        'json_contact' : json.dumps(contact_data),
                        'mime_type': 'text/plain',
                        'hasmedia' : False,
                        'is_queued' : True
                    })
                sts = True
        except Exception as e:
            sts = False
            raise UserError(f"Error in set_webhook_message: {e}")
        return sts

    def _send_whatsapp_blasting(self):
        _logger.info("_send_whatsapp_blasting")
        now = fields.Datetime.now()

        #You can add a small tolerance window if cron runs every minute
        one_minute_ago = now - timedelta(minutes=1)
        one_minute_after = now + timedelta(minutes=1)

        _logger.info("now: %s", now)
        _logger.info("one_minute_ago: %s", one_minute_ago)
        _logger.info("one_minute_after: %s", one_minute_after)  

        records = self.sudo().search([('state', '=', 'submit'),
                                        ('schedule_date', '>=', one_minute_ago),
                                        ('schedule_date', '<=', one_minute_after)
                                    ])

        if records:
            _logger.info("Found records to process: %s", records)
            for record in records:
                _logger.info(" Record Process : %s", record, " state : %s", record.state)
                self.mailing_queue(record,record.contact_ids,record.state)
                
            
        return True
    
    def _execute_enqueue(self):
        _logger.info("__execute_queue")
        
        payload = {}
        contact_data={}
        records = self.env['infinys.whatsapp.sent'].search([('is_queued', '=', True)],limit=10)
        
        for record in records:
            try:
                records.error_msg = ""

                contact_data = ({
                   "sent_id" : f"{record.id}",
                   "contact_id" : f"{record.contact_id.id}", 
                   "contact_name" : f"{record.name}",
                   "contact_whatsapp" : f"{record.from_number}",
                    "message" : f"{record.body}",
                })
                _logger.info(f"Sending contact_data: {contact_data}")

                payload = {
                    "jsonrpc": "2.0",
                    "wa_config_id": f"{record.config_id.id}",
                    "wa_config_name": f"{record.config_id.name}",
                    "mailing_id": f"{record.mailing_id.id}" if record.mailing_id else "0",
                    "mailing_list": f"{record.mailing_list_id.id}" if record.mailing_list_id else "0",
                    "mailing_list_name": f"{record.mailing_list_id.name}" if record.mailing_list_id else "",
                    "mailing_log_id": f"{record.mailing_log_id.id}" if record.mailing_log_id else "0",
                    "session" : "default",
                    "reply_to": f"{record.to_number}",
                    "contact": f"{json.dumps(contact_data)}"
                }

                _logger.info(f"Sending payload: {payload}")
                            
                _n8n_utils = n8n_utils.send_message(records,
                                    records.config_id.webhook_url,
                                    records.config_id.authentication_user,
                                    records.config_id.authentication_password,
                                    payload)
                time.sleep(3)  # Simulate processing time

            except Exception as e:
                _logger.error(f"Error in _execute_enqueue: {e}")
                record.error_msg = f"Error in _execute_enqueue: {e}"
                record.is_queued = True

        return True
    
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default.update({
            'name': f"{self.name} (Copy)-{self.id}",
            'state': 'draft',
        })
        return super(WhatsappMailing, self).copy(default=default)

    def btn_cancel(self):
        self.state = "canceled"
    
    @api.depends('state', 'state_idx')
    def _compute_state_idx(self):
        self.state_idx=1
        for record in self:
            idx=1
            match record.state:
                case 'draft':
                    idx = 1
                case 'submit':
                    idx = 2
                case 'done':
                    idx = 3
                case 'failed':
                    idx = 4
                case 'canceled':
                    idx = 5
            record.state_idx = idx
         

            