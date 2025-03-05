# -*- coding: utf-8 -*-
from itertools import groupby
from odoo import models, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo import models, fields, Command

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    project_id = fields.Many2one('project.project', string='Project', help="Project linked to this sale")

    def _create_invoices(self, grouped=False, final=False, date=None):
        if not self.env['account.move'].check_access_rights('create', False):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                return self.env['account.move']
            
        if not all(order.project_id for order in self):
            return super(SaleOrder, self)._create_invoices(grouped=grouped, final=final, date=date)
        else:
            return self._create_invoices_with_project(grouped=grouped, final=final, date=date)

    def _create_invoices_with_project(self, grouped=False, final=False, date=None):
        """Nueva lógica cuando hay project_id en todas las órdenes."""
        invoice_vals_list = []
        invoice_item_sequence = 0

        for order in self:
            order = order.with_company(order.company_id)
            invoice_vals = order._prepare_invoice()
            invoiceable_lines = order._get_invoiceable_lines(final)

            internal_product_total = 0.0
            invoice_line_vals = []
            down_payment_section_added = False
            sale_line_ids = []
            for line in invoiceable_lines:
                if line.product_id.is_internal_product:
                    # Sumar el monto de los productos internos (omitir de la factura)
                    internal_product_total += line.price_subtotal
                    sale_line_ids.append(line.id)
                    continue  # No se añade a la factura

                if not down_payment_section_added and line.is_downpayment:
                    invoice_line_vals.append(
                        Command.create(
                            order._prepare_down_payment_section_line(sequence=invoice_item_sequence)
                        ),
                    )
                    down_payment_section_added = True
                    invoice_item_sequence += 1

                invoice_line_vals.append(
                    Command.create(
                        line._prepare_invoice_line(sequence=invoice_item_sequence)
                    ),
                )
                invoice_item_sequence += 1

            # Si hay monto acumulado de productos internos, se agrega la línea consolidada
            if internal_product_total > 0:
                internal_product_line = {
                    'product_id': self.env.ref('internal_products.product_product_project').id,  # Producto específico para consolidar
                    'name': order.project_id.name,
                    'quantity': 1,
                    'price_unit': internal_product_total,
                    'sequence': invoice_item_sequence,
                    'sale_line_ids': [(6, 0, sale_line_ids)]
                }
                invoice_line_vals.append(Command.create(internal_product_line))
                invoice_item_sequence += 1

            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list and self._context.get('raise_if_nothing_to_invoice', True):
            raise UserError(self._nothing_to_invoice_error_message())

        # Si quieres agrupar facturas por partner/currency (opcional)
        if not grouped:
            invoice_vals_list = self._group_invoice_vals_list(invoice_vals_list)

        if len(invoice_vals_list) < len(self):
            SaleOrderLine = self.env['sale.order.line']
            for invoice in invoice_vals_list:
                sequence = 1
                for line in invoice['invoice_line_ids']:
                    line[2]['sequence'] = SaleOrderLine._get_invoice_line_sequence(new=sequence, old=line[2]['sequence'])
                    sequence += 1


        moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(invoice_vals_list)

        if final:
            moves.sudo().filtered(lambda m: m.amount_total < 0).action_switch_invoice_into_refund_credit_note()

        for move in moves:
            move.message_post_with_view(
                'mail.message_origin_link',
                values={'self': move, 'origin': move.line_ids.sale_line_ids.order_id},
                subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'))

        return moves

    def _group_invoice_vals_list(self, invoice_vals_list):
        """Función auxiliar para agrupar las facturas (similar a la lógica original)."""
        new_invoice_vals_list = []
        invoice_grouping_keys = self._get_invoice_grouping_keys()
        invoice_vals_list = sorted(
            invoice_vals_list,
            key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys]
        )
        for _grouping_keys, invoices in groupby(
            invoice_vals_list,
            key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys]
        ):
            origins = set()
            payment_refs = set()
            refs = set()
            ref_invoice_vals = None
            for invoice_vals in invoices:
                if not ref_invoice_vals:
                    ref_invoice_vals = invoice_vals
                else:
                    ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                origins.add(invoice_vals['invoice_origin'])
                payment_refs.add(invoice_vals['payment_reference'])
                refs.add(invoice_vals['ref'])
            ref_invoice_vals.update({
                'ref': ', '.join(refs)[:2000],
                'invoice_origin': ', '.join(origins),
                'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
            })
            new_invoice_vals_list.append(ref_invoice_vals)

        return new_invoice_vals_list
