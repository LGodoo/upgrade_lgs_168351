# © 2016 Carlos Dauden <carlos.dauden@tecnativa.com>
# © 2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2018 Tecnativa - Luis M. Ontalba
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
from io import BytesIO
from zipfile import ZipFile, BadZipfile  # BadZipFile in Python >= 3.2

from odoo import _, api, models, fields
from odoo.exceptions import Warning as UserError
import logging
_logger = logging.getLogger(__name__)
from .base_parser import BaseParser
from .pain_parser import PainParser



class PaymentSepaImport(models.TransientModel):
    _name = 'payment.sepa.import'
    _description = 'Import Payment Sepa'
    _inherit = 'mail.thread'

    data_file = fields.Binary(
        'SEPA Payment File', required=True,
        help='XML file')

    def import_file(self):
        """Process the file chosen in the wizard"""
        self.ensure_one()
        data_file = base64.b64decode(self.data_file)
        self.with_context(active_id=self.id)._import_file(data_file)


    @api.model
    def _parse_all_files(self, data_file):
        """Parse one or multiple files from zip-file.

        :param data_file: Decoded raw content of the file
        :return: List of payment returns dictionaries for further processing.
        """
        payment_return_raw_list = []
        files = [data_file]

        try:
            with ZipFile(BytesIO(data_file), 'r') as archive:
                files = [
                    archive.read(filename) for filename in archive.namelist()
                    if not filename.endswith('/')
                    ]
        except BadZipfile:
            pass
        # Parse the file(s)
        for import_file in files:


            vals = self._parse_file(import_file)

            if isinstance(vals, list):
                payment_return_raw_list += vals
            else:
                payment_return_raw_list.append(vals)
        return payment_return_raw_list

    @api.model
    def _import_file(self, data_file):
        payment_return_raw_list = self._parse_all_files(data_file)

        # self._check_parsed_data(payment_return_raw_list)
        # Import all payment returns:

        for payret_vals in payment_return_raw_list:
            _logger.error("payret_vals: %s", payret_vals)

            if len(payret_vals['recordid']) > 0:
                for i in range(0, len(payret_vals['recordid'])):
                    name = (payret_vals['recordid'][i]) or ''
                    if name:
                        payment_ref = self.env['account.payment'].search([['name', '=', name]])

                        for record in payment_ref:
                            if (payret_vals['errorcode'][i]) != '' and (payret_vals['status'][i]) != 'ACCP':
                                msg = 'Reference: %s ' % (payret_vals['recordid'][i]) + 'Date: %s \n' % (
                                payret_vals['date'][i]) + 'SEPA: Declined with error code: %s, Error description: %s \n' % (
                                          (payret_vals['errorcode'][i]), (payret_vals['textcode'][i]))
                                message = ({

                                     'email_from': self.env.user.partner_id.email,
                                     'author_id': self.env.user.partner_id.id,
                                })

                                record.message_post(body= msg, subject= "Declined SEPA payment for: " + payret_vals['recordid'][i], message_type="notification", **message)

                            else:
                                msg = 'Reference: %s ' % (payret_vals['recordid'][i]) + 'Date: %s \n' % (
                                payret_vals['date'][i]) + 'SEPA: Accepted amount: %s \n' % \
                                      (payret_vals['amount'][i])

                                message = ({

                                    'email_from': self.env.user.partner_id.email,
                                    'author_id': self.env.user.partner_id.id,
                                })
                                record.message_post(body= msg, subject= "Accepted SEPA payment for: " + payret_vals['recordid'][i], message_type="notification", **message)

            if len(payret_vals['status']) > 0:
                for i in range(0, len(payret_vals['msgid'])):
                    msgid = (payret_vals['msgid'][i]) or ''
                    if msgid != '' and payret_vals['status'][i] == 'ACCP':
                        payment_ref_id = self.env['account.payment'].search([['msg_id', '=', msgid]])
                        _logger.error(payment_ref_id)
                        for record in payment_ref_id:
                            msg = 'SEPA: ACCP'
                            message = ({

                                'email_from': self.env.user.partner_id.email,
                                'author_id': self.env.user.partner_id.id,
                            })

                            record.message_post(body= msg, subject= "Accepted SEPA payment: ", message_type="notification", **message)
                    elif msgid != '' and payret_vals['status'][i] == 'RJCT':
                        payment_ref_id = self.env['account.payment'].search([['msg_id', '=', msgid]])
                        _logger.error(payment_ref_id)
                        for record in payment_ref_id:
                            msg = 'SEPA: RJCT'
                            message = ({

                                'email_from': self.env.user.partner_id.email,
                                'author_id': self.env.user.partner_id.id,
                            })

                            record.message_post(body= msg, subject= "Rejected SEPA payment: ", message_type="notification", **message)
                                  





    @api.model
    def _parse_file(self, data_file):
        """ Each module adding a file support must extends this method. It
        processes the file if it can, returns super otherwise, resulting in a
        chain of responsability.
        This method parses the given file and returns the data required by
        the bank payment return import process, as specified below.
        - bank payment returns data: list of dict containing (optional
                                items marked by o) :
            -o account number: string (e.g: 'BE1234567890')
                The number of the bank account which the payment return
                belongs to
            - 'name': string (e.g: '000000123')
            - 'date': date (e.g: 2013-06-26)
            - 'transactions': list of dict containing :
                - 'amount': float
                - 'unique_import_id': string
                -o 'concept': string
                -o 'reason_code': string
                -o 'reason': string
                -o 'partner_name': string
                -o 'reference': string
        """
        parser = PainParser()
        try:
            return parser.parse(data_file)
        except Exception:
            raise UserError(_(
                'Selected file could not be parsed.\n'
                'Make sure you selected either an XML file, or a ZIP folder containing XML files'
            ))

    @api.model
    def _check_parsed_data(self, payment_returns):
        """ Basic and structural verifications """
        if not payment_returns:
            raise UserError(_(
                'This file doesn\'t contain any relevant information.'))
        for payret_vals in payment_returns:
            if payret_vals.get('transactions'):
                return
        # If we get here, no transaction was found:
        raise UserError(_('This file doesn\'t contain any transaction.'))







