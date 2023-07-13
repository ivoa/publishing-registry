"""
Generation of VODataService 1.1 tablesets from resources.

Fudge note: sprinkled in below are lots of lower()s for column names and the
like.  These were added for the convenience of TAP clients that may
want to use these names quoted.  Quoted identifiers match regular identifiers
only if case-normalized (i.e., all-lower in DaCHS).
"""

#c Copyright 2008-2023, the GAVO project <gavo@ari.uni-heidelberg.de>
#c
#c This program is free software, covered by the GNU GPL.  See the
#c COPYING file in the source distribution.


import functools
import itertools

from gavo import base
from gavo import rscdef
from gavo import svcs
from gavo import utils
from gavo.registry.model import VS


_VOTABLE_TO_SIMPLE_TYPE_MAP = {
	"char": "char",
	"bytea": "char",
	"unicodeChar": "char",
	"short": "integer",
	"int": "integer",
	"long": "integer",
	"float": "real",
	"double": "real",
}

def simpleDataTypeFactory(dbType, declaredXtype=None):
	type, length, xtype = base.sqltypeToVOTable(dbType)
	if length=='1':
		length = None
	return VS.dataType(arraysize=length, xsi_type="vs:SimpleDataType")[
		_VOTABLE_TO_SIMPLE_TYPE_MAP.get(type, "char")]


def voTableDataTypeFactory(dbType, declaredXtype=None):
	type, length, xtype = base.sqltypeToVOTable(dbType)
	# the following hack is mirrored in //tap; any similar hacks
	# would have to go there, too.
	if declaredXtype=="adql:REGION":
		type, length, xtype = "char", "*", "adql:REGION"
	return VS.voTableDataType(arraysize=length)[type](extendedType=xtype)


def getForeignKeyForForeignKey(fk, namesInSet):
	"""returns a VS.foreignKey for a rscdef.ForeignKey.

	If the target table's name is not in nameInSet, the foreign key
	is not created.
	"""
	targetName = fk.destTableName.lower()
	if targetName in namesInSet:
		return VS.foreignKey[
			VS.targetTable[targetName], [
				VS.fkColumn[
					VS.fromColumn[fromColName.lower()],
					VS.targetColumn[toColName.lower()]]
				for fromColName,toColName in zip(fk.source, fk.dest)]]


def _serializeFloats(stats):
	"""human-format float-typed values in stats.

	Background: XSLT 1 doesn't know about scientific notation, so we can't
	use format-number when displaying our column statistics through XSL
	(in vosi.xslt.  So, we give out ready-made floats (precision isn't
	a matter in the statistics values this is used for.
	"""
	res = {}
	for k, v in stats.items():
		try:
			res[k] = utils.formatFloat(float(v))
		except ValueError:
			res[k] = v
	return res


def getTableColumnFromColumn(column, typeFactory):
	"""returns a VS.column instance for an rscdef.Column instance.

	typeElement is a factory for types that has to accept an internal (SQL)
	type as child and generate whatever is necessary from that.
	
	This module contains simpleDataTypeFactory, voTableDataTypeFactory,
	and should soon contain tapTypeFactory.
	"""
	if isinstance(column.name, utils.QuotedName):
		colName = str(column.name)
	else:
		colName = column.name.lower()

	flags = []
	if column.isIndexed():
		flags.append("indexed")
	if column.isPrimary():
		flags.append("primary")
	elif not column.required:
		flags.append("nullable")

	return VS.column[
		VS.name[colName],
		VS.description[column.description],
		VS.unit[column.unit],
		VS.ucd[column.ucd],
		VS.utype[column.utype],
		typeFactory(column.type, column.xtype),
		[VS.flag[f] for f in flags]](**_serializeFloats(column.getStatistics()))


def getEffectiveTableName(tableDef):
	"""returns the "effective name" of tableDef.

	This is mainly for fudging the names of output tables since,
	by default, they're ugly (and meaningless on top of that).
	"""
	if isinstance(tableDef, svcs.OutputTableDef):
		return "output"
	else:
		return tableDef.getQName().lower()


def getTableForTableDef(
		tableDef, namesInSet, rootElement=VS.table, suppressBodies=False):
	"""returns a VS.table instance for a rscdef.TableDef.

	namesInSet is a set of lowercased qualified table names; we need this
	to figure out which foreign keys to create.
	"""
	name = getEffectiveTableName(tableDef)

	# Fake type=output on the basis of the table name.  We'll have
	# to do something sensible here if this "type" thing ever becomes
	# more meaningful.
	type = None
	if name=="output":
		type = "output"

	res = rootElement(type=type)[
		VS.name[name],
		VS.title[base.getMetaText(tableDef, "title", propagate=False)],
		VS.description[base.getMetaText(tableDef, "description", propagate=True)],
		VS.utype[base.getMetaText(tableDef, "utype")],
		VS.nrows[str(tableDef.nrows or "")]]
	
	if not suppressBodies:
		res[[
			getTableColumnFromColumn(col, voTableDataTypeFactory)
				for col in tableDef if not col.hidden], [
			getForeignKeyForForeignKey(fk, namesInSet)
				for fk in tableDef.foreignKeys]]

	return res


@functools.lru_cache(1)
def _getObscoreStub():
	"""returns a fake table definition for ivoa.obscore used to
	declare that a data collection is listed in obscore, too.
	"""
	td = base.makeStruct(rscdef.TableDef, id="obscore",
		parent_=base.caches.getRD("//obscore"))
	td.setMeta("description", "This data collection is queryable in"
		" %s's obscore table."%base.getConfig("web", "sitename"))
	return td


def getTablesetForSchemaCollection(
		schemas, rootElement=VS.tableset, suppressBodies=False):
	"""returns a vs:tableset element from a sequence of (rd, tables) pairs.
	
	In each pair, rd is used to define a VODataService schema, and tables is
	a sequence of TableDefs that define the tables within that schema.
	"""
	# we don't want to report foreign keys into tables not part of the
	# service's tableset (this is for consistency with TAP_SCHEMA,
	# mainly).  Hence, we collect the table names given.
	# While doing that, we also see if we have obscore-published tables.
	# If so, we want to add an ivoa.obscore stub unless we have obscore
	# in the tableset already.
	namesInSet, obscorePublished = set(), False
	for td in itertools.chain(*(tables for rd, tables in schemas)):
		namesInSet.add(getEffectiveTableName(td).lower())
		if td.hasProperty("obscoreClause"):
			obscorePublished = True

	# adding ivoa.obscore at this point is tricky since we want to
	# avoid having multiple ivoa schemas or obscore tables.
	# (really, only the last "else" will count in practice)
	if obscorePublished:
		for rd, tables in schemas:
			if rd.schema=='ivoa':
				for td in tables:
					if td.getQName().lower()=='ivoa.obscore':
						break
				else:
					tables.append(_getObscoreStub())
				break
		else:
			schemas.append((base.caches.getRD('//obscore'), [_getObscoreStub()]))

	res = rootElement()
	for rd, tables in schemas:
		res[VS.schema[
			VS.name[rd.schema],
			VS.title[base.getMetaText(rd, "title")],
			VS.description[base.getMetaText(rd, "description")],
			VS.utype[base.getMetaText(rd, "utype", None)],
			[getTableForTableDef(td, namesInSet, suppressBodies=suppressBodies)
				for td in tables]]]
	return res


class _InternalSchemaStandin(base.MetaMixin):
	"""a place-holder for the RD of a schema-less table (which doesn't
	have an RD).
	"""
	schema = "internal"
	def __init__(self):
		base.MetaMixin.__init__(self)
		self.setMeta("title", "Not a Schema")
		self.setMeta("description",
			"A helper for virtual and temporary tables")

_INTERNAL_SCHEMA = _InternalSchemaStandin()


def getTablesetForService(
		resource, rootElement=VS.tableset, suppressBodies=False):
	"""returns a VS.tableset for a service or a published data resource.

	This is for VOSI queries and the generation of registry records.
	Where it actually works on services, it uses the service's getTableset
	method to find out the service's table set; if it's passed a TableDef
	of a DataDescriptor, it will turn these into tablesets.

	Sorry about the name.
	"""
	if isinstance(resource, rscdef.TableDef):
		tables = [resource]

	elif isinstance(resource, rscdef.DataDescriptor):
		tables = [td for td in resource.iterTableDefs()
			if td.adql and td.adql!="hidden"]
	
	else:
		tables = resource.getTableSet()

	if not tables:
		return rootElement[
			VS.schema[
				VS.name["default"]]]

	# it's possible that multiple RDs define the same schema (don't do
	# that, it's going to cause all kinds of pain).  To avoid
	# generating bad tablesets in that case, we have the separate
	# account of schema names; the schema meta is random when
	# more than one RD exists for the schema.
	bySchema, rdForSchema = {}, {}
	for t in tables:
		if t.rd:
			# it's a DB table that actually is in a schema
			bySchema.setdefault(t.rd.schema, []).append(t)
			rdForSchema[t.rd.schema] = t.rd
		else:
			# it's some sort of generated thing.  Stuff it into "internal";
			# by VODataService, schema needs a name, and we won't cheat
			# by making it empty.
			bySchema.setdefault("internal", []).append(t)
			rdForSchema["internal"] = _INTERNAL_SCHEMA

	schemas = []
	for schemaName, tables in sorted(bySchema.items()):
		schemas.append((rdForSchema[schemaName], tables))
	
	return getTablesetForSchemaCollection(
		schemas,
		rootElement,
		suppressBodies=suppressBodies)
