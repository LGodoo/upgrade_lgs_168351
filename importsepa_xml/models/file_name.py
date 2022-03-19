from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
import base64
import random
import re
import time
from lxml import etree

from odoo.tools.float_utils import float_repr
from odoo.tools.xml_utils import create_xml_node, create_xml_node_chain
import logging
_logger = logging.getLogger(__name__)

class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'
    
    def _generate_export_file(self):
        if self.payment_method_code == 'sdd':
            
            # Constrains on models ensure all the payments can generate SDD data before
            # calling this method, so we make no further check of their content here

            company = self.env.company
            count = self.env['account.batch.payment'].search_count([('date', '=', datetime.now()),('payment_method_id','=','SEPA Direct Debit')])
            filename = 'PAIN008' +'-0219-'+ datetime.now().strftime('%Y%m%d')+ '-' + str(count) + '.xml'
            
            return {
                'filename': filename,
                'file': base64.encodestring(self.payment_ids.generate_xml(company, self.sdd_required_collection_date, self.sdd_batch_booking)),
                
            }

        return super(AccountBatchPayment, self)._generate_export_file()
