# Copyright 2016 Carlos Dauden <carlos.dauden@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import api, models
from .pain_parser import PainParser

_logger = logging.getLogger(__name__)


class PaymentSepaImport(models.TransientModel):
    _name = 'payment.sepa.import'
    _description = 'Import Payment Sepa'

    @api.model
    def _parse_file(self, data_file):
        """Parse a PAIN.002.001.03 XML file."""
        _logger.error('_parse_file:')

        parser = PainParser()
        try:
            _logger.error("Try parsing with Direct Debit Unpaid Report.")
            return parser.parse(data_file)
        except ValueError:
            # Not a valid file, returning super will call next candidate:
            _logger.error("Payment return file was not a Direct Debit Unpaid "
                          "Report file.",
                          exc_info=True)
            return super(PaymentSepaImport, self)._parse_file(data_file)
