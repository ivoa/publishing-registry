"""
The (DC-internal) service list: querying, adding records, etc.
"""

#c Copyright 2008-2023, the GAVO project <gavo@ari.uni-heidelberg.de>
#c
#c This program is free software, covered by the GNU GPL.  See the
#c COPYING file in the source distribution.


from gavo import base
from gavo import utils
from gavo import rsc
from gavo.protocols import vocabularies
from gavo.registry import common


def getSetsForResource(restup):
	"""returns the list of set names the resource described by restup
	belongs to.
	"""
	with base.getTableConn() as conn:
		return [str(r[0]) for r in
			conn.query("SELECT DISTINCT setName FROM dc.sets WHERE"
				" sourceRD=%(sourceRD)s AND resId=%(resId)s AND NOT deleted",
				restup)]


def getSets():
	"""returns a sequence of dicts giving setName and and a list of
	services belonging to that set.
	"""
	tableDef = common.getServicesRD().getById("sets")
	setMembers = {}

	for rec in tableDef.doSimpleQuery():
		setMembers.setdefault(rec["setName"], []).append(
			(rec["sourceRD"], rec["resId"]))

	return [{"setName": key, "services": value}
		for key, value in setMembers.items()]


def queryServicesList(whereClause="", pars={}, tableName="resources_join"):
	"""returns a list of services based on selection criteria in
	whereClause.

	The table queried is the resources_join view, and you'll get back all
	fields defined there.
	"""
	td = common.getServicesRD().getById(tableName)
	return td.doSimpleQuery(fragments=whereClause, params=pars)


def querySubjectsList(setName=None):
	"""returns a list of local services chunked by subjects.

	This is mainly for the root page (see web.root).  Query the
	cache using the __system__/services key to clear the cache on services.

	Note that this will translate known UAT terms to their labels.
	"""
	try:
		uat = vocabularies.get_vocabulary("uat")
	except base.ReportableError as msg:
		# fetching the vocabulary somehow failed; don't stop operations
		# just because of that.
		base.ui.notifyWarning("Tried to get UAT but failed: %s.  Trugding on."%
			msg)
		uat = {"terms": {}}

	setName = setName or 'local'
	svcsForSubjs = {}
	td = common.getServicesRD().getById("subjects_join")
	for row in td.doSimpleQuery(
			fragments="setName=%(setName)s AND subject IS NOT NULL",
			params={"setName": setName}):
		svcsForSubjs.setdefault(row["subject"], []).append(row)

	for s in list(svcsForSubjs.values()):
		s.sort(key=lambda a: a["title"])

	res = [{"subject": vocabularies.get_label(uat, subject), "chunk": s}
		for subject, s in svcsForSubjs.items()]
	res.sort(key=lambda i: i["subject"])
	return res


def getChunkedServiceList(setName=None):
	"""returns a list of local services chunked by title char.

	This is mainly for the root page (see web.root).  Query the
	cache using the __system__/services key to clear the cache on services
	reload.
	"""
	setName = setName or 'local'
	return utils.chunk(
		sorted(queryServicesList("setName=%(setName)s and not deleted",
			{"setName": setName}),
			key=lambda s: s.get("title").lower()),
		lambda srec: srec.get("title", ".")[0].upper())


def cleanServiceTablesFor(rd, connection):
	"""removes/invalidates all entries originating from rd from the service
	tables.
	"""
# this is a bit of a hack: We're running services#tables' newSource
#	skript without then importing anything new.
	tables = rsc.Data.create(
		common.getServicesRD().getById("tables"),
		connection=connection)
	tables.runScripts("newSource", sourceToken=rd)


def basename(tableName):
	if "." in tableName:
		return tableName.split(".")[-1]
	else:
		return tableName


def getTableDef(tableName):
	"""returns a tableDef instance for the schema-qualified tableName.

	If no such table is known to the system, a NotFoundError is raised.
	"""
	with base.getTableConn() as conn:
		res = list(conn.query("SELECT tableName, sourceRD FROM dc.tablemeta WHERE"
				" LOWER(tableName)=LOWER(%(tableName)s)", {"tableName": tableName}))
	if len(res)!=1:
		raise base.NotFoundError(tableName, what="table",
			within="DaCHS' table listing.", hint="The table is missing from"
			" the dc.tablemeta table.  This gets filled at gavoimp time.")
	tableName, rdId = res[0]
	return base.caches.getRD(rdId).getById(basename(tableName))
