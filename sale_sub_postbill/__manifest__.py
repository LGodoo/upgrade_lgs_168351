# -*- coding: utf-8 -*-
{
    'name': "Post Billing",
    'summary': "Adds post billing functionallity to sale_subscriptions. Adds scheduled action to import PBX transacitons.",
    'description': """
    """,
    'author': "cm, gg",
    'version': '1.0.0',
    'license': 'LGPL-3',
    'depends': ['sale_subscription','sale','account_accountant'],
    'data': [
        'views/postbill_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
