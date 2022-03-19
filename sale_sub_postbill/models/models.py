import logging
import datetime
import traceback
import math
import calendar
import requests
import time
import pytz

import pandas as pd
from dateutil.relativedelta import relativedelta
from uuid import uuid4

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import format_date
from odoo.tools.safe_eval import safe_eval

from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)

#update product_id to yiannis
#update sale_order_template_id (quotation template)

class PostBillingTemplate(models.Model):
    _inherit = 'sale.subscription.template'
    #post_billed = fields.Boolean(string='Post Billing', default=False, copy=False)


class PostBillingAccountInvoice(models.Model):
    _inherit = 'account.move'

class PostBillingSaleOrder(models.Model):
    _inherit = 'sale.order'
    
    def _prepare_invoice_values(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        journal_id = self.env['account.move'].default_get(['journal_id'])['journal_id']
        if not journal_id:
            raise UserError(_('Please define an accounting sales journal for this company.'))
        invoice_vals = {
            'name': self.client_order_ref or '',
            'origin': self.name,
            'type': 'out_invoice',
            'account_id': self.partner_invoice_id.property_account_receivable_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'journal_id': journal_id,
            'currency_id': self.pricelist_id.currency_id.id,
            'comment': self.note,
            'payment_term_id': self.payment_term_id.id,
            'fiscal_position_id': self.fiscal_position_id.id or self.partner_invoice_id.property_account_position_id.id,
            'company_id': self.company_id.id,
            'user_id': self.user_id and self.user_id.id,
            'team_id': self.team_id.id,
            'transaction_ids': [(6, 0, self.transaction_ids.ids)],
        }
        orderLineID = self.env['sale.order.line'].search(["&",["order_id","=",self.id],"|",["product_id","=",943],["product_id","=",932]]) # if uid exists on subscription instead of sale, copy to invoice
        
        return invoice_vals

    def _prepare_subscription_data(self, template):
        """Prepare a dictionnary of values to create a subscription from a template."""
        #if sale order has lines with either telephony product then pass recurring date to subscription created as last day of month
        self.ensure_one()
        values = {
            'name': template.name,
            'template_id': template.id,
            'partner_id': self.partner_invoice_id.id,
            'user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'date_start': fields.Date.today(),
            'description': self.note or template.description,
            'pricelist_id': self.pricelist_id.id,
            'company_id': self.company_id.id,
            'analytic_account_id': self.analytic_account_id.id,
            'payment_token_id': self.transaction_ids._get_last().token_id.id if template.payment_mode == 'success_payment' else False,
        }
        default_stage = self.env['sale.subscription.stage'].search([('category', '=', 'progress')], limit=1)
        if default_stage:
            values['stage_id'] = default_stage.id
        # compute the next date
        today = datetime.date.today()
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        invoicing_period = relativedelta(**{periods[template.recurring_rule_type]: template.recurring_interval})
        recurring_next_date = today + invoicing_period
        values['recurring_next_date'] = fields.Date.to_string(recurring_next_date)
        # if self.sale_order_template_id:
        _logger.error('self id of sale.order %s', self.id)
        if self.env['sale.order.line'].search(["&",["order_id","=",self.id],"|","|",["product_id","=",943],["product_id","=",932],["product_id","=",645]]):
            recurring_next_date = today + invoicing_period
            recurring_next_date_endofmonth = recurring_next_date.replace(
                day=calendar.monthrange(recurring_next_date.year, recurring_next_date.month)[1])
            values.update({
                'recurring_next_date': fields.Date.to_string(recurring_next_date_endofmonth),
            })

        return values

    
class PostBilling(models.Model):
    _inherit = 'sale.subscription'
    post_billed = fields.Boolean(string='Post Billing', default=False, copy=False)
    
    
    def _prepare_invoice_data(self):
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("You must first select a Customer for Subscription %s!", self.name))

        company = self.env.company or self.company_id

        journal = self.template_id.journal_id or self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', company.id)], limit=1)
        if not journal:
            raise UserError(_('Please define a sale journal for the company "%s".') % (company.name or '', ))
        next_date = self.recurring_next_date
        #!-------------------------
        months_interval = self.recurring_interval

        next_date_start = next_date.replace(day=1)
        next_date_start_month = next_date_start - (relativedelta(months=months_interval - 1))  # startdate if months
        #-------------------------
        if not next_date:
            raise UserError(_('Please define Date of Next Invoice of "%s".') % (self.display_name,))
        recurring_next_date = self._get_recurring_next_date(self.recurring_rule_type, self.recurring_interval, next_date, self.recurring_invoice_day)
        end_date = fields.Date.from_string(recurring_next_date) - relativedelta(days=1)     # remove 1 day as normal people thinks in term of inclusive ranges.
        
        #!-------------------------------
        end_date_month = end_date.replace(day=calendar.monthrange(end_date.year, end_date.month)[1])
        next_date_month = next_date.replace(day=calendar.monthrange(next_date.year, next_date.month)[1])
        # next_date_start_years = next_date_month - relativedelta(**{periods[self.recurring_rule_type]: self.recurring_interval})  # startdate if years
        next_date_start_years = next_date_month - relativedelta(years=self.recurring_interval,
                                                                days=-1)  # startdate if years
                                                                
        
        #_logger.error('startdate if years %s', next_date_start_years)
        #sub_f_ids = self.env['sale.subscription'].search([["message_channel_ids", "=", "sales"]])
        #for record in sub_f_ids:
        #    _logger.error('unsubscribe %s', record.message_channel_ids.ids)

        #    record.message_unsubscribe(channel_ids=record.message_channel_ids.ids)
        #----------------------------------                                                        
        addr = self.partner_id.address_get(['delivery', 'invoice'])
        sale_order = self.env['sale.order'].search([('order_line.subscription_id', 'in', self.ids)], order="id desc", limit=1)
        use_sale_order = sale_order and sale_order.partner_id == self.partner_id
        partner_id = sale_order.partner_invoice_id.id if use_sale_order else self.partner_invoice_id.id or addr['invoice']
        partner_shipping_id = sale_order.partner_shipping_id.id if use_sale_order else self.partner_shipping_id.id or addr['delivery']
        fpos = self.env['account.fiscal.position'].with_company(company).get_fiscal_position(self.partner_id.id, partner_shipping_id)
        narration = _("This invoice covers the following period: %s - %s") % (format_date(self.env, next_date), format_date(self.env, end_date))
        if self.description:
            narration += '\n' + self.description
        elif self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms') and self.company_id.invoice_terms:
            narration += '\n' + self.company_id.invoice_terms
        
        #!-----------------------------------
        last_day_of_month = calendar.monthrange(self.recurring_next_date.year, self.recurring_next_date.month)[1]
        if self.post_billed == True:
            #try:
                #_logger.error("Writing nextcall")
                #cron = self.sudo().env.ref('sale_sub_postbill._telecom_cron')
                #cron.sudo().write({'nextcall': (
                #    (datetime.datetime.now() + (relativedelta(months=1))).replace(day=1, hour=2, minute=0, second=0,
                #                                                                  microsecond=0)).strftime('%d/%m/%Y %H:%M:%S')})
            #except Exception as e:
                #_logger.error("Failed to write nextcall: %s", e)
                #pass
            if self.recurring_next_date != datetime.date(self.recurring_next_date.year, self.recurring_next_date.month,
                                                         last_day_of_month):
                raise UserError(_('Subscriptions app failed to generate a post-billed invoice: %s'
                                  ' Can only generate post-billed invoices if Date of next invoice is set on the last day of a month: "%s".') % (
                                    self.name, self.recurring_next_date,))
            else:
                recurringnextdate = next_date_month.replace(day=1)
                self.write({'recurring_next_date': recurringnextdate.replace(
                    day=calendar.monthrange(recurringnextdate.year, recurringnextdate.month)[1])})
                _logger.error('recurringnextdate: %s', recurringnextdate)  # startdate
                _logger.error('recurring_next_date: %s', self.recurring_next_date)  # enddate
                if self.recurring_rule_type == 'yearly':
                    return {
                        'move_type': 'out_invoice',
                        'partner_id': partner_id,
                        'partner_shipping_id': partner_shipping_id,
                        'currency_id': self.pricelist_id.currency_id.id,
                        'journal_id': journal.id,
                        'invoice_origin': self.code,
                        'fiscal_position_id': fpos.id,
                        'invoice_payment_term_id': self.payment_term_id.id,
                        'narration': _("This invoice covers the following period: %s - %s") % (
                            format_date(self.env, next_date_start_years), format_date(self.env, next_date_month)),
                        'invoice_user_id': self.user_id.id,
                        'partner_bank_id': company.partner_id.bank_ids.filtered(lambda b: not b.company_id or b.company_id == company)[:1].id,
                        'invoice_date': next_date_month,  # set invoice date to last date of month
                        'invoice_date_due': self.recurring_next_date,
                    }
                else:
                    return {
                        'move_type': 'out_invoice',
                        'partner_id': partner_id,
                        'partner_shipping_id': partner_shipping_id,
                        'currency_id': self.pricelist_id.currency_id.id,
                        'journal_id': journal.id,
                        'invoice_origin': self.code,
                        'fiscal_position_id': fpos.id,
                        'invoice_payment_term_id': self.payment_term_id.id,
                        'narration': _("This invoice covers the following period: %s - %s") % (
                            format_date(self.env, next_date_start_month), format_date(self.env, next_date_month)),
                        'invoice_user_id': self.user_id.id,
                        'partner_bank_id': company.partner_id.bank_ids.filtered(lambda b: not b.company_id or b.company_id == company)[:1].id,
                        'invoice_date': next_date_month,  # set invoice date to last date of month
                        'invoice_date_due': self.recurring_next_date,
                    }
        else:
          res = {
              'move_type': 'out_invoice',
              'partner_id': partner_id,
              'partner_shipping_id': partner_shipping_id,
              'currency_id': self.pricelist_id.currency_id.id,
              'journal_id': journal.id,
              'invoice_origin': self.code,
              'fiscal_position_id': fpos.id,
              'invoice_payment_term_id': self.payment_term_id.id,
              'narration': narration,
              'invoice_user_id': self.user_id.id,
              'partner_bank_id': company.partner_id.bank_ids.filtered(lambda b: not b.company_id or b.company_id == company)[:1].id,
          }
          
        if self.team_id:
            res['team_id'] = self.team_id.id
        return res
    
    def _recurring_create_invoice(self, automatic=False, batch_size=20):
        auto_commit = self.env.context.get('auto_commit', True)
        cr = self.env.cr
        invoices = self.env['account.move']
        current_date = datetime.date.today()

        if len(self) > 0:
            subscriptions = self
            need_cron_trigger = False
        else:
            subscriptions = self.search([
                ('recurring_next_date', '<=', current_date),
                ('template_id.payment_mode', '!=','manual'),
                '|',
                ('stage_category', '=', 'progress'),
                ('to_renew', '=', True),
            ], limit=batch_size + 1)
            need_cron_trigger = len(subscriptions) > batch_size
            if need_cron_trigger:
                subscriptions = subscriptions[:batch_size]

        if subscriptions:
            sub_data = subscriptions.read(fields=['id', 'company_id'])
            for company_id in set(data['company_id'][0] for data in sub_data):
                sub_ids = [s['id'] for s in sub_data if s['company_id'][0] == company_id]
                subs = self.with_company(company_id).with_context(company_id=company_id).browse(sub_ids)
                Invoice = self.env['account.move'].with_context(move_type='out_invoice', company_id=company_id).with_company(company_id)
                subs_order_lines = self.env['sale.order.line'].search([('subscription_id', 'in', sub_ids)])
                for subscription in subs:
                    subscription = subscription[0]  # Trick to not prefetch other subscriptions, as the cache is currently invalidated at each iteration
                    sub_so = subs_order_lines.filtered(lambda ol: ol.subscription_id.id == subscription.id).order_id
                    sub_so_renewal = sub_so.filtered(lambda so: so.subscription_management == 'renew')
                    reference_so = max(sub_so_renewal, key=lambda so: so.date_order, default=False) or min(sub_so,
                                                                                                           key=lambda
                                                                                                               so: so.date_order,
                                                                                                           default=False)
                    invoice_ctx = {'lang': subscription.partner_id.lang}
                    if reference_so and reference_so.client_order_ref:
                        invoice_ctx['new_invoice_ref'] = reference_so.client_order_ref
                    if automatic and auto_commit:
                        cr.commit()

                    # if we reach the end date of the subscription then we close it and avoid to charge it
                    if automatic and subscription.date and subscription.date <= current_date:
                        subscription.set_close()
                        continue

                    # payment + invoice (only by cron)
                    if subscription.template_id.payment_mode == 'success_payment' and subscription.recurring_total and automatic:
                        try:
                            payment_token = subscription.payment_token_id
                            tx = None
                            if payment_token:

                                invoice_values = subscription.with_context(invoice_ctx)._prepare_invoice()
                                new_invoice = Invoice.create(invoice_values)
                                if subscription.analytic_account_id or subscription.tag_ids:
                                    for line in new_invoice.invoice_line_ids:
                                        if subscription.analytic_account_id:
                                            line.analytic_account_id = subscription.analytic_account_id
                                        if subscription.tag_ids:
                                            line.analytic_tag_ids = subscription.tag_ids
                                new_invoice.message_post_with_view(
                                    'mail.message_origin_link',
                                    values={'self': new_invoice, 'origin': subscription},
                                    subtype_id=self.env.ref('mail.mt_note').id)
                                tx = subscription._do_payment(payment_token, new_invoice)[0]
                                # commit change as soon as we try the payment so we have a trace somewhere
                                if auto_commit:
                                    cr.commit()
                                if tx.renewal_allowed:
                                    msg_body = _('Automatic payment succeeded. Payment reference: <a href=# data-oe-model=payment.transaction data-oe-id=%d>%s</a>; Amount: %s. Invoice <a href=# data-oe-model=account.move data-oe-id=%d>View Invoice</a>.') % (tx.id, tx.reference, tx.amount, new_invoice.id)
                                    subscription.message_post(body=msg_body)
                                    # success_payment
                                    if new_invoice.state != 'posted':
                                        new_invoice._post(False)
                                    subscription.send_success_mail(tx, new_invoice)
                                    if auto_commit:
                                        cr.commit()
                                else:
                                    _logger.error('Fail to create recurring invoice for subscription %s', subscription.code)
                                    if auto_commit:
                                        cr.rollback()
                                    # Check that the invoice still exists before unlinking. It might already have been deleted by `reconcile_pending_transaction`.
                                    new_invoice.exists().unlink()
                            if tx is None or not tx.renewal_allowed:
                                amount = subscription.recurring_total
                                auto_close_limit = subscription.template_id.auto_close_limit or 15
                                date_close = (
                                    subscription.recurring_next_date +
                                    relativedelta(days=auto_close_limit)
                                )
                                close_subscription = current_date >= date_close
                                email_context = self.env.context.copy()
                                email_context.update({
                                    'payment_token': subscription.payment_token_id and subscription.payment_token_id.name,
                                    'renewed': False,
                                    'total_amount': amount,
                                    'email_to': subscription.partner_id.email,
                                    'code': subscription.code,
                                    'currency': subscription.pricelist_id.currency_id.name,
                                    'date_end': subscription.date,
                                    'date_close': date_close,
                                    'auto_close_limit': auto_close_limit
                                })
                                if close_subscription:
                                    template = self.env.ref('sale_subscription.email_payment_close')
                                    template.with_context(email_context).send_mail(subscription.id)
                                    _logger.debug("Sending Subscription Closure Mail to %s for subscription %s and closing subscription", subscription.partner_id.email, subscription.id)
                                    msg_body = _('Automatic payment failed after multiple attempts. Subscription closed automatically.')
                                    subscription.message_post(body=msg_body)
                                    subscription.set_close()
                                else:
                                    template = self.env.ref('sale_subscription.email_payment_reminder')
                                    msg_body = _('Automatic payment failed. Subscription set to "To Renew".')
                                    if (datetime.date.today() - subscription.recurring_next_date).days in [0, 3, 7, 14]:
                                        template.with_context(email_context).send_mail(subscription.id)
                                        _logger.debug("Sending Payment Failure Mail to %s for subscription %s and setting subscription to pending", subscription.partner_id.email, subscription.id)
                                        msg_body += _(' E-mail sent to customer.')
                                    subscription.message_post(body=msg_body)
                                    subscription.set_to_renew()
                            if auto_commit:
                                cr.commit()
                        except Exception:
                            if auto_commit:
                                cr.rollback()
                            # we assume that the payment is run only once a day
                            traceback_message = traceback.format_exc()
                            _logger.error(traceback_message)
                            last_tx = self.env['payment.transaction'].search([('reference', 'like', 'SUBSCRIPTION-%s-%s' % (subscription.id, datetime.date.today().strftime('%y%m%d')))], limit=1)
                            error_message = "Error during renewal of subscription %s (%s)" % (subscription.code, 'Payment recorded: %s' % last_tx.reference if last_tx and last_tx.state == 'done' else 'No payment recorded.')
                            _logger.error(error_message)

                    # invoice only
                    elif subscription.template_id.payment_mode in ['draft_invoice', 'manual', 'validate_send']:
                        try:
                            # We don't allow to create invoice past the end date of the contract.
                            # The subscription must be renewed in that case
                            if subscription.date and subscription.recurring_next_date >= subscription.date:
                                return
                            else:
                                invoice_values = subscription.with_context(invoice_ctx)._prepare_invoice()
                                new_invoice = Invoice.create(invoice_values)
                                if subscription.analytic_account_id or subscription.tag_ids:
                                    for line in new_invoice.invoice_line_ids:
                                        if subscription.analytic_account_id:
                                            line.analytic_account_id = subscription.analytic_account_id
                                        if subscription.tag_ids:
                                            line.analytic_tag_ids = subscription.tag_ids
                                new_invoice.message_post_with_view(
                                    'mail.message_origin_link',
                                    values={'self': new_invoice, 'origin': subscription},
                                    subtype_id=self.env.ref('mail.mt_note').id)
                                invoices += new_invoice
                                next_date = subscription.recurring_next_date or current_date
                                periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
                                invoicing_period = relativedelta(
                                    **{periods[subscription.recurring_rule_type]: subscription.recurring_interval})
                                new_date = next_date + invoicing_period
                                _logger.error("NEW DATE %s:", new_date)
                                if subscription.post_billed == True:
                                    new_date_plus = new_date.replace(
                                        day=calendar.monthrange(new_date.year, new_date.month)[1])
                                    _logger.error("post billed ticked and recurring next date is %s:", new_date_plus)
                                    subscription.write({'recurring_next_date': new_date_plus.strftime('%Y-%m-%d')})
                                else:
                                  # When `recurring_next_date` is updated by cron or by `Generate Invoice` action button,
                                  # write() will skip resetting `recurring_invoice_day` value based on this context value
                                  subscription.with_context(skip_update_recurring_invoice_day=True).increment_period()
                                  if subscription.template_id.payment_mode == 'validate_send':
                                      new_invoice.action_post()
                                  if automatic and auto_commit:
                                    cr.commit()
                        except Exception:
                            if automatic and auto_commit:
                                cr.rollback()
                                _logger.exception('Fail to create recurring invoice for subscription %s', subscription.code)
                            else:
                                raise

        # Retrieve the invoice to send mails.
        self._cr.execute('''
            SELECT
                DISTINCT aml.move_id,
                move.date
            FROM account_move_line aml
            JOIN sale_subscription subscr ON subscr.id = aml.subscription_id
            JOIN sale_subscription_template subscr_tpl ON subscr_tpl.id = subscr.template_id
            JOIN account_move move ON move.id = aml.move_id
            WHERE move.state = 'posted'
                AND move.is_move_sent IS FALSE
                AND subscr_tpl.payment_mode = 'validate_send'
            ORDER BY move.date DESC
        ''')
        invoice_to_send_ids = [row[0] for row in self._cr.fetchall()]

        invoices_to_send = self.env['account.move'].browse(invoice_to_send_ids)
        for invoice in invoices_to_send:
            if invoice._is_ready_to_be_sent():
                subscription = invoice.line_ids.subscription_id
                subscription.validate_and_send_invoice(invoice)

        # There is still some subscriptions to process. Then, make sure the CRON will be triggered again asap.
        if need_cron_trigger:
            self.env.ref('sale_subscription.account_analytic_cron_for_invoice')._trigger()

        return invoices
    
    
    
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        """
        Override to add subscription-specific behaviours.

        Display the invoicing period in the invoice line description, link the invoice line to the
        correct subscription and to the subscription's analytic account if present, add revenue dates.
        """
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)  # <-- ensure_one()
        if self.subscription_id:
            res.update(subscription_id=self.subscription_id.id)
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            next_date = self.subscription_id.recurring_next_date
            previous_date = next_date - relativedelta(**{periods[self.subscription_id.recurring_rule_type]: self.subscription_id.recurring_interval})
            is_already_period_msg = True if _("Invoicing period") in self.name else False
            if self.order_id.subscription_management != 'upsell':  # renewal or creation: one entire period
                date_start = previous_date
                date_start_display = previous_date
                date_end = next_date - relativedelta(days=1)  # the period does not include the next renewal date
            else:  # upsell: pro-rated period\
                date_start, date_start_display, date_end = None, None, None
                #if is_already_period_msg:
                try:
                    regexp = r"\[(\d{4}-\d{2}-\d{2}) -> (\d{4}-\d{2}-\d{2})\]"
                    match = re.search(regexp, self.name)
                    date_start = fields.Date.from_string(match.group(1))
                    date_start_display = date_start
                    date_end = fields.Date.from_string(match.group(2))
                except Exception:
                    _logger.error('_prepare_invoice_line: unable to compute invoicing period for %r - "%s"', self, self.name)
            if not date_start or not date_start_display or not date_end:
                # here we have a slight problem: the date used to compute the pro-rated discount
                # (that is, the date_from in the upsell wizard) is not stored on the line,
                # preventing an exact computation of start and end revenue dates
                # witness me as I try to retroengineer the ~correct dates 🙆‍
                # (based on `partial_recurring_invoice_ratio` from the sale.subscription model)
                total_days = (next_date - previous_date).days
                days = round((1 - self.discount / 100.0) * total_days)
                date_start = next_date - relativedelta(days=days+1)
                date_start_display = next_date - relativedelta(days=days)
                date_end = next_date - relativedelta(days=1)
                #else:
                    #is_already_period_msg = True
                    
            if not is_already_period_msg:
                lang = self.order_id.partner_invoice_id.lang
                format_date = self.env['ir.qweb.field.date'].with_context(lang=lang).value_to_html
                # Ugly workaround to display the description in the correct language
                if lang:
                    self = self.with_context(lang=lang)
                if self.subscription_id.post_billed and self.subscription_id.recurring_rule_type == 'monthly':
                    period_msg = _("Invoicing period: %s - %s") % (
                        format_date(fields.Date.to_string(previous_date + relativedelta(months=-1) + relativedelta(day=1)), {}),
                        format_date(fields.Date.to_string(previous_date + relativedelta(months=-1) + relativedelta(day=31)), {}))
                    res.update(name=self.name + '\n' + period_msg)
                #elif self.subscription_id.post_billed and self.subscription_id.recurring_rule_type == 'yearly':
                  #  period_msg = _("Invoicing period: %s - %s") % (
                 # #      format_date(fields.Date.to_string(self.subscription_id.date_start), {}), 
                  #      format_date(fields.Date.to_string(self.subscription_id.recurring_next_date), {}))
                 #   res.update(name=self.name + '\n' + period_msg)
                    
                #else:
                #    period_msg = _("Invoicing period") + ": %s - %s" % (format_date(fields.Date.to_string(date_start_display), {}), format_date(fields.Date.to_string(date_end), {}))
                #    res.update({
                #        'name': res['name'] + '\n' + period_msg,
                #    })
            res.update({
                'subscription_start_date': date_start,
                'subscription_end_date': date_end,
            })
            if self.subscription_id.analytic_account_id:
                res['analytic_account_id'] = self.subscription_id.analytic_account_id.id
        return res
    