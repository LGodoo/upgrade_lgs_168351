# Copyright 2018 ForgeFlow, S.L. (http://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models
import logging
import base64
from datetime import datetime

_logger = logging.getLogger(__name__)

class OutstandingStatementWizard(models.TransientModel):
    """Outstanding Statement wizard."""

    _name = "outstanding.statement.wizard"
    _inherit = ['statement.common.wizard','mail.thread']
    _description = "Outstanding Statement Wizard"

    def _export(self):
        """Export to PDF."""
        data = self._prepare_statement()
        return self.env.ref(
            "partner_statement.action_print_outstanding_statement"
        ).report_action(self.ids, data=data)
        
    def get_object_reference(self, module, xml_id):
        """Returns (model, res_id) corresponding to a given module and xml_id (cached) or raise ValueError if not found"""
        ir_model_obj = self.env['ir.model.data']
        
        return ir_model_obj._xmlid_lookup("%s.%s" % (module, xml_id))[1:3]
    
    def _mail(self):
        template = self.env.ref('partner_statement.outstanding_statement_email_template')
        ir_model_obj = self.env['ir.model.data']

        template_browse = self.get_object_reference('partner_statement', 'outstanding_statement_email_template')[1]
        email_template_obj = self.env['mail.template'].browse(template_browse)

        # self.composer_id.template_id = template


        context = dict(self._context or {})

        active_ids = context.get('active_ids', []) or []
        _logger.info("active ids : %r", active_ids)
        partner_ids = []
        for record in self.env['res.partner'].browse(active_ids):
            if record.search([("message_partner_ids", "not ilike", record.id)]):
                partner_ids = []
                partner_ids.append(record.id)
                record.message_subscribe(partner_ids=partner_ids)
                _logger.info("message partner ids with added: %r", record.message_partner_ids)
            data = self._prepare_statement()
            data.update({'partner_ids': [record.id]})
            #emails = []
            pdf = self.env.ref('partner_statement.action_print_outstanding_statement').sudo()._render_qweb_pdf([record.id],data=data)
            b64_pdf = base64.b64encode(pdf[0])
            dateend = self.date_end.strftime("%d-%b-%Y")


            ATTACHMENT_NAME_out = "Outstanding_statement_" + record.name+"_"+dateend

            att1 =  self.env['ir.attachment'].create({
                'name': 'Outstanding_statement_'+record.name+'_'+dateend +'.pdf',
                'type': 'binary',
                'datas': b64_pdf,   #TESTTESTTEST
                #'datas_fname': ATTACHMENT_NAME_out + '.pdf',
                'store_fname': ATTACHMENT_NAME_out,
                'res_model': 'res.partner',
                #'res_id': record.id,
                #'res_field': 1,
                'mimetype': 'application/pdf'
            })
            #for partner in record.message_partner_ids:
            #    emails.append(partner.email)

            #values = email_template_obj.generate_email(record.id, ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])  # it is to generate email for specific object record
            #self.composer_id.template_id.send_mail(record.id,force_send=True)
            #_logger.info("emails : %r", emails)

            #values.update({
            #    'attachment_ids':[att1.id],
            #    'email_cc':[emails],
            #})

            #_logger.info("record : %r", record)
            #_logger.info("values: %r", values)
            #record.message_post(type="email")#, body= "Dear " + record.name + ", Please find attached your activity report. Regards", force_send=True, notif_layout=False, attachments=values)
            #email_template_obj.attachment_ids = [(4, att1.id)]
            #email_template_obj.send_mail(record.id, force_send=True)
            #email_template_obj.attachment_ids = None
            
            email_template_obj.attachment_ids = [(6,0, [att1.id])]
            #email_template_obj.email_to = partner_ids
            record.message_post_with_template(email_template_obj.id)
            email_template_obj.attachment_ids = [(3, att1.id)]
