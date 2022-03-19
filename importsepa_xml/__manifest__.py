

{
    'name': 'Import SEPA XMLs',
    'author': 'cm, gg',
    'description': 'A module that allows the importing of SEPA xmls',
    'data': [
        'security/ir.model.access.csv',
        'wizard/payment_sepa_import_view.xml',
        'data/sequence.xml',
    ],
    'depends': [
        'account_sepa_direct_debit',
        'account_payment',
        'account_batch_payment',
        'mail'

    ],
    'license': 'LGPL-3',
    'installable': True,
}
