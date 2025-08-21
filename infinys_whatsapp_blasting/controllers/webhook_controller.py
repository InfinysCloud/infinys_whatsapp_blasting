import re
import json
import logging
from curses import raw
from datetime import datetime
from odoo import http
from odoo.http import request
from ..utils import texttohtml_utils

_logger = logging.getLogger(__name__)

expected_token = "infinys_whatsapp_blasting.token" 

class WebhookController(http.Controller):
    
    @http.route('/isi/get_token', type='http', auth='public', methods=['GET'], csrf=False)
    def get_token(self, **kwargs):
        
        response  = ""
        token = request.env['ir.config_parameter'].sudo().get_param('infinys_whatsapp_blasting.token')

        if not token:
            _logger.error("Token not found")
            response = error_response(None, "Token not found")

        response= success_response(0, {
            "infinys_whatsapp_blasting_token": f"{token}"
            })
        _logger.info("Token retrieved successfully %s", response)

        return request.make_response(
            json.dumps(response),
            headers=[('Content-Type', 'application/json')]
        )
        
    
    @http.route('/isi/wa_incoming', type='json', auth='public', methods=['POST'], csrf=False)
    def whatsappincomming(self, **kwargs):
        _logger.info("Request data: %s", kwargs)

        raw = request.httprequest.data.decode('utf-8')
             
        try:
            expected_token = request.env['ir.config_parameter'].sudo().get_param('infinys_whatsapp_blasting.token')
            data = kwargs.get('data')
            _logger.info("Parsed data: %s --- Raw body: %s", data, raw)
            if not kwargs and not raw:
                _logger.error("No data received in the request")
                return {'status': 'error', 'message': 'No data received'}

            # If raw data is provided, parse it as JSON
            if raw:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as e:
                    _logger.error("JSON decode error: %s", e)
                    return {'status': 'error', 'message': 'Invalid JSON format'}
                        
            token = data.get('token')
            if token is None:
                return {'status': 'error', 'message': 'No token provided'}

            # Validate the token
            if token != expected_token:
                return {'status': 'error', 'message': 'Invalid token'}
                        
            message_data = data.get('messages', [])
            if not message_data:
                _logger.error("No messages found in the request")
                return {'status': 'error', 'message': 'No messages found'}
            
            _logger.info("Processing with messages %s", message_data)

            for message in message_data:
                _logger.info("Processing message: %s", message)

                action = message.get('action')
                if action not in ['create', 'update']:
                    _logger.error("Invalid action: %s", action)
                    return {'status': 'error', 'message': f'Invalid action: {action}'}
                
                records = []
                data = []
                rec_wahaconfig = {}
                if action == 'update':
                    _logger.info("Update whatsapp incomming")
                    id_record = message.get('id')
                    records = request.env['infinys.whatsapp.incoming'].sudo().search([('id', '=', id_record)], limit=1)
                   

                    if not records.exists():
                        return {"status": "error", "message": "Whatsapp Incoming not found"}
                    else:
                        _logger.info("Updating record: %s", records)
                                                
                        isNewUser = True if records.contact_id.is_new_user else False

                        substr_to_remove = '@'
                        from_number = records.from_number
                        to_number = records.to_number
                        rec_wahaconfig = request.env['infinys.whatsapp.config'].sudo().search([('whatsapp_number','=',to_number)], limit=1)

                        if substr_to_remove in from_number:
                            from_number = from_number.split(substr_to_remove, 1)[0]
                        if substr_to_remove in to_number:
                            to_number = to_number.split(substr_to_remove, 1)[0]

                        records.sudo().write({
                            'from_number': from_number,
                            'to_number': to_number,
                            'raw_data': records.raw_data,
                            'hasmedia': bool(message.get('media')),
                            'mime_type': message.get('type', 'text/plain'),
                            'body': records.raw_data,
                        })

                        # Panggil fungsi _onchange
                        records.sudo()._onchange_from_number()

                        incoming_records = request.env['infinys.whatsapp.incoming'].sudo().search_count([('from_number', '=', from_number)])

                        if incoming_records < 2:
                            _logger.info(f"Found {incoming_records} incoming records for from_number: {from_number}")
                            isNewUser = True

                        for rec in records:
                            data.append({
                                'id': rec.id,
                                'name': rec.name,
                                'from_number': rec.from_number,
                                'to_number': rec.to_number,
                                'hasmedia': rec.hasmedia,
                                'create_date': rec.create_date,
                                'contact_id': f'{rec.contact_id.id}',
                                'contact_id_name': rec.contact_id.name,
                                'whatsapp_config_id': f'{rec_wahaconfig.id}',
                                "isNewUser": isNewUser,
                                'welcome_message': rec_wahaconfig.welcome_message if rec_wahaconfig else ''
                            })

                elif action == 'create':
                    _logger.info("Creating whatsapp incomming")

                    substr_to_remove = '@'  
                    from_number = message.get('from', '')
                    to_number = message.get('to', '')
                    if substr_to_remove in from_number:
                        from_number = from_number.split(substr_to_remove, 1)[0]
                    if substr_to_remove in to_number:
                        to_number = to_number.split(substr_to_remove, 1)[0]
                    
                    rec_wahaconfig = request.env['infinys.whatsapp.config'].sudo().search([('whatsapp_number','=',to_number)], limit=1)
                    
                    records = request.env['infinys.whatsapp.incoming'].sudo().create({
                        'name': message.get('name'),
                        'from_number': from_number,
                        'to_number': to_number,
                        'raw_data': message.get('body'),
                        'hasmedia': bool(message.get('hasmedia')),
                        'mime_type': message.get('type', 'text/plain'),
                        'body': message.get('body', '')
                    })
                    _logger.info("Created record: %s", records.id)

                    records.sudo()._onchange_from_number()

                    for rec in records:
                            data.append({
                                'id': rec.id,
                                'name' : rec.name,
                                'from_number': rec.from_number,
                                'to_number': rec.to_number,
                                'hasmedia': rec.hasmedia,
                                'create_date': rec.create_date,
                                'contact_id': f'{rec.contact_id.id}',
                                'contact_id_name': rec.contact_id.name,
                                'whatsapp_config_id': f'{rec_wahaconfig.id}',
                                'welcome_message': rec_wahaconfig.welcome_message if rec_wahaconfig else ''
                            })

            _logger.info("All messages processed successfully")

            return success_response(records.id,data)

        except Exception as e:
            return error_response(e, "An error occurred while processing the request")
    
    @http.route('/isi/wa_config', type='json', auth='public', methods=['POST'], csrf=False)
    def whatsappconfig(self, **kwargs):
        _logger.info("Request data: %s", kwargs)

        raw = request.httprequest.data.decode('utf-8')
        _logger.info("RAW whatsappconfig: %s", raw)

        data = ""
        rec_wahaconfig = []

        try:
            expected_token = request.env['ir.config_parameter'].sudo().get_param('infinys_whatsapp_blasting.token')
            data = kwargs.get('data')
            _logger.info("Parsed data: %s --- Raw body: %s", data, raw)
            if not kwargs and not raw:
                _logger.error("No data received in the request")
                return {'status': 'error', 'message': 'No data received'}

            # If raw data is provided, parse it as JSON
            if raw:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as e:
                    _logger.error("JSON decode error: %s", e)
                    return {'status': 'error', 'message': 'Invalid JSON format'}
                        
            token = data.get('token')
            if token is None:
                return {'status': 'error', 'message': 'No token provided'}

            # Validate the token
            if token != expected_token:
                return {'status': 'error', 'message': 'Invalid token'}
                        
            whatsappnumber = data.get('whatsappnumber')
            if whatsappnumber is None:
                return {'status': 'error', 'message': 'No Whatsapp Number provided'}
            
            _logger.info("get_whatsappconfig with whatsappnumber: %s", whatsappnumber)
            rec_wahaconfig = request.env['infinys.whatsapp.config'].sudo().search([('whatsapp_number','=',whatsappnumber)], limit=1)
            
            if token and rec_wahaconfig:
                _logger.info("Found Whatsapp Config: %s", rec_wahaconfig.name)  

                for rec in rec_wahaconfig:
                    data = ({
                        'id': rec.id,
                        'name' : rec.name,
                        'provider': rec.provider,
                        'token': token,
                        'welcome_message': rec.welcome_message
                    })

                return success_response(rec_wahaconfig.id,data)
            
            else :
                return error_response(None,"No Data Whatsapp Config!!")
        
        except Exception as e:
            _logger.info(f"An error occurred while processing the request %s", e)
            return error_response(e, "An error occurred while processing the request")
    
    @http.route('/isi/cleanup_message', type='json', auth='public', methods=['POST'], csrf=False)
    def cleanup_message(self, **kwargs):
        raw = request.httprequest.data.decode('utf-8')
        _logger.info("RAW BODY: %s", raw)

        data = []
        message = ""
        try:
            expected_token = request.env['ir.config_parameter'].sudo().get_param('infinys_whatsapp_blasting.token')
            data = kwargs.get('data')
            _logger.info("Parsed data: %s --- Raw body: %s", data, raw)
            if not kwargs and not raw:
                _logger.error("No data received in the request")
                return {'status': 'error', 'message': 'No data received'}

            # If raw data is provided, parse it as JSON
            if raw:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as e:
                    _logger.error("JSON decode error: %s", e)
                    return {'status': 'error', 'message': 'Invalid JSON format'}
                        
            token = data.get('token')
            if token is None:
                return {'status': 'error', 'message': 'No token provided'}

            # Validate the token
            if token != expected_token:
                return {'status': 'error', 'message': 'Invalid token'}
                        
            message_data = data.get('messages', [])
            if not message_data:
                _logger.error("No messages found in the request")
                return {'status': 'error', 'message': 'No messages found'}
            
            _logger.info("Processing with messages %s", message_data)

            for message in message_data:
                _logger.info("Processing message: %s", message)

                text = message.get('text')
                if not text:
                    _logger.error("Empty Text: %s", text)
                    return {'status': 'error', 'message': f'Empty Text: {text}'}
                
                _texttohtml_utils = texttohtml_utils.TextToHtmlUtils()                   
                message = _texttohtml_utils.clean_html_for_whatsapp(text)

            data.append({
                        "text" :  f"{message}"
                    })
            return success_response(1,json.dumps(data))
        except Exception as e:
            return error_response(e, "An error occurred while processing the request")

    
    @http.route('/isi/create_logsent', type='json', auth='public', methods=['POST'], csrf=False)
    def create_logsent(self, **kwargs):
        _logger.info("create_logsent: %s", kwargs)

        raw = request.httprequest.data.decode('utf-8')
        _logger.info("RAW BODY: %s", raw)
     
        try:
            expected_token = request.env['ir.config_parameter'].sudo().get_param('infinys_whatsapp_blasting.token')
            data = kwargs.get('data')
            _logger.info("Parsed data: %s --- Raw body: %s", data, raw)
            if not kwargs and not raw:
                _logger.error("No data received in the request")
                return {'status': 'error', 'message': 'No data received'}

            # If raw data is provided, parse it as JSON
            if raw:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as e:
                    _logger.error("JSON decode error: %s", e)
                    return {'status': 'error', 'message': 'Invalid JSON format'}
                        
            token = data.get('token')
            if token is None:
                return {'status': 'error', 'message': 'No token provided'}

            # Validate the token
            if token != expected_token:
                return {'status': 'error', 'message': 'Invalid token'}
                        
            message_data = data.get('messages', [])
            if not message_data:
                _logger.error("No messages found in the request")
                return {'status': 'error', 'message': 'No messages found'}
            
            _logger.info("Prcessing with messages %s", message_data)

            for message in message_data:
                _logger.info("Processing message: %s", message)

                action = message.get('action')
                if action not in ['create','update']:
                    _logger.error("Invalid action: %s", action)
                    return {'status': 'error', 'message': f'Invalid action: {action}'}
                
                records = []
                data = []
                
                if action == 'update':

                    record_mailing = False
                    record_mailing_log = False

                    _logger.info("create whatsapp sent")
                    id_record = message.get('id')
                    config_id = message.get('config_id')
                    contact_id = message.get('contact_id')
                    mailing_id = message.get('mailing_id')
                    mailing_log_id = message.get('mailing_log_id')
                    
                    result_from = message.get('result_from')
                    from_number = message.get('from_number')
                    to_number = message.get('to_number')
                    body = message.get('body')
                    json_message = message.get('json_message', {})

                    record = request.env['infinys.whatsapp.sent'].sudo().search([('id', '=', id_record)], limit=1)
                    record_contact = request.env['infinys.whatsapp.contact'].sudo().search([('id', '=', contact_id)], limit=1)

                    if mailing_id:
                        record_mailing = request.env['infinys.whatsapp.mailing'].sudo().search([('id', '=', mailing_id)], limit=1)
                    
                    if mailing_log_id:
                        record_mailing_log = request.env['infinys.whatsapp.mailing.log'].sudo().search([('id', '=', mailing_log_id)], limit=1)

                    _logger.info("sent record: %s", record.id)
                    record.sudo().write({
                        "is_queued": False,
                        "error_msg" : ""
                    })

                    if record_mailing :
                        _logger.info("Updating mailing_id: %s", record_mailing.id)
                        record_mailing.sudo().write({
                                'sent_date': datetime.now(),
                                'sent_count': record_mailing.sent_count + 1,
                                'total_recipients': record_mailing.total_recipients + 1
                        })
                    
                    _logger.info("Updating contact_id: %s", record_contact.id)
                    record_contact.sudo().write({
                         'last_sent_date': datetime.now(),
                         'total_messages_sent': record_contact.total_messages_sent + 1
                    })

                    if record_mailing_log:      
                        _logger.info("Updating Mailing Log: %s", record_mailing_log.id)
                        record_mailing_log.sudo().write({
                                'sent_count': record_mailing_log.sent_count + 1,
                                'sent_date': datetime.now()
                        })

            return success_response(1, "Log sent successfully")
            
        except Exception as e:
            _logger.info("Error Sent Log : %s", e)
            return error_response(e, "An error occurred while processing the request")

    
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

def success_response(id,data):
    return {
        "jsonrpc": "2.0",
        "id": id,
        "status": "success",
        "result": data
    }