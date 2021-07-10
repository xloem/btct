import sys
if sys.version_info < (3,6):
    sys.exit("I'm not sure tables will function correctly without python 3.6 dict ordering")
    # this has to do with how kwparams are used to pass the column names in.
    # using tuples instead of kwparams would resolve the limitation

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
                if col.foreign is not None and type(val) is not Table.Row:
                    setattr(self, key, Table.Row(Table.tables[col.foreign], val))
                else:
                    #if type(val) is Table.Row:
                        #print(val,'is',val.id)
                    setattr(self, key, val)
            self.addr = self.id
        def __getattr__(self, attr):
            #print(self.table.name, self.id, 'getattr')
            vals = c.execute(
                'SELECT ' + 
                ', '.join((col.name for col in self.table.cols[1:])) +
                ' FROM ' + self.table.name + ' WHERE id == ?',
                (hex2b(self.id),)
            ).fetchone()
            if vals is None:
                raise LookupError(self.table.name + ' not found: ' + self.id)
            result = {}
            for col in self.table.cols[1:]:
                val = vals[col.idx - 1]
                if col.foreign is not None:
                    val = b2hex(val)
                    val = Table.Row(Table.tables[col.foreign], val)
                result[col.name] = val
                setattr(self, col.name, val)
            #print(self.table.name, 'EXPAND', self.id, result)
            return result[attr]
        def __str__(self):
            if self.table.keycolidx > 1:
                return getattr(self, self.table.cols[1].name)
            elif self.table.keycolidx < self.table.numcols:
                #print([getattr(self, col.name) for col in self.table.cols[1:]])
                return '/'.join((str(getattr(self, col.name)) for col in self.table.cols[1:]))
            else:
                return self.id

    class Column:
        def __init__(self, idx, name, sqltype, foreign = None):
            self.idx = idx
            self.name = name
            self.type = type
            self.sqltype = sqltype
            self.foreign = foreign

    def __init__(self, name, *strcols, **coltables):
        #print('TABLE',strcols,coltables)
        self.coltables = coltables
        self.keycolidx = 1 + len(strcols)
        self.colslist = ([Table.Column(0, 'id', 'BLOB PRIMARY KEY')] +
            [
                    Table.Column(idx + 1, col, 'TEXT')
                    for idx, col in enumerate(strcols)
            ] +
            [
                    Table.Column(idx + self.keycolidx, coltable[0], 'BLOB', coltable[1])
                    for idx, coltable in enumerate(coltables.items())
            ])
        self.colsdict = {col.name:col for col in self.colslist}
        self.cols = self.colslist
        self.numcols = len(self.cols)
        self.name = name
        c.execute(
            'CREATE TABLE IF NOT EXISTS ' + self.name + '(' +
            ', '.join((col.name + ' ' + col.sqltype for col in self.cols)) +
            ')')
        Table.tables[self.name] = self
    def ensure(self, *vals):
        vals = [*vals]
        sqlite_vals = [*vals]
        for idx in (0,*range(self.keycolidx, self.numcols)):
            val = sqlite_vals[idx]
            if type(val) is Table.Row:
                val = val.id
            sqlite_vals[idx] = hex2b(val)
        #print(self.name, 'ensure-insert', {self.cols[idx].name:sqlite_vals[idx] for idx in range(self.numcols)})
        with c:
            c.execute(
                'INSERT OR IGNORE INTO ' + self.name + ' VALUES(' + 
                ', '.join('?' * self.numcols) +
                ')',
                sqlite_vals
            )
        return Table.Row(self, *vals)
    def __getitem__(self, id):
        return Table.Row(self, id)
    def __call__(self, *params, **kwparams):
        for col, val in zip(self.cols, params):
            kwparams[col.name] = val
        #print(self.name, 'call', kwparams)
        if len(kwparams) == len(self.cols):
            #print('call going to ensure')
            return self.ensure(*(kwparams[col.name] for col in self.cols))
        sqlite_cols = []
        sqlite_vals = []
        for col, val in kwparams.items():
            if self.coltables[col].foreign is not None:
                if type(val) is Table.Row:
                    val = val.id
                val = hex2b(val)
            sqlite_cols.append(col)
            sqlite_vals.append(val)
        params = c.execute(
            'SELECT ' + ', '.join((col.name for col in self.cols)) + ' FROM ' + self.name + ' WHERE ' +
            ' AND '.join(
                key + ' = ?'
                for key in sqlite_cols
            ), sqlite_vals
        ).fetchone()
        return Table.Row(self, *params)

token = Table('token', 'symbol')
pair = Table('pair', token0='token', token1='token', dex='dex')
dex = Table('dex', 'name')
