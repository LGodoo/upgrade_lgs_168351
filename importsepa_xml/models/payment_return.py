# © 2016 Carlos Dauden <carlos.dauden@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from datetime import datetime

from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class PaymentReturnLine(models.Model):
    _inherit = "sdd.mandate"
    def _compute_nameseq(self):
        total2 = 0
        name = self.env['ir.sequence'].next_by_code(
            'self.mandate')
        i = 17
        for n in name:
            total = (i * int(n))
            total2 = total + total2

            i = i - 1
        name = (str(name) + str(total2 % 10))[-13:]
        return name

    name = fields.Char(string='Identifier', required=True, readonly=True, states={'draft':[('readonly',False)]}, help="The unique identifier of this mandate.", default=_compute_nameseq, copy=False)

