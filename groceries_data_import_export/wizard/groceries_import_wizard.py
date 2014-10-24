# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import os
import random

from openerp.osv import fields, osv
from openerp.tools.translate import _
import base64
import openerp.tools as tools
import xlrd
from openerp.osv.orm import TransientModel

'''
Created on 23/10/2014
@author: Antonio Mauri Garcia
'''

class groceries_import_wizard(TransientModel):

    worksheet = None
    num_rows = None
    num_cells = None
    SEARCH_VALS = [u'Name', u'Product_UPC']

    def _get_image(self, cr, uid, context=None):
        path = os.path.join('groceries_data_import_export', 'res', 'config_pixmaps', '%d.png' % random.randrange(1, 4))
        image_file = tools.file_open(path, 'rb')
        try:
            file_data = image_file.read()
            return base64.encodestring(file_data)
        finally:
            image_file.close()

    def _get_image_fn(self, cr, uid, ids, name, args, context=None):
        image = self._get_image(cr, uid, context)
        return dict.fromkeys(ids, image)

    _name = "groceries.import.wizard"
    _columns = {
        'product_category_file': fields.binary('Product Category File', filename="module_filename", filters='*.xlsx',
                                               required=True),
        'config_logo': fields.function(_get_image_fn, string='Image', type='binary', readonly=True),
        'category_product_rel': fields.char(string='Category Product Rel', size=1000000),
    }

    _defaults = {
        'config_logo': _get_image
    }

    def check_product_category_step1(self, cr, uid, ids, context= None):
        obj = self.browse(cr, uid, ids[0])

        if obj.product_category_file:
            self.open_worbook(obj.product_category_file)
            find_res = self.find_column_by_name()
            self.persist_data(cr, uid, find_res, ids[0], context)
            obj = self.browse(cr, uid, ids[0])
            return {
                 'view_type': 'form',
                 'name': 'Groceries Import Process Step 2. Select Product File',
                 'view_mode': 'form',
                 'res_model': 'groceries.import.wizard1',
                 'views': [],
                 'type': 'ir.actions.act_window',
                 'target': 'new',
                 'context': {
                     'category_product_rel': obj.category_product_rel,
                 }
            }


    def open_worbook(self, binary_file):
        res = {}

        str_file = base64.decodestring(binary_file)
        workbook = xlrd.open_workbook(file_contents=str_file, encoding_override='cp1252')
        self.worksheet = workbook.sheet_by_index(0)
        self.num_rows = self.worksheet.nrows - 1
        self.num_cells = self.worksheet.ncols - 1

    def find_column_by_name(self):
        result = {}
        curr_row = -1
        quantity_of_columns = len(self.SEARCH_VALS)
        counter = 0

        while curr_row < self.num_rows:
            curr_row += 1
            #row = self.worksheet.row(curr_row)
            curr_cell = -1
            if counter >= quantity_of_columns:
                break
            else:
                while curr_cell < self.num_cells:
                    curr_cell += 1
                    # Cell Types: 0=Empty, 1=Text, 2=Number, 3=Date, 4=Boolean, 5=Error, 6=Blank
                    #cell_type = worksheet.cell_type(curr_row, curr_cell)
                    #cell_name = xlrd.cellname(curr_row, curr_cell)
                    cell_value = self.worksheet.cell_value(curr_row, curr_cell)
                    if cell_value:
                        if cell_value in self.SEARCH_VALS:
                            counter += 1
                            result[cell_value] = {'row': curr_row, 'col': curr_cell}
        return result

    def persist_data(self, cr, uid, source, id, context=None):
        result = {}
        source_name = source.get(u'Name')
        curr_row = source_name.get('row')
        category_product_rel = ''

        while curr_row < self.num_rows:
            curr_row += 1
            curr_cell = source_name.get('col')
            while curr_cell < self.num_cells + 1:
                cell_str_value = self.worksheet.cell_value(int(curr_row), int(curr_cell))
                if curr_cell != self.num_cells:
                    # id_category = self.pool.get('product.category').create(cr, uid, {'name': cell_str_value})
                    if cell_str_value.rindex('(') > 0:
                        cell_str_value = cell_str_value[cell_str_value.index(')')+2:cell_str_value.rindex('(')-1]
                    else:
                        cell_str_value = cell_str_value[cell_str_value.index(')')+2:]
                    arr_tree_catgorie = cell_str_value.split('/')
                    if len(arr_tree_catgorie) == 1:
                        cr.execute('insert into product_category (name) values (%s) returning id', (cell_str_value,))
                        id_category = cr.fetchone()[0]
                        category_product_rel = category_product_rel + str(id_category) + ':'
                    else:
                        parent_id = False
                        for cat in arr_tree_catgorie:
                            if not parent_id:
                                cr.execute('insert into product_category (name) values (%s) returning id', (cat,))
                                parent_id = cr.fetchone()[0]
                            else:
                                cr.execute('insert into product_category (name,parent_id) values (%s,%s) returning id',
                                           (cat, parent_id))
                                parent_id = cr.fetchone()[0]
                        category_product_rel = category_product_rel + str(parent_id) + ':'

                else:
                    category_product_rel = category_product_rel + str(cell_str_value) + ','
                curr_cell += 1
        self.write(cr, uid, [id], {'category_product_rel': category_product_rel})
groceries_import_wizard()

class groceries_import_wizard_1(TransientModel):

    def _get_image(self, cr, uid, context=None):
        path = os.path.join('groceries_data_import_export', 'res', 'config_pixmaps', '%d.png' % random.randrange(1, 4))
        image_file = tools.file_open(path, 'rb')
        try:
            file_data = image_file.read()
            return base64.encodestring(file_data)
        finally:
            image_file.close()

    def _get_image_fn(self, cr, uid, ids, name, args, context=None):
        image = self._get_image(cr, uid, context)
        return dict.fromkeys(ids, image)

    _name = "groceries.import.wizard1"
    _columns = {
        'product_file': fields.binary('Product File', filename="module_filename", filters='*.xlsx',
                                               required=True),
        'config_logo': fields.function(_get_image_fn, string='Image', type='binary', readonly=True),
    }

    _defaults = {
        'config_logo': _get_image
    }

    def check_product_step2(self, cr, uid, ids, context= None):
        return False

groceries_import_wizard_1()
