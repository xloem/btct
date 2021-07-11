import sys
if sys.version_info < (3,6):
    # this has to do with how kwparams are used to pass the column names in concisely.
    # using tuples instead of kwparams would resolve the limitation
    sys.exit("I'm not sure tables will function correctly without python 3.6 dict ordering")

import pickle
import sqlite3
import typing
from typing import Optional

from web3 import _utils as utils, Web3
from hexbytes import HexBytes

c = sqlite3.connect('dex.sqlite')

def hex2b(hex):
    return HexBytes(hex)
def b2hex(b):
    if type(b) is not HexBytes:
        b = HexBytes(b)
    if len(b) == 20:
        return Web3.toChecksumAddress(b.hex())
    else:
        return b.hex()

def o2sql(o):
    if type(o) is Table.Row:
        return hex2b(o.id)
    else:
        return o


class Table:
    tables = {}
    class Row:
        def __init__(self, table, *params, **kwparams):
            self.table = table
            for col, val in zip(table.cols, params):
                kwparams[col.name] = val
            self.kwparams = kwparams
            #print(table.name, 'ROW', {key:str(val) for key,val in kwparams.items()})
            for key, val in kwparams.items():
                col = self.table.colsdict[key]
                if col.foreign is not None:
                    if type(val) is not Table.Row:
                        val = Table.Row(Table.tables[col.foreign], val)
                        kwparams[key] = val
                elif col.primary:
                    if isinstance(val, bytes):
                        val = b2hex(val)
                        kwparams[key] = val
                elif isinstance(val, bytes) and col.type is int:
                    val = pickle.decode_long(val)
                setattr(self, key, val)
        @property
        def addr(self):
            return self.id
        def __iter__(self):
            return self._select()
        def ascending(self, key):
            return self._orderby(key, 'ASC')
        def descending(self, key):
            return self._orderby(key, 'DESC')
        def _orderby(self, key, direction = 'ASC'):
            return self._select('ORDER BY `' + key + '` ' + direction)
        def _select(self, wherestr = '', *wherevals):
            return (
                Table.Row(self.table, *row)
                for row in self._selectraw(wherestr, *wherevals)
            )
        def _selectraw(self, wherestr = '', *wherevals):
            if 'id' in self.kwparams:
                wherestr = 'WHERE id == ? ' + wherestr
                wherevals = (hex2b(self.id), *wherevals)
            elif len(self.kwparams):
                wherestr = (
                    'WHERE `' +
                    'AND `'.join(
                        key + '` == ? '
                        for key in self.kwparams.keys()
                    )
                ) + wherestr
                wherevals = (
                    *(o2sql(getattr(self, key)) for key in self.kwparams.keys()),
                    *wherevals
                )
            query = 'SELECT * FROM ' + self.table.name + ' ' + wherestr
            #print(query, wherevals)
            return c.execute(query, wherevals)
        def __len__(self):
            return len(self._selectraw().fetchall())
        def __bool__(self):
            return self._selectraw().fetchone() is not None
        def __getattr__(self, attr):
            #print(self.table.name, self.id, 'getattr')
            vals = None
            for row in self._select():
                if vals is not None:
                    raise AttributeError(attr)
                vals = row.kwparams
            if vals is None:
                raise LookupError(self.table.name + ' not found: ' + str(self.kwparams))
            for col, val in vals.items():
                setattr(self, col, val)
            self.kwparams = vals
            #print(self.table.name, 'EXPAND', self.id, result)
            return vals[attr]
        def __str__(self):
            if self.table.numrequiredcols - self.table.numforeigncols > 0:
                for col in self.table.cols:
                    # 2021-07-11 col.primary has a type of str, the id
                    if not col.primary and col.type is str:
                        val = getattr(self, col.name)
                        if val is not None:
                            return val
            if self.table.numforeigncols > 0:
                #print([getattr(self, col.name) for col in self.table.cols[1:]])
                return '/'.join((str(getattr(self, col.name)) for col in self.table.cols[1:] if col.foreign is not None))
            else:
                for col in self.table.cols:
                    if col.type is not str and not isinstance(col.type, bytes):
                        val = getattr(self, col.name)
                        if val is not None:
                            return str(val)
            return self.id

    class Column:
        def __init__(self, idx, name, type, sqltype, foreign = None, primary = False, optional = False):
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
        self.colslist = ([Table.Column(0, 'id', str, 'BLOB', None, True)] +
            [
                    Table.Column(idx + 1, col, 'TEXT')
                    for idx, col in enumerate(strcols)
            ])
        self.numrequiredcols = 0
        self.numforeigncols = 0
        self.primarykeys = ['id']
        for col, specifier in colspecifiers.items():
            primary = False
            big = False
            optional = False
            sqltype = 'BLOB'
            foreign = None
            while isinstance(specifier, typing._Final):
                if typing.get_origin(specifier) is typing.Union and typing.get_args(specifier)[1] is type(None):
                    # Optional
                    optional = True
                    specifier = typing.get_args(specifier)[0]
                if typing.get_origin(specifier) is PrimaryKey:
                    # Primary
                    primary = True
                    specifier = typing.get_args(specifier)[0]
                if typing.get_origin(specifier) is Big:
                    # Primary
                    big = True
                    specifier = typing.get_args(specifier)[0]
                if type(specifier) is typing.ForwardRef:
                    # non-type string argument
                    specifier = specifier.__forward_arg__
            if big:
                sqlype = 'BLOB'
            elif specifier is int:
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
                specifier = Table.Row
                self.coltables[col] = foreign
                self.numforeigncols += 1
            else:
                raise NotImplementedError("column specifier: " + repr(specifier))
            if primary:
                self.primarykeys.append(col)
            if not optional:
                sqltype += ' NOT NULL'
                self.numrequiredcols += 1
            self.colslist.append(
                Table.Column(len(self.colslist), col, specifier, sqltype, foreign, False, optional)
            )
        self.colsdict = {col.name:col for col in self.colslist}
        self.cols = self.colslist
        self.numcols = len(self.cols)
        self.name = __name
        c.execute(
            'CREATE TABLE IF NOT EXISTS ' + self.name + '(' +
            ', '.join(('`' + col.name + '` ' + col.sqltype for col in self.cols)) +
            ', PRIMARY KEY (`' + '`, `'.join(self.primarykeys) + '`)' +
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
            if (col.foreign is not None or col.primary) and not isinstance(val, bytes):
                val = hex2b(val)
            elif col.type is int and col.sqltype == 'BLOB':
                val = pickle.encode_long(val)
            sqlite_vals.append(val)
        #print(self.name, 'ensure-insert', {self.cols[idx].name:sqlite_vals[idx] for idx in range(self.numcols)})
        cres = c.execute(
            'INSERT OR IGNORE INTO ' + self.name + ' (`' +
                '`, `'.join(kwvals.keys())
            + '`) VALUES(' +
                ', '.join('?' * len(sqlite_vals)) +
            ')',
            sqlite_vals
        )
        return Table.Row(self, **kwvals)
    def __getitem__(self, id):
        if len(self.primarykeys) > 1:
            kwparams = {
                key: val
                for key, val in zip(id, self.primarykeys)
            }
            return Table.Row(self, **kwparams)
        else:
            return Table.Row(self, id)
    def __call__(self, *params, **kwparams):
        for col, val in zip(self.cols, params):
            kwparams[col.name] = val
        #print(self.name, 'call', kwparams)
        if len(kwparams) >= self.numrequiredcols:
            #print('call going to ensure')
            return self.ensure(**kwparams)
        return Table.Row(self, *params, **kwparams)
    def __contains__(self, id):
        return bool(self[id])
    def __iter__(self):
        return iter(self())
    def commit(self):
        c.commit();
    def __del__(self):
        c.commit();
    def __enter__(self, *params):
        return c.__enter__(*params)
    def __exit__(self, *params):
        return c.__exit__(*params)

class PrimaryKey(typing.Generic[typing.T]):
    pass

#class Unique(typing.Generic[typing.T]):
#    pass

class Big(typing.Generic[typing.T]):
    pass

token = Table('token', symbol=str)
dex = Table('dex', name=str)
acct = Table('acct')
block = Table('block', num=int)
pair = Table('pair', token0='token', token1='token', dex='dex', index=Optional[int])

trade = Table('trade',
        # for ordering
        blocknum = int,
        blockidx = int,
        txidx = PrimaryKey[int],
        pair = PrimaryKey['pair'],

        block = 'block',
        trader0 = Optional['acct'],
        trader1 = Optional['acct'],
        token0_to_trader1 = Optional[int],
        token1_to_trader1 = Optional[int],
        const0 = Optional[Big[int]],
        const1 = Optional[Big[int]])

