# -*- coding: utf-8 -*-

{
    "name": "Infinys Whatsapp Blasting",
    "summary": """
        Manage & Track Whatsapp Marketing Campaigns, Lists, and Contacts 
    """,
    "description": """
        Our Whatsapp Blasting / Broadcasting Messaging Application is a powerful communication tool designed to send personalized or bulk messages to multiple WhatsApp contacts directly through a user-friendly dashboard. Ideal for businesses, marketers, and customer support teams, this tool leverages the WhatsApp Web protocol to automate message delivery while maintaining human-like interactions.

        Whatsapp Blasting Distribution is a system designed to automate and streamline the process of sending bulk messages to a large list of WhatsApp contacts. It is commonly used for marketing campaigns, announcements, customer engagement, alerts, and internal communications. 
        Key Features:
        - Bulk Messaging: Send messages to multiple contacts at once.
        - Scheduling: Plan and schedule messages for optimal delivery times.
        - Record all incoming and outgoing messages for compliance and analysis.
        - Convert all incoming messages to database contact
        - Analytics: Track message delivery and engagement metrics (not this in community edition).
    """,
    "author": "Infinys System Indonesia",
    "website": "https://www.infinyscloud.com/platform/odoo/",
    "category": "Marketing/Email Marketing",
    "version": "1.0.0",
    "license": "AGPL-3",
    "live_test_url": "https://odoo-ce.atisicloud.com/",
    "icon": "/infinys_whatsapp_blasting/static/description/icon.png",
    # any module necessary for this one to work correctly
    "depends": ["base", "mail", "mass_mailing"],
    #'external_dependencies': {'python': ['pyshorteners']},
    # always loaded
    "data": [
        "views/init.xml",
        "security/ir.model.access.csv",
        "views/infinys_whatsapp_config_views.xml",
        "views/infinys_whatsapp_contact_views.xml",
        "views/infinys_whatsapp_mailinglist_views.xml",
        "views/infinys_whatsapp_mailing_views.xml",
        "views/infinys_whatsapp_incoming_views.xml",
        "views/infinys_whatsapp_sent_views.xml",
        "views/infinys_whatsapp_mailing_log_views.xml",
        "views/whatsapp_mass_menu_views.xml",
        "data/ir_cron_whatsapp_send.xml",
        "data/ir_config_parameter.xml",
    ],
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
