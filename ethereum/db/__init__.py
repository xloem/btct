import sys
if sys.version_info < (3,6):
    # this has to do with how kwparams are used to pass the column names in concisely.
    # using tuples instead of kwparams would resolve the limitation
    sys.exit("I'm not sure tables will function correctly without python 3.6 dict ordering")

import binascii
import pickle
import sqlite3
import typing
from typing import Optional

from web3 import _utils as utils, Web3
from hexbytes import HexBytes

c = sqlite3.connect('dex.sqlite')
#c_orig = c
#old_ex = c_orig.execute
#c = lambda: None
#c.commit = c_orig.commit
#c.execute = old_ex
#def ex_wrapper(*params, **kwparams):
#    print('SQL', *params, kwparams)
#    result = old_ex(*params, **kwparams)
#    print(' ->', result)
#    return result
#c.execute = ex_wrapper

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
            if 'addr' in kwparams and 'id' not in kwparams:
                kwparams['id'] = kwparams['addr']
                del kwparams['addr']
            if 'hash' in kwparams and 'id' not in kwparams:
                kwparams['id'] = kwparams['hash']
                del kwparams['hash']
            #print(self.table.name, kwparams)
            if 'id' in kwparams:
                try:
                    hex2b(kwparams['id'])
                except binascii.Error:
                    found = False
                    id = kwparams['id']
                    for col in self.table.cols:
                        if not col.foreign:
                            if col.type is type(id) and col.name not in kwparams:
                                found = True
                        else:
                            table = Table.tables[col.foreign]
                            try:
                                if table(id):
                                    found = True
                            except binascii.Error:
                                pass
                        if found:
                            kwparams[col.name] = id
                            del kwparams['id']
                            break

                    if 'id' in kwparams:
                        raise

            self.kwparams = kwparams
            #print(table.name, 'ROW', {key:str(val) for key,val in kwparams.items()})
            self._colstoattrs(kwparams)
        def __call__(self, *params, **kwparams):
            for col, val in zip(self.table.cols, params):
                kwparams[col.name] = val
            for col, val in self.kwparams.items():
                if col not in kwparams:
                    kwparams[col] = val
            return self.table(**kwparams)
        def _colstoattrs(self, kwparams):
            for key, val in kwparams.items():
                col = self.table.colsdict[key]
                if col.foreign is not None:
                    if type(val) is not Table.Row and val is not None:
                        val = Table.Row(Table.tables[col.foreign], val)
                        kwparams[key] = val
                elif col.primary:
                    if isinstance(val, bytes):
                        val = b2hex(val)
                        kwparams[key] = val
                elif isinstance(val, bytes) and col.type is int: # Big
                    val = pickle.decode_long(val)
                    kwparams[key] = val
                super().__setattr__(key, val)
        @property
        def addr(self):
            return self.id
        @property
        def hash(self):
            return self.id
        def __iter__(self):
            return self._select()
        def ascending(self, key, wherestr = '', *wherevals, limit = None, subkey = None):
            return self._orderby(key, 'ASC', wherestr, *wherevals, limit = limit, subkey = subkey)
        def descending(self, key, wherestr = '', *wherevals, limit = None, subkey = None):
            return self._orderby(key, 'DESC', wherestr, *wherevals, limit = limit, subkey = subkey)
        def _orderby(self, key, direction = 'ASC', wherestr = '', *wherevals, limit = None, subkey = None):
            if limit is not None:
                direction += ' LIMIT ' + str(limit)
            if subkey is None:
                key = '`' + key + '`'
            else:
                subkeytable = self.table.colsdict[key].foreign
                key = '(SELECT `' + subkey + '` FROM ' + subkeytable + ' WHERE ' + subkeytable + '.id = `' + key + '`)'
            result = self._select(wherestr, 'ORDER BY ' + key + ' ' + direction, *wherevals)
            return result
        def _select(self, wherestr = '', morestr = '', *wherevals):
            return (
                Table.Row(self.table, *row)
                for row in self._selectraw(wherestr, morestr, *wherevals)
            )
        def _where(self, wherestr = '', morestr = '', *wherevals):
            if 'id' in self.kwparams:
                if wherestr:
                    wherestr = ' AND ' + wherestr
                wherestr = 'id == ?' + wherestr
                wherevals = (hex2b(self.id), *wherevals)
            elif len(self.kwparams):
                if wherestr:
                    wherestr = ' AND ' + wherestr
                wherestr = (
                    '`' +
                    'AND `'.join(
                        key + '` == ? '
                        for key in self.kwparams.keys()
                    )
                ) + wherestr
                wherevals = (
                    *(o2sql(getattr(self, key)) for key in self.kwparams.keys()),
                    *wherevals
                )
            if wherestr:
                wherestr = ' WHERE ' + wherestr
            if morestr:
                wherestr = wherestr + ' ' + morestr
            return wherestr, wherevals
        def _selectraw(self, wherestr = '', morestr = '', *wherevals):
            wherestr, wherevals = self._where(wherestr, morestr, *wherevals)
            query = 'SELECT * FROM ' + self.table.name + ' ' + wherestr
            #print(query, wherevals)
            result = c.execute(query, wherevals)
            #print('->', result.rowcount)
            return result
        def _update(self, **kwparams):
            wherestr, wherevals = self._where()
            sqlite_vals = []
            for key, val in kwparams.items():
                col = self.table.colsdict[key]
                if type(val) is Table.Row:
                    val = val.id
                if (col.foreign is not None or col.primary) and not isinstance(val, bytes):
                    val = hex2b(val)
                elif col.type is int and col.sqltype == 'BLOB': # Big
                    val = pickle.encode_long(val)
                sqlite_vals.append(val)
            query = 'UPDATE ' + self.table.name + ' SET `' + ', `'.join(key + '` = ?' for key in kwparams.keys()) + ' ' + wherestr
            #print(query, *sqlite_vals, *wherevals)
            result = c.execute(query, (*sqlite_vals, *wherevals))
        def __conform__(self, protocol):
            if protocol is sqlite3.PrepareProtocol:
                return self.id
            else:
                raise AttributeError(self, '__conform__')
        def __len__(self):
            return len(self._selectraw().fetchall())
        def __bool__(self):
            return self._selectraw().fetchone() is not None
        def __getattr__(self, attr):
            #print(self.table.name, self.id, 'getattr', attr)
            vals = None
            for row in self._select():
                if vals is not None:
                    raise LookupError('multiple ' + self.table.name + 's: ' + str(self.kwparams))
                vals = row.kwparams
            if vals is None:
                raise LookupError(self.table.name + ' not found: ' + str(self.kwparams))
            self._colstoattrs(vals)
            self.kwparams = vals
            #print(self.table.name, 'EXPAND', self.id, result)
            return vals[attr]
        #def __setattr__(self, attr, value):
        #    self._update(**{attr:value})
        def __getitem__(self, item):
            return getattr(self, item)
        def __setitem__(self, item, value):
            #return setattr(self, item, value)
            self._update(**{item:value})
        def __repr__(self):
            return str(self)
        def __str__(self):
            if self.table.numrequiredcols - self.table.numforeignrequiredcols > 1:
                for col in self.table.cols:
                    # 2021-07-11 col.primary has a type of str, the id
                    if not col.primary and col.type is str:
                        val = getattr(self, col.name)
                        if val is not None:
                            return val
            if self.table.numforeignrequiredcols > 0:
                #print([getattr(self, col.name) for col in self.table.cols[1:]])
                return '/'.join((str(getattr(self, col.name)) for col in self.table.cols[1:] if col.foreign is not None and not col.optional))
            else:
                for col in self.table.cols:
                    if col.type is not str and not isinstance(col.type, bytes):
                        val = getattr(self, col.name)
                        if val is not None:
                            return str(val)
            return self.id

    class Column:
        def __init__(self, idx, name, type, sqltype, foreign = None, primary = False, optional = False, index = False):
            self.idx = idx
            self.name = name
            self.type = type
            self.sqltype = sqltype
            self.foreign = foreign
            self.primary = primary
            self.optional = optional
            self.index = index

    def __init__(self, __name, *strcols, **colspecifiers):
        #print('TABLE',strcols,coltables)
        self.coltables = {}
        self.colslist = ([Table.Column(0, 'id', str, 'BLOB', None, True)] +
            [
                    Table.Column(idx + 1, col, 'TEXT')
                    for idx, col in enumerate(strcols)
            ])
        self.numrequiredcols = 1
        self.numforeigncols = 0
        self.numforeignrequiredcols = 0
        self.primarykeys = ['id']
        for col, specifier in colspecifiers.items():
            primary = False
            big = False
            optional = False
            index = False
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
                if typing.get_origin(specifier) is Index:
                    # Index
                    index = True
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
                if not optional:
                    self.numforeignrequiredcols += 1
            else:
                raise NotImplementedError("column specifier: " + repr(specifier))
            if primary:
                self.primarykeys.append(col)
            if not optional:
                sqltype += ' NOT NULL'
                self.numrequiredcols += 1
            self.colslist.append(
                Table.Column(len(self.colslist), col, specifier, sqltype, foreign, False, optional, index)
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
        sql_cols = [*c.execute('PRAGMA table_info(' + self.name + ')')]
        for idx, col in enumerate(self.cols):
            if idx >= len(sql_cols):
                c.execute('ALTER TABLE ' + self.name + ' ADD COLUMN `' + col.name + '` ' + col.sqltype)
                continue
            cid, sqlname, sqltype, notnull, dflt_value, pk = sql_cols[idx]
            if notnull:
                sqltype += ' NOT NULL'
            if sqlname != col.name or sqltype != col.sqltype:
                raise Exception(self.name + ' col ' + col.name + ' ' + col.sqltype + ' mismatches sql of ' + sqlname + ' ' + sqltype)
            if col.index:
                c.execute('CREATE INDEX IF NOT EXISTS `index_' + col.name + '` ON ' + self.name + '(`' + col.name + '`)')
        Table.tables[self.name] = self

    def ensure(self, *vals, **kwvals):
        obj = Table.Row(self, *vals,**kwvals)
        if obj:
            return obj
        for col, val in zip(self.cols, vals):
            kwvals[col.name] = val
        sqlite_vals = []
        for key, val in kwvals.items():
            col = self.colsdict[key]
            if type(val) is Table.Row:
                val = val.id
            if (col.foreign is not None or col.primary) and not isinstance(val, bytes):
                val = hex2b(val)
            elif col.type is int and col.sqltype == 'BLOB': # Big
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

class Index(typing.Generic[typing.T]):
    pass

block = Table('block', num=Index[int], time=Index[int])
acct = Table('acct')
token = Table('token', symbol=str, decimals=int)
dex = Table('dex', name=str, start=Optional['block'])
pair = Table('pair', token0=Index['token'], token1=Index['token'], dex=Index['dex'], index=Optional[Index[int]], latest_synced_trade=Optional['trade'])

trade = Table('trade',
        # for ordering
        blocknum = Index[int],
        blockidx = int,
        txidx = PrimaryKey[int],
        pair = PrimaryKey['pair'],

        block = 'block',
        trader0 = Optional['acct'],
        trader1 = Optional['acct'],
        token0_to_trader1 = Optional[int],
        token1_to_trader1 = Optional[int],
        const0 = Optional[Big[int]],
        const1 = Optional[Big[int]],
        gas_fee = Optional[int])

