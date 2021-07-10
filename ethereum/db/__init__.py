import sys
if sys.version_info < (3,6):
    # this has to do with how kwparams are used to pass the column names in concisely.
    # using tuples instead of kwparams would resolve the limitation
    sys.exit("I'm not sure tables will function correctly without python 3.6 dict ordering")

import typing
from typing import Optional

import sqlite3
from web3 import _utils as utils

c = sqlite3.connect('dex.sqlite')

def hex2b(hex):
    return utils.encoding.to_bytes(hexstr=str(hex))
def b2hex(b):
    return '0x' + b.hex()


class Table:
    tables = {}
    class Row:
        def __init__(self, table, *params, **kwparams):
            self.table = table
            for col, val in zip(table.cols, params):
                kwparams[col.name] = val
            #print(table.name, 'ROW', {key:str(val) for key,val in kwparams.items()})
            for key, val in kwparams.items():
                col = self.table.colsdict[key]
                if col.foreign is not None:
                    if type(val) is not Table.Row:
                        val = Table.Row(Table.tables[col.foreign], val)
                elif col.primary:
                    if type(val) is bytes:
                        val = b2hex(val)
                setattr(self, key, val)
            self.addr = self.id
        def __iter__(self, attr):
            for row in c.execute(
                'SELECT ' + 
                ', '.join((col.name for col in self.table.cols[1:])) +
                ' FROM ' + self.table.name + ' WHERE id == ?',
                (hex2b(self.id),)
            ):
                yield Table.Row(self.table, *row)
        def __getattr__(self, attr):
            #print(self.table.name, self.id, 'getattr')
            vals = c.execute(
                'SELECT ' + 
                ', '.join((col.name for col in self.table.cols)) +
                ' FROM ' + self.table.name + ' WHERE id == ?',
                (hex2b(self.id),)
            ).fetchone()
            if vals is None:
                raise LookupError(self.table.name + ' not found: ' + self.id)
            result = {}
            for col, val in zip(self.table.cols, vals):
                if col.foreign is not None or col.primary:
                    val = b2hex(val)
                if col.foreign is not None:
                    val = Table.Row(Table.tables[col.foreign], val)
                result[col.name] = val
                setattr(self, col.name, val)
            #print(self.table.name, 'EXPAND', self.id, result)
            return result[attr]
        def __str__(self):
            if self.table.numrequiredcols - self.table.numforeigncols > 0:
                for col in self.table.cols:
                    if col.foreign is None and not col.optional and not col.primary:
                        return str(getattr(self, col.name))
            if self.table.numforeigncols > 0:
                #print([getattr(self, col.name) for col in self.table.cols[1:]])
                return '/'.join((str(getattr(self, col.name)) for col in self.table.cols[1:] if col.foreign is not None))
            else:
                return self.id

    class Column:
        def __init__(self, idx, name, sqltype, foreign = None, primary = False, optional = False):
            self.idx = idx
            self.name = name
            self.type = type
            self.sqltype = sqltype
            self.foreign = foreign
            self.primary = primary
            self.optional = optional

    def __init__(self, __name, *strcols, **colspecifiers):
        #print('TABLE',strcols,coltables)
        self.coltables = {}
        self.colslist = ([Table.Column(0, 'id', 'BLOB PRIMARY KEY', None, True)] +
            [
                    Table.Column(idx + 1, col, 'TEXT')
                    for idx, col in enumerate(strcols)
            ])
        self.numrequiredcols = 0
        self.numforeigncols = 0
        for col, specifier in colspecifiers.items():
            optional = False
            sqltype = 'BLOB'
            foreign = None
            if typing.get_origin(specifier) is typing.Union and typing.get_args(specifier)[1] is type(None):
                optional = True
                specifier = typing.get_args(specifier)[0]
            if specifier is int:
                sqltype = 'INTEGER'
            elif specifier is float:
                sqltype = 'REAL'
            elif specifier is str:
                sqltype = 'TEXT'
            elif specifier is bytes:
                sqltype = 'BLOB'
            elif type(specifier) is str: # a foreign key, specifier is name of table
                sqltype = 'BLOB'
                foreign = specifier
                self.coltables[col] = foreign
                self.numforeigncols += 1
            else:
                raise NotImplementedError("column specifier: " + repr(specifier))
            if not optional:
                sqltype += ' NOT NULL'
                self.numrequiredcols += 1
            self.colslist.append(
                Table.Column(len(self.colslist), col, sqltype, foreign, False, optional)
            )
        self.colsdict = {col.name:col for col in self.colslist}
        self.cols = self.colslist
        self.numcols = len(self.cols)
        self.name = __name
        c.execute(
            'CREATE TABLE IF NOT EXISTS ' + self.name + '(' +
            ', '.join(('`' + col.name + '` ' + col.sqltype for col in self.cols)) +
            ')')
        Table.tables[self.name] = self
    def ensure(self, *vals, **kwvals):
        for col, val in zip(self.cols, vals):
            kwvals[col.name] = val
        sqlite_vals = []
        for key, val in kwvals.items():
            col = self.colsdict[key]
            if type(val) is Table.Row:
                val = val.id
            if col.foreign is not None or col.primary:
                val = hex2b(val)
            sqlite_vals.append(val)
        #print(self.name, 'ensure-insert', {self.cols[idx].name:sqlite_vals[idx] for idx in range(self.numcols)})
        c.execute(
            'INSERT OR IGNORE INTO ' + self.name + ' (`' +
                '`, `'.join(kwvals.keys())
            + '`) VALUES(' + 
                ', '.join('?' * len(sqlite_vals)) +
            ')',
            sqlite_vals
        )
        return Table.Row(self, **kwvals)
    def __getitem__(self, id):
        return Table.Row(self, id)
    def __call__(self, *params, **kwparams):
        for col, val in zip(self.cols, params):
            kwparams[col.name] = val
        #print(self.name, 'call', kwparams)
        if len(kwparams) >= self.numrequiredcols:
            #print('call going to ensure')
            return self.ensure(**kwparams)
        sqlite_cols = []
        sqlite_vals = []
        for col, val in kwparams.items():
            col = self.coltables[col]
            if col.foreign is not None or col.primary:
                if type(val) is Table.Row:
                    val = val.id
                val = hex2b(val)
            sqlite_cols.append(col.name)
            sqlite_vals.append(val)
        params = c.execute(
            'SELECT ' + ', '.join((col.name for col in self.cols)) + ' FROM ' + self.name + ' WHERE ' +
            ' AND '.join(
                key + ' = ?'
                for key in sqlite_cols
            ), sqlite_vals
        ).fetchone()
        return Table.Row(self, *params)
    def __iter__(self):
        for row in c.execute('SELECT * FROM ' + self.name):
            yield Table.Row(self, *row)
    def commit(self):
        c.commit();
    def __del__(self):
        c.commit();
    def __enter__(self, *params):
        return c.__enter__(*params)
    def __exit__(self, *params):
        return c.__exit__(*params)

token = Table('token', symbol=str)
pair = Table('pair', token0='token', token1='token', dex='dex', index=Optional[int])
dex = Table('dex', name=str)
