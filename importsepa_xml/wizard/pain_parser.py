# Copyright 2016 Carlos Dauden <carlos.dauden@tecnativa.com>
# Copyright 2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
from lxml import etree
from odoo import _, api, models, fields
import logging
_logger = logging.getLogger(__name__)

class PainParser(object):
    """Parser for SEPA Direct Debit Unpaid Report import files."""


    def parse_msgid(self,root):
        msgid = []
        ns = 'urn:iso:std:iso:20022:tech:xsd:pain.002.001.03'

        if root.findall('.//ns:OrgnlMsgId', namespaces={'ns': ns}):

            for OrgnlMsgId in root.iter('{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}CstmrPmtStsRpt'):
                msgidval = OrgnlMsgId.find('.//ns:OrgnlMsgId', namespaces={'ns': ns}).text
                if msgidval:
                    msgid.append(msgidval)
                else:
                    msgid.append('')
            return msgid

        else:
            return ''



    def parse_record(self,root):
        recordid = []
        ns = 'urn:iso:std:iso:20022:tech:xsd:pain.002.001.03'
        if root.findall('.//EndToEndId'):
            for EndToEndId in root.iter('TrxInf'):
                recordidval = EndToEndId.find('EndToEndId').text
                if recordidval:
                    recordid.append(recordidval)
                else:
                    recordid.append('')

            return recordid
        elif root.findall('.//ns:OrgnlEndToEndId', namespaces={'ns': ns}):

            for OrgnlEndToEndId in root.iter('{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}OrgnlPmtInfAndSts'):
                recordidval = OrgnlEndToEndId.find('.//ns:OrgnlEndToEndId', namespaces={'ns': ns}).text
                if recordidval:
                    recordid.append(recordidval)
                else:
                    recordid.append('')

            return recordid
        else:
            return ' '

    def parse_date(self,root):
        date = []
        ns = 'urn:iso:std:iso:20022:tech:xsd:pain.002.001.03'
        if root.findall('.//ValueDate'):
            for ValueDate in root.iter('TrxInf'):
                dateval = ValueDate.find('ValueDate').text
                if dateval:
                    date.append(dateval)
                else:
                    date.append('')
            return date
        elif root.findall('.//ns:ReqdColltnDt', namespaces={'ns': ns}):
            for ReqdColltnDt in root.iter('{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}OrgnlPmtInfAndSts'):
                dateval = ReqdColltnDt.find('.//ns:ReqdColltnDt', namespaces={'ns': ns}).text
                if dateval:
                    date.append(dateval)
                else:
                    date.append('')
            return date
        else:
            return ''

    def parse_amount(self,root):
        amount = []
        ns = 'urn:iso:std:iso:20022:tech:xsd:pain.002.001.03'
        if root.findall('.//CollectionAmount'):

            for CollectionAmount in root.iter('TrxInf'):
                amountval = CollectionAmount.find('CollectionAmount').text
                if amountval:
                    amount.append(amountval)
                else:
                    amount.append(0.0)

            return amount
        elif root.findall('.//ns:InstdAmt', namespaces={'ns': ns}):
            for InstdAmt in root.iter('{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}OrgnlPmtInfAndSts'):
                amountval = InstdAmt.find('.//ns:InstdAmt', namespaces={'ns': ns}).text
                if amountval:
                    print(amountval)
                    amount.append(amountval)
                else:
                    amount.append(0.0)
            return amount
        else:
            return 0.0

    def parse_status(self,root):
        status = []
        ns = 'urn:iso:std:iso:20022:tech:xsd:pain.002.001.03'
        if root.findall('.//GrpSts'):
            for GrpSts in root.iter('OrgnlGrpInfAndSts'):
                statusval = GrpSts.find('GrpSts').text
                if statusval:
                    status.append(statusval)
                else:
                    status.append('')
            return status

        elif root.findall('.//ns:TxSts', namespaces={'ns': ns}):

            for TxSts in root.iter('{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}OrgnlPmtInfAndSts'):
                msgidval = TxSts.find('.//ns:TxSts', namespaces={'ns': ns}).text
                if msgidval:
                    status.append(msgidval)
                else:
                    status.append('')
            return status

        elif root.findall('.//ns:GrpSts', namespaces={'ns': ns}):

            for GrpSts in root.iter('{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}OrgnlGrpInfAndSts'):
                msgidval = GrpSts.find('.//ns:GrpSts', namespaces={'ns': ns}).text
                if msgidval:
                    status.append(msgidval)

                else:
                    status.append('')
            return status
        else:
            return ''

    def parse_errorcode(self,root):
        ns = 'urn:iso:std:iso:20022:tech:xsd:pain.002.001.03'
        error = []
        if root.findall('.//CollectionAmount'):
            for CollectionAmount in root.iter('TrxInf'):
                error.append('')
            return error
        elif root.findall('.//ns:Cd', namespaces={'ns': ns}):

            for Cd in root.iter('{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}Rsn'):
                errorcode = Cd.find('.//ns:Cd', namespaces={'ns': ns}).text
                if errorcode:
                    _logger.error(errorcode)

                    error.append(errorcode)
                    _logger.error(error)

                else:
                    error.append('')
            return error
        elif root.findall('.//ns:Cd', namespaces={'ns': ns}):
            for Cd in root.iter('{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}OrgnlGrpInfAndSts'):
                errorcode = Cd.find('.//ns:Cd', namespaces={'ns': ns}).text
                if errorcode:
                    error.append(errorcode)
                    _logger.error(error)
                    _logger.error('test2')


                else:
                    error.append('')
            return error

        else:
            return ''

    def text_code(self,errorcodetext):
        switcher = {
            'AC01': "Account identifier incorrect (i.e. invalid IBAN)",
            'AC04': "Account closed",
            'AC06': "Account blocked: Account blocked for direct debit by the Debtor",
            'AG01': "Direct debit forbidden on this account for regulatory reasons",
            'AG02': "Operation/transaction code incorrect, invalid file format Usage Rule: To be used to indicate an incorrect ‘operation/transaction’ code",
            'AM01': "Specified message amount is equal to zero",
            'AM02': "Specific transaction/message amount is greater than allowed maximum",
            'AM04': "Insufficient funds",
            'AM05': "Duplicate collection",
            'BE05': "Identifier of the Creditor Incorrect",
            'DT01': "Invalid date (eg. wrong settlement date)",
            'FF01': "Operation/transaction code incorrect, invalid file formatUsage Rule: To be used to indicate an invalid file format.",
            'FF05': "Direct Debit type incorrect",
            'MD01': "No valid Mandate",
            'MD02': "Mandate data missing or incorrect",
            'MD07': "Debtor deceased",
            'MS02': "Refusal by the Debtor",
            'MS03': "Reason not specified",
            'RC01': "Bank identifier incorrect (i.e. invalid BIC)",
            'RR01': "Regulatory Reason",
            'RR02': "Regulatory Reason",
            'RR03': "Regulatory Reason",
            'RR04': "Regulatory Reason",
            'SL01': "Specific Service offered by the Debtor Bank.",
            'DNOR': "Debtor bank is not registered under this BIC in the CSM",
            'CNOR': "Creditor bank is not registered under this BIC in the CSM",
            'AGNT': "Agent in the payment workflow is incorrect.",
            'CURR': "Currency of the payment is incorrect.",
            'CUST': "Cancellation requested by the Debtor.",
            'CUTA': "Cancellation requested because an investigation request has been received and no remediation is possible.",
            'DUPL': "Payment is a duplicate of another payment.",
            'UPAY': "Payment is not justified.",
        }
        print(errorcodetext)
        textcode = []
        for errorcode in errorcodetext:
            textcode.append(switcher.get(errorcode, ""))
        if len(textcode) != 0:

            return textcode
        else:
            return ''


    def parse(self, data):
        """Parse a pain.002.001.03 file."""
        try:
            _logger.error("1")
            root = etree.fromstring(
                data, parser=etree.XMLParser(recover=True))
            _logger.error(root)

        except etree.XMLSyntaxError:
            # ABNAmro is known to mix up encodings
            root = etree.fromstring(
                data.decode('iso-8859-15').encode('utf-8'))
        if root == None:
            raise ValueError(
                'Not a valid xml file, or not an xml file at all.')
        payment_transactions = {}
        payment_transactions['transactions'] = []
        transaction = {}
        payment_returns = []

        amount = self.parse_amount(root)
        if amount:
            amounttext = amount
            transaction['amount'] = amounttext
        else:
            amount = 0.0
            transaction['amount'] = amount
        _logger.error("amount")

        recordid = self.parse_record(root)
        if recordid:
            payment_transactions['name'] = recordid
        elif recordid == '':
            payment_transactions['name'] = 'no reference'
        _logger.error("record")

        msgid = self.parse_msgid(root)
        if msgid:
            payment_transactions['msgid'] = msgid
        elif msgid == '':
            payment_transactions['msgid'] = ''
        _logger.error("msgid")

        date = self.parse_date(root)
        if date:
            payment_transactions['date'] = date
        elif date == '':
            payment_transactions['date'] = ''

        _logger.error("date")

        status = self.parse_status(root)
        if status:
            payment_transactions['status'] = status
        elif status == '':
            payment_transactions['status'] = ''
        _logger.error("status")

        errorcode = self.parse_errorcode(root)
        _logger.error("after errorcode")
        _logger.error(errorcode)
        if errorcode:
            _logger.error("in if after textcode=")
            textcode = (self.text_code(errorcode))
            transaction['reason_code'] = errorcode
            transaction['reason'] = textcode
        elif errorcode == '':
            _logger.error("in else")
            textcode = ''
            payment_transactions['reason_code'] = ''
            payment_transactions['reason'] = ''
        if len(transaction):
            payment_transactions['transactions'].append(transaction)
        _logger.error("before dict")
        dict = {
            'recordid': recordid,
            'date': date,
            'errorcode': errorcode,
            'textcode': textcode,
            'amount': amount,
            'msgid': msgid,
            'status': status,

        }
        _logger.error("after dict")
        payment_returns.append(dict)

        _logger.error(recordid)
        _logger.error(payment_returns)



        return payment_returns


