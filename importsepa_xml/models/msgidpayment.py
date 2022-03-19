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
from odoo.addons.account_batch_payment.models.account_payment import AccountPayment as AccountPaymentOrigin
import logging
_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    msg_id = fields.Text(string='msg_id', default=False, copy=False)
    
    def _sdd_xml_gen_header(self, company_id, CstmrDrctDbtInitn):
        """ Generates the header of the SDD XML file.
        """
        GrpHdr = create_xml_node(CstmrDrctDbtInitn, 'GrpHdr')
        msgid = create_xml_node(GrpHdr, 'MsgId',
                        str(time.time()))  # Using time makes sure the identifier is unique in an easy way
        create_xml_node(GrpHdr, 'CreDtTm', datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
        create_xml_node(GrpHdr, 'NbOfTxs', str(len(self)))
        create_xml_node(GrpHdr, 'CtrlSum', float_repr(sum(x.amount for x in self),
                                                      precision_digits=2))  # This sum ignores the currency, it is used as a checksum (see SEPA rulebook)
        InitgPty = create_xml_node(GrpHdr, 'InitgPty')
        create_xml_node(InitgPty, 'Nm', self.split_node(company_id.name, 70)[0])
        create_xml_node_chain(InitgPty, ['Id', 'OrgId', 'Othr', 'Id'], company_id.sdd_creditor_identifier)
        for record in self:
            _logger.error("msgid: %s", msgid.text)
            record.msg_id = msgid.text
                

    def sdd_xml_gen_payment(self,company_id, partner, end2end_name, PmtInf):
        """ Appends to a SDD XML file being generated all the data related to the
        payments of a given partner.
        """
        #The two following conditions should never execute.
        #They are here to be sure future modifications won't ever break everything.
        if self.company_id != company_id:
            raise UserError(_("Trying to generate a Direct Debit XML file containing payments from another company than that file's creditor."))

        if self.payment_method_id.code != 'sdd':
            raise UserError(_("Trying to generate a Direct Debit XML for payments coming from another payment method than SEPA Direct Debit."))

        if not self.sdd_mandate_id:
            raise UserError(_("The payment must be linked to a SEPA Direct Debit mandate in order to generate a Direct Debit XML."))

        if self.sdd_mandate_id.state == 'revoked':
            raise UserError(_("The SEPA Direct Debit mandate associated to the payment has been revoked and cannot be used anymore."))

        DrctDbtTxInf = create_xml_node_chain(PmtInf, ['DrctDbtTxInf','PmtId','EndToEndId'], end2end_name)[0]

        InstdAmt = create_xml_node(DrctDbtTxInf, 'InstdAmt', float_repr(self.amount, precision_digits=2))
        InstdAmt.attrib['Ccy'] = self.currency_id.name

        MndtRltdInf = create_xml_node_chain(DrctDbtTxInf, ['DrctDbtTx','MndtRltdInf','MndtId'], self.sdd_mandate_id.name)[-2]
        create_xml_node(MndtRltdInf, 'DtOfSgntr', fields.Date.to_string(self.sdd_mandate_id.start_date))
        if self.sdd_mandate_id.partner_bank_id.bank_id.bic:
            create_xml_node_chain(DrctDbtTxInf, ['DbtrAgt', 'FinInstnId', 'BIC'], self.sdd_mandate_id.partner_bank_id.bank_id.bic.replace(' ', '').upper())
        else:
            create_xml_node_chain(DrctDbtTxInf, ['DbtrAgt', 'FinInstnId', 'Othr', 'Id'], "NOTPROVIDED")
        Dbtr = create_xml_node_chain(DrctDbtTxInf, ['Dbtr','Nm'], self.sdd_mandate_id.partner_bank_id.acc_holder_name or partner.name or partner.parent_id.name)[0]

        if partner.contact_address:
            PstlAdr = create_xml_node(Dbtr, 'PstlAdr')
            if partner.country_id and partner.country_id.code:
                create_xml_node(PstlAdr, 'Ctry', partner.country_id.code)
            n_line = 0
            contact_address = partner.contact_address.replace('\n', ' ').strip()
            while contact_address and n_line < 2:
                create_xml_node(PstlAdr, 'AdrLine', self.split_node(contact_address, 70)[0])
                contact_address = self.split_node(contact_address, 70)[1]
                n_line = n_line + 1

        if self.sdd_mandate_id.debtor_id_code:
            chain_keys = ['Id', 'PrvtId', 'Othr', 'Id']
            if partner.commercial_partner_id.is_company:
                chain_keys = ['Id', 'OrgId', 'Othr', 'Id']
            create_xml_node_chain(Dbtr, chain_keys, self.sdd_mandate_id.debtor_id_code)

        create_xml_node_chain(DrctDbtTxInf, ['DbtrAcct','Id','IBAN'], self.sdd_mandate_id.partner_bank_id.sanitized_acc_number)

        if self.ref:
            create_xml_node_chain(DrctDbtTxInf, ['RmtInf', 'Ustrd'], self._sanitize_communication(self.ref))
            
        return super(AccountPayment,self).sdd_xml_gen_payment(company_id, partner, end2end_name, PmtInf)



    
