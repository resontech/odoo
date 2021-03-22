# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import Form, TransactionCase
from odoo import fields


class TestSaleMrpFlow(TransactionCase):

    def setUp(self):
        super(TestSaleMrpFlow, self).setUp()
        # Useful models
        self.UoM = self.env['uom.uom']
        self.categ_unit = self.env.ref('uom.product_uom_categ_unit')
        self.categ_kgm = self.env.ref('uom.product_uom_categ_kgm')
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.warehouse = self.env.ref('stock.warehouse0')

        self.uom_kg = self.env['uom.uom'].search([('category_id', '=', self.categ_kgm.id), ('uom_type', '=', 'reference')],
                                                 limit=1)
        self.uom_kg.write({
            'name': 'Test-KG',
            'rounding': 0.000001})
        self.uom_gm = self.UoM.create({
            'name': 'Test-G',
            'category_id': self.categ_kgm.id,
            'uom_type': 'smaller',
            'factor': 1000.0,
            'rounding': 0.001})
        self.uom_unit = self.env['uom.uom'].search(
            [('category_id', '=', self.categ_unit.id), ('uom_type', '=', 'reference')], limit=1)
        self.uom_unit.write({
            'name': 'Test-Unit',
            'rounding': 0.01})
        self.uom_dozen = self.UoM.create({
            'name': 'Test-DozenA',
            'category_id': self.categ_unit.id,
            'factor_inv': 12,
            'uom_type': 'bigger',
            'rounding': 0.001})

        # Creating all components
        self.component_a = self._create_product('Comp A', self.uom_unit)
        self.component_b = self._create_product('Comp B', self.uom_unit)
        self.component_c = self._create_product('Comp C', self.uom_unit)
        self.component_d = self._create_product('Comp D', self.uom_unit)
        self.component_e = self._create_product('Comp E', self.uom_unit)
        self.component_f = self._create_product('Comp F', self.uom_unit)
        self.component_g = self._create_product('Comp G', self.uom_unit)

        # Create a kit 'kit_1' :
        # -----------------------
        #
        # kit_1 --|- component_a   x2
        #         |- component_b   x1
        #         |- component_c   x3

        self.kit_1 = self._create_product('Kit 1', self.uom_unit)

        self.bom_kit_1 = self.env['mrp.bom'].create({
            'product_tmpl_id': self.kit_1.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})

        BomLine = self.env['mrp.bom.line']
        BomLine.create({
            'product_id': self.component_a.id,
            'product_qty': 2.0,
            'bom_id': self.bom_kit_1.id})
        BomLine.create({
            'product_id': self.component_b.id,
            'product_qty': 1.0,
            'bom_id': self.bom_kit_1.id})
        BomLine.create({
            'product_id': self.component_c.id,
            'product_qty': 3.0,
            'bom_id': self.bom_kit_1.id})

        # Create a kit 'kit_parent' :
        # ---------------------------
        #
        # kit_parent --|- kit_2 x2 --|- component_d x1
        #              |             |- kit_1 x2 -------|- component_a   x2
        #              |                                |- component_b   x1
        #              |                                |- component_c   x3
        #              |
        #              |- kit_3 x1 --|- component_f x1
        #              |             |- component_g x2
        #              |
        #              |- component_e x1

        # Creating all kits
        self.kit_2 = self._create_product('Kit 2', self.uom_unit)
        self.kit_3 = self._create_product('kit 3', self.uom_unit)
        self.kit_parent = self._create_product('Kit Parent', self.uom_unit)

        # Linking the kits and the components via some 'phantom' BoMs
        bom_kit_2 = self.env['mrp.bom'].create({
            'product_tmpl_id': self.kit_2.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})

        BomLine.create({
            'product_id': self.component_d.id,
            'product_qty': 1.0,
            'bom_id': bom_kit_2.id})
        BomLine.create({
            'product_id': self.kit_1.id,
            'product_qty': 2.0,
            'bom_id': bom_kit_2.id})

        bom_kit_parent = self.env['mrp.bom'].create({
            'product_tmpl_id': self.kit_parent.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})

        BomLine.create({
            'product_id': self.component_e.id,
            'product_qty': 1.0,
            'bom_id': bom_kit_parent.id})
        BomLine.create({
            'product_id': self.kit_2.id,
            'product_qty': 2.0,
            'bom_id': bom_kit_parent.id})

        bom_kit_3 = self.env['mrp.bom'].create({
            'product_tmpl_id': self.kit_3.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})

        BomLine.create({
            'product_id': self.component_f.id,
            'product_qty': 1.0,
            'bom_id': bom_kit_3.id})
        BomLine.create({
            'product_id': self.component_g.id,
            'product_qty': 2.0,
            'bom_id': bom_kit_3.id})

        BomLine.create({
            'product_id': self.kit_3.id,
            'product_qty': 2.0,
            'bom_id': bom_kit_parent.id})

    def _create_product(self, name, uom_id, routes=()):
        p = Form(self.env['product.product'])
        p.name = name
        p.type = 'product'
        p.uom_id = uom_id
        p.uom_po_id = uom_id
        p.route_ids.clear()
        for r in routes:
            p.route_ids.add(r)
        return p.save()

        # Helper to process quantities based on a dict following this structure :
        #
        # qty_to_process = {
        #     product_id: qty
        # }

    def _process_quantities(self, moves, quantities_to_process):
        """ Helper to process quantities based on a dict following this structure :
            qty_to_process = {
                product_id: qty
            }
        """
        moves_to_process = moves.filtered(lambda m: m.product_id in quantities_to_process.keys())
        for move in moves_to_process:
            move.write({'quantity_done': quantities_to_process[move.product_id]})

    def _assert_quantities(self, moves, quantities_to_process):
        """ Helper to check expected quantities based on a dict following this structure :
            qty_to_process = {
                product_id: qty
                ...
            }
        """
        moves_to_process = moves.filtered(lambda m: m.product_id in quantities_to_process.keys())
        for move in moves_to_process:
            self.assertEquals(move.product_uom_qty, quantities_to_process[move.product_id])

    def _create_move_quantities(self, qty_to_process, components, warehouse):
        """ Helper to creates moves in order to update the quantities of components
        on a specific warehouse. This ensure that all compute fields are triggered.
        The structure of qty_to_process should be the following :

         qty_to_process = {
            component: (qty, uom),
            ...
        }
        """
        for comp in components:
            f = Form(self.env['stock.move'])
            f.name = 'Test Receipt Components'
            f.location_id = self.env.ref('stock.stock_location_suppliers')
            f.location_dest_id = warehouse.lot_stock_id
            f.product_id = comp
            f.product_uom = qty_to_process[comp][1]
            f.product_uom_qty = qty_to_process[comp][0]
            move = f.save()
            move._action_confirm()
            move._action_assign()
            move_line = move.move_line_ids[0]
            move_line.qty_done = qty_to_process[comp][0]
            move._action_done()

    def test_01_sale_mrp_kit_qty_delivered(self):
        """ Test that the quantities delivered are correct when
        a kit with subkits is ordered with multiple backorders and returns
        """

        # 'kit_parent' structure:
        # ---------------------------
        #
        # kit_parent --|- kit_2 x2 --|- component_d x1
        #              |             |- kit_1 x2 -------|- component_a   x2
        #              |                                |- component_b   x1
        #              |                                |- component_c   x3
        #              |
        #              |- kit_3 x1 --|- component_f x1
        #              |             |- component_g x2
        #              |
        #              |- component_e x1

        # Creation of a sale order for x7 kit_parent
        partner = self.env.ref('base.res_partner_1')
        f = Form(self.env['purchase.order'])
        f.partner_id = partner
        with f.order_line.new() as line:
            line.product_id = self.kit_parent
            line.product_qty = 7.0
            line.price_unit = 10

        po = f.save()
        po.button_confirm()

        # Check picking creation, its move lines should concern
        # only components. Also checks that the quantities are corresponding
        # to the PO
        self.assertEquals(len(po.picking_ids), 1)
        order_line = po.order_line[0]
        picking_original = po.picking_ids[0]
        move_lines = picking_original.move_lines
        products = move_lines.mapped('product_id')
        kits = [self.kit_parent, self.kit_3, self.kit_2, self.kit_1]
        components = [self.component_a, self.component_b, self.component_c, self.component_d, self.component_e,
                      self.component_f, self.component_g]
        expected_quantities = {
            self.component_a: 56.0,
            self.component_b: 28.0,
            self.component_c: 84.0,
            self.component_d: 14.0,
            self.component_e: 7.0,
            self.component_f: 14.0,
            self.component_g: 28.0
        }

        self.assertEquals(len(move_lines), 7)
        self.assertTrue(not any(kit in products for kit in kits))
        self.assertTrue(all(component in products for component in components))
        self._assert_quantities(move_lines, expected_quantities)

        # Process only 7 units of each component
        qty_to_process = 7
        move_lines.write({'quantity_done': qty_to_process})

        # Create a backorder for the missing componenents
        backorder_wizard = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, po.picking_ids[0].id)]})
        backorder_wizard.process()

        # Check that a backorded is created
        self.assertEquals(len(po.picking_ids), 2)
        backorder_1 = po.picking_ids - picking_original
        self.assertEquals(backorder_1.backorder_id.id, picking_original.id)

        # Even if some components are received completely,
        # no KitParent should be received
        self.assertEquals(order_line.qty_received, 0)

        # Process just enough components to make 1 kit_parent
        qty_to_process = {
            self.component_a: 1,
            self.component_c: 5,
        }
        self._process_quantities(backorder_1.move_lines, qty_to_process)

        # Create a backorder for the missing componenents
        backorder_wizard = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, backorder_1.id)]})
        backorder_wizard.process()

        # Only 1 kit_parent should be received at this point
        self.assertEquals(order_line.qty_received, 1)

        # Check that the second backorder is created
        self.assertEquals(len(po.picking_ids), 3)
        backorder_2 = po.picking_ids - picking_original - backorder_1
        self.assertEquals(backorder_2.backorder_id.id, backorder_1.id)

        # Set the components quantities that backorder_2 should have
        expected_quantities = {
            self.component_a: 48,
            self.component_b: 21,
            self.component_c: 72,
            self.component_d: 7,
            self.component_f: 7,
            self.component_g: 21
        }

        # Check that the computed quantities are matching the theorical ones.
        # Since component_e was totally processed, this componenent shouldn't be
        # present in backorder_2
        self.assertEquals(len(backorder_2.move_lines), 6)
        move_comp_e = backorder_2.move_lines.filtered(lambda m: m.product_id.id == self.component_e.id)
        self.assertFalse(move_comp_e)
        self._assert_quantities(backorder_2.move_lines, expected_quantities)

        # Process enough components to make x3 kit_parents
        qty_to_process = {
            self.component_a: 16,
            self.component_b: 5,
            self.component_c: 24,
            self.component_g: 5
        }
        self._process_quantities(backorder_2.move_lines, qty_to_process)

        # Create a backorder for the missing componenents
        backorder_wizard = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, backorder_2.id)]})
        backorder_wizard.process()

        # Check that x3 kit_parents are indeed received
        self.assertEquals(order_line.qty_received, 3)

        # Check that the third backorder is created
        self.assertEquals(len(po.picking_ids), 4)
        backorder_3 = po.picking_ids - (picking_original + backorder_1 + backorder_2)
        self.assertEquals(backorder_3.backorder_id.id, backorder_2.id)

        # Check the components quantities that backorder_3 should have
        expected_quantities = {
            self.component_a: 32,
            self.component_b: 16,
            self.component_c: 48,
            self.component_d: 7,
            self.component_f: 7,
            self.component_g: 16
        }
        self._assert_quantities(backorder_3.move_lines, expected_quantities)

        # Process all missing components
        self._process_quantities(backorder_3.move_lines, expected_quantities)

        # Validating the last backorder now it's complete.
        # All kits should be received
        backorder_3.button_validate()
        self.assertEquals(order_line.qty_received, 7.0)

        # Return all components processed by backorder_3
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=backorder_3.ids, active_id=backorder_3.ids[0],
            active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        for return_move in return_wiz.product_return_moves:
            return_move.write({
                'quantity': expected_quantities[return_move.product_id],
                'to_refund': True
            })
        res = return_wiz.create_returns()
        return_pick = self.env['stock.picking'].browse(res['res_id'])

        # Process all components and validate the picking
        wiz_act = return_pick.button_validate()
        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
        wiz.process()

        # Now quantity received should be 3 again
        self.assertEquals(order_line.qty_received, 3)

        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=return_pick.ids, active_id=return_pick.ids[0],
            active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        for move in return_wiz.product_return_moves:
            move.quantity = expected_quantities[move.product_id]
        res = return_wiz.create_returns()
        return_of_return_pick = self.env['stock.picking'].browse(res['res_id'])

        # Process all components except one of each
        for move in return_of_return_pick.move_lines:
            move.write({
                'quantity_done': expected_quantities[move.product_id] - 1,
                'to_refund': True
            })

        backorder_wizard = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, return_of_return_pick.id)]})
        backorder_wizard.process()

        # As one of each component is missing, only 6 kit_parents should be received
        self.assertEquals(order_line.qty_received, 6)

        # Check that the 4th backorder is created.
        self.assertEquals(len(po.picking_ids), 7)
        backorder_4 = po.picking_ids - (
                    picking_original + backorder_1 + backorder_2 + backorder_3 + return_of_return_pick + return_pick)
        self.assertEquals(backorder_4.backorder_id.id, return_of_return_pick.id)

        # Check the components quantities that backorder_4 should have
        for move in backorder_4.move_lines:
            self.assertEquals(move.product_qty, 1)


class TestPurchaseMrpFlow(TransactionCase):


    def test_01_purchase_mrp_anglo_saxon(self):
        """Test the price unit of a kit"""
        # This test will check that the correct journal entries are created when a consumable product in real time valuation
        # and in fifo cost method is sold in a company using anglo-saxon.
        # For this test, let's consider a product category called Test category in real-time valuation and real price costing method
        # Let's  also consider a finished product with a bom with two components: component1(cost = 20) and component2(cost = 10)
        # These products are in the Test category
        # The bom consists of 2 component1 and 1 component2
        # The invoice policy of the finished product is based on ordered quantities
        self.categ_unit = self.env.ref('uom.product_uom_categ_unit')
        self.uom_unit = self.uom_unit = self.env['uom.uom'].search([('category_id', '=', self.categ_unit.id), ('uom_type', '=', 'reference')], limit=1)
        self.company = self.env.ref('base.main_company')
        self.company.anglo_saxon_accounting = True
        self.partner = self.env.ref('base.res_partner_1')
        self.category = self.env.ref('product.product_category_1').copy({'name': 'Test category','property_valuation': 'real_time', 'property_cost_method': 'fifo'})
        account_type = self.env['account.account.type'].create({'name': 'RCV type', 'type': 'receivable'})
        self.account_receiv = self.env['account.account'].create({'name': 'Receivable', 'code': 'RCV00' , 'user_type_id': account_type.id, 'reconcile': True})
        self.account_stock = self.env['account.account'].create({'name': 'Stock', 'code': 'STK00' , 'user_type_id': account_type.id, 'reconcile': True})
        self.account_input = self.env['account.account'].create({'name': 'Input', 'code': 'INP00' , 'user_type_id': account_type.id, 'reconcile': True})
        account_expense = self.env['account.account'].create({'name': 'Expense', 'code': 'EXP00' , 'user_type_id': account_type.id, 'reconcile': True})
        account_output = self.env['account.account'].create({'name': 'Output', 'code': 'OUT00' , 'user_type_id': account_type.id, 'reconcile': True})
        self.partner.property_account_receivable_id = self.account_receiv
        self.category.property_account_income_categ_id = self.account_receiv
        self.category.property_account_expense_categ_id = account_expense
        self.category.property_stock_account_input_categ_id = self.account_input
        self.category.property_stock_account_output_categ_id = account_output
        self.category.property_stock_valuation_account_id = self.account_stock
        self.category.property_stock_journal = self.env['account.journal'].create({'name': 'Stock journal', 'type': 'purchase', 'code': 'STK00'})

        Product = self.env['product.product']
        self.finished_product = Product.create({
                'name': 'Finished product',
                'type': 'consu',
                'uom_id': self.uom_unit.id,
                'categ_id': self.category.id,
                'purchase_method': 'purchase',
                'supplier_taxes_id': [(6, 0, [])]})
        self.component1 = Product.create({
                'name': 'Component 1',
                'type': 'product',
                'uom_id': self.uom_unit.id,
                'categ_id': self.category.id,
                'supplier_taxes_id': [(6, 0, [])],
                'purchase_method': 'purchase',
                'standard_price': 20})
        self.component2 = Product.create({
                'name': 'Component 2',
                'type': 'product',
                'uom_id': self.uom_unit.id,
                'categ_id': self.category.id,
                'supplier_taxes_id': [(6, 0, [])],
                'purchase_method': 'purchase',
                'standard_price': 10})
        self.bom = self.env['mrp.bom'].create({
                'product_tmpl_id': self.finished_product.product_tmpl_id.id,
                'product_qty': 1.0,
                'type': 'phantom'})
        BomLine = self.env['mrp.bom.line']
        BomLine.create({
                'product_id': self.component1.id,
                'product_qty': 2.0,
                'bom_id': self.bom.id})
        BomLine.create({
                'product_id': self.component2.id,
                'product_qty': 1.0,
                'bom_id': self.bom.id})
        # Create a PO for a specific partner for three units of the finished product
        po_vals = {
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {'name': self.finished_product.name, 'product_id': self.finished_product.id, 'product_qty': 3, 'product_uom': self.finished_product.uom_id.id, 'price_unit': 60.0, 'date_planned': fields.Datetime.now()})],
            'company_id': self.company.id,
            'currency_id': self.company.currency_id.id,
        }
        self.po = self.env['purchase.order'].create(po_vals)
        # Validate the PO
        self.po.button_confirm()
        self.invoice = self.env['account.invoice'].create({
            'partner_id': self.partner.id,
            'purchase_id': self.po.id,
            'account_id': self.account_receiv.id,
            'type': 'in_invoice'
        })
        self.invoice.purchase_order_change()
        self.invoice.action_invoice_open()
        aml = self.invoice.move_id.line_ids
        aml_input = aml.filtered(lambda l: l.account_id.id == self.account_input.id)
        self.assertEqual(aml_input.debit, 180, "Cost of Good Sold entry missing or mismatching")
