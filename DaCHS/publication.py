"""
"Publishing" service records -- grammar-type stuff and UI.

This module basically turns "publishable things" -- services, resource
records, data items -- into row dictionaries that can be entered into
the database.

This is one half of getting them into the registry.  The other half is
done in identifiers and builders; these take the stuff from the database,
rebuilds actual objects and creates registry records from them.  So,
the content of the service table is not actually used to build resource
records.
"""

#c Copyright 2008-2023, the GAVO project <gavo@ari.uni-heidelberg.de>
#c
#c This program is free software, covered by the GNU GPL.  See the
#c COPYING file in the source distribution.


import functools
import datetime
import itertools
import os
import urllib.parse

import pkg_resources

from gavo import base
from gavo import grammars
from gavo import rsc
from gavo import rscdef
from gavo import utils

from gavo.registry import builders
from gavo.registry import common


# Names of renders that should not be shown to humans; these are
# also not included in the dc.interfaces table.  Right now, this
# list only contains the VOSI renderers, but other infrastructure-type
# capabilities might belong here, too.
HIDDEN_RENDERERS = frozenset([
	'tableMetadata', 'availability', 'capabilities'])


@functools.lru_cache(1)
def getManagedAuthorities():
	"""returns a (cached) set of authorities our main registry
	manages.
	"""
	reg = base.resolveCrossId("//services#registry")
	return frozenset(v.getContent()
		for v in reg.iterMeta("managedAuthority"))


def makeBaseRecord(res, keepTimestamp=False):
	"""returns a dictionary giving the metadata common to resource records.
	"""
	# bomb out if critical metadata is missing
	base.validateStructure(res)
	# bomb out if, for some reason, we can't come up with a resource record
	# for this guy
	builders.getVOResourceElement(res)
	# skip this resource if we must not publish it because we don't
	# manage its authority
	ivoid = base.getMetaText(res, "identifier")
	auth = urllib.parse.urlparse(ivoid).netloc

	if (auth=="x-unregistred"
			and not "yes"==base.getMetaText(res, "i-am-sure", "")):
		# allow this if people have no ivo_managed publications
		if list(res.getPublicationsForSet(
				{"ivo_managed"}, includeDatalink=False)):
			raise base.ReportableError("Resource {} uses the authority"
				" x-unregistered; this is not permitted.".format(res.getFullId()),
				hint="This in all likelihood means that you are not setting"
				" the [ivoa]authority config item in your gavo.rc.  Read up"
				" on 'Choosing your authority' in the tutorial to see how"
				" to fix this.")

	if not auth in getManagedAuthorities():
		base.ui.notifyWarning("Skipping publication of resource"
			" with identifier %s because we don't manage its authority"%
			ivoid)
		raise base.SkipThis("Resource from non-managed authority")

	rec = {}
	rec["ivoid"] = ivoid
	rec["shortName"] = base.getMetaText(res, "shortName")
	rec["sourceRD"] = res.rd.sourceId
	rec["resId"] = res.id
	rec["title"] = base.getMetaText(res, "title", propagate=True)
	rec["deleted"] = False
	rec["recTimestamp"] = datetime.datetime.utcnow()
	rec["description"] = base.getMetaText(res, "description")
	rec["authors"] = "; ".join(m.getExpandedContent(res)
		for m in res.iterMeta("creator.name", propagate=True))
	rec["dateUpdated"] = base.getMetaText(res, "_dataUpdated", default=None)

	if keepTimestamp:
		try:
			rec["recTimestamp"] = utils.parseISODT(
				base.getMetaText(res, "recTimestamp")
				or datetime.datetime.utcnow())
		except base.NoMetaKey:
			# not published, nothing to keep
			pass

	return rec


def iterAuthorsAndSubjects(resource, sourceRD, resId):
	"""yields rows for the subjects and authors tables.

	resource is the meta-carrier for the resource to be described,
	sourceRD and resId are its keys in the resources table.
	"""
	for subject in [str(item) for item in resource.getMeta("subject") or (None,)]:
		yield ("subjects", {
			"sourceRD": sourceRD,
			"resId": resId,
			"subject": subject})
	
	# for authors, we support a special notation, separating individual
	# authors with semicolons.
	for authors in resource.iterMeta("creator.name", propagate="True"):
		authors = [s.strip() for s in
			authors.getExpandedContent(resource).split(";")]
		for author in authors:
			if not author.startswith("et al"):
				yield ("authors", {
					"sourceRD": sourceRD,
					"resId": resId,
					"author": author})


def iterSvcRecs(service, keepTimestamp=False):
	"""iterates over records suitable for importing into the service list
	for service.
	"""
	if not service.publications:
		return  # don't worry about missing meta if there are no publications

	try:
		rec = makeBaseRecord(service, keepTimestamp)
	except base.SkipThis:
		return

	rec["owner"] = service.limitTo
	yield ("resources", rec)

	# each publication becomes one interface, except for auxiliary
	# and VOSI publications, which are for the VO registry only.
	for pub in service.publications:
		if pub.auxiliary:
			continue
		if pub.render in HIDDEN_RENDERERS:
			continue

		try:
			browseable = service.isBrowseableWith(pub.render)
		except AttributeError:  # service is not a ServiceBasedPage
			browseable = False

		pubService = service
		if pub.service:
			pubService = pub.service

		intfRec = {
			"sourceRD": rec["sourceRD"],
			"resId": rec["resId"],
			"renderer": pub.render,
			"accessURL":  pubService.getURL(pub.render, absolute=False),
			"referenceURL": base.getMetaText(pubService, "referenceURL"),
			"browseable": browseable,
			"deleted": False}
		yield ("interfaces", intfRec)

		for setName in pub.sets:
			intfRec.copy()
			intfRec["setName"] = setName
			yield ("sets", intfRec)

	for pair in iterAuthorsAndSubjects(service,
			rec["sourceRD"], rec["resId"]):
		yield pair


def iterResRecs(res, keepTimestamp=False):
	"""as iterSvcRecs, just for ResRecs rather than Services.
	"""
	try:
		rec = makeBaseRecord(res, keepTimestamp)
	except base.SkipThis:
		return

	# resource records only make sense if destined for the registry
	rec["setName"] = "ivo_managed"
	rec["renderer"] = "rcdisplay"
	yield ("resources", rec)
	yield ("sets", rec)

	for pair in iterAuthorsAndSubjects(res,
			rec["sourceRD"], rec["resId"]):
		yield pair


def iterDataRecs(res, keepTimestamp=False):
	"""as iterSvcRecs, just for DataDescriptors rather than Services.
	"""
	try:
		rec = makeBaseRecord(res, keepTimestamp)
	except base.SkipThis:
		return

	yield ("resources", rec)
	for setName in res.registration.sets:
		rec["setName"] = setName
		rec["renderer"] = "rcdisplay"
		yield ("sets", rec.copy())
		# if we have a local publication, add a fake interface with
		# an accessURL pointing towards TAP
		if setName=="local":
			refURL = base.getMetaText(res, "referenceURL", macroPackage=res.rd)
			yield ("interfaces", {
				"sourceRD": rec["sourceRD"],
				"resId": rec["resId"],
				"renderer": "rcdisplay",
				"accessURL": refURL+"?tapinfo=True" if refURL else None,
				"referenceURL": refURL,
				"browseable": False,
				"deleted": False})

	for pair in iterAuthorsAndSubjects(res,
			rec["sourceRD"], rec["resId"]):
		yield pair


class RDRscRecIterator(grammars.RowIterator):
	"""A RowIterator yielding resource records for inclusion into the
	service list for the services defined in the source token RD.
	"""
	notify = False

	def _iterRows(self):
		if self.grammar.unpublish:
			return

		for svc in self.sourceToken.services:
			self.curSource = svc.id
			for sr in iterSvcRecs(svc, self.grammar.keepTimestamp):
				yield sr

		for res in self.sourceToken.resRecs:
			self.curSource = res.id
			for sr in iterResRecs(res, self.grammar.keepTimestamp):
				yield sr

		for res in itertools.chain(self.sourceToken.tables, self.sourceToken.dds):
			self.curSource = res.id
			if res.registration:
				for sr in iterDataRecs(res, self.grammar.keepTimestamp):
					yield sr

		# now see if there's a TAP-published table in there.  If so,
		# re-publish the TAP service, too, unless that table is published
		# by itself (in which case we deem the metadata update on the
		# table enough for now -- TODO: reconsider this when we allow
		# TAP registration without an associated tableset)

		ignoredRegistrations = frozenset(["local"])
		if self.sourceToken.sourceId!="__system__/tap":
			for table in self.sourceToken.tables:
				if table.adql and not table.registration.sets<ignoredRegistrations:
					# we shortcut this and directly update the TAP timestamp
					# since producing a TAP record can be fairly expensive.
					with base.getWritableAdminConn() as conn:
						conn.execute("UPDATE dc.resources SET"
							" dateupdated=CURRENT_TIMESTAMP,"
							" rectimestamp=CURRENT_TIMESTAMP"
							" WHERE sourcerd='__system__/tap'")
					break
	
	def getLocation(self):
		return "%s#%s"%(self.sourceToken.sourceId, self.curSource)


# extra handwork to deal with timestamps on deleted records
def getDeletedIdentifiersUpdater(conn, rd):
	"""returns a function to be called after records have been
	updated to mark new deleted identifiers as changed.

	The problem solved here is that we mark all resource metadata
	belonging to and RD as deleted before feeding the new stuff in.
	We don't want to change resources.rectimestamp there; this would,
	for instance, bump old deleted records.

	What we can do is see if there's new deleted records after and rd
	is through and update their rectimestamp.  We don't need to like it.
	"""
	oldDeletedRecords = set(r[0] for r in
		conn.query("select ivoid from dc.resources"
			" where sourcerd=%(rdid)s and deleted",
			{"rdid": rd.sourceId}))

	def bumpNewDeletedRecords():
		newDeletedRecords = set(r[0] for r in
			conn.query("select ivoid from dc.resources"
				" where sourcerd=%(rdid)s and deleted",
				{"rdid": rd.sourceId}))
		toBump = newDeletedRecords-oldDeletedRecords
		if toBump:
			conn.execute("update dc.resources set rectimestamp=%(now)s"
				" where ivoid in %(ivoids)s", {
					"now": datetime.datetime.utcnow(),
					"ivoids": toBump})
	
	return bumpNewDeletedRecords


class RDRscRecGrammar(grammars.Grammar):
	"""A grammar for "parsing" raw resource records from RDs.
	"""
	rowIterator = RDRscRecIterator
	isDispatching = True

	# this is a flag to try and keep the registry timestamps as they are
	# during republication.
	keepTimestamp = False
	# setting the following to false will inhibit the re-creation of
	# resources even if they're still defined in the RD.
	unpublish = False


def updateServiceList(rds,
		metaToo=False,
		connection=None,
		onlyWarn=True,
		keepTimestamp=False,
		unpublish=False):
	"""updates the services defined in rds in the services table in the database.

	This is what actually does the publication.
	"""
	if metaToo:
		raise NotImplementedError("Meta updating from within pub is no longer"
			" supported.  Use dachs imp -m instead.")

	recordsWritten = 0
	parseOptions = rsc.getParseOptions(validateRows=True, batchSize=20)
	if connection is None:
		connection = base.getDBConnection("admin")
	dd = common.getServicesRD().getById("tables")
	dd.grammar = base.makeStruct(RDRscRecGrammar)
	dd.grammar.keepTimestamp = keepTimestamp
	dd.grammar.unpublish = unpublish

	depDD = common.getServicesRD().getById("deptable")
	msg = None
	for rd in rds:
		if rd.sourceId.startswith("/"):
			raise base.Error("Resource descriptor ID must not be absolute, but"
				" '%s' seems to be."%rd.sourceId)

		deletedUpdater = getDeletedIdentifiersUpdater(connection, rd)

		try:
			data = rsc.makeData(dd, forceSource=rd, parseOptions=parseOptions,
				connection=connection)
			recordsWritten += data.nAffected
			rsc.makeData(depDD, forceSource=rd, connection=connection)
			deletedUpdater()
			connection.commit()

		except base.MetaValidationError as ex:
			msg = ("Aborting publication of rd '%s' since meta structure of"
				" %s (id='%s') is invalid:\n * %s")%(
				rd.sourceId, repr(ex.carrier), ex.carrier.id, "\n * ".join(ex.failures))
		except base.NoMetaKey as ex:
			msg = ("Aborting publication of '%s' at service '%s': Resource"
				" record generation failed: %s"%(
				rd.sourceId, ex.carrier.id, str(ex)))
		except Exception as ex:
			base.ui.notifyError("Fatal error while publishing from RD %s: %s"%(
				rd.sourceId, str(ex)))
			raise

		if msg is not None:
			if onlyWarn:
				base.ui.notifyWarning(msg)
			else:
				raise base.ReportableError(msg)
		msg = None

	common.getServicesRD().updateMetaInDB(connection, "import")

	connection.commit()
	return recordsWritten


def _purgeFromServiceTables(rdId, conn):
	"""purges all resources coming from rdId from the registry tables.

	This is not for user code that should rely on the tables doing the
	right thing (e.g., setting the deleted flag rather than deleting rows).
	Test code that is not in contact with the actual registry might want
	this, though (until postgres grows nested transactions).
	"""
	cursor = conn.cursor()
	for tableName in [
			"resources", "interfaces", "sets", "subjects", "res_dependencies",
			"authors"]:
		cursor.execute("delete from dc.%s where sourceRD=%%(rdId)s"%tableName,
			{"rdId": rdId})
	cursor.close()


def makeDeletedRecord(ivoid, conn):
	"""enters records into the internal service tables to mark ivoid
	as deleted.
	"""
	fakeId = ivoid.split("/")[-1] or "<empty>"
	svcRD = base.caches.getRD("//services")
	rscTable = rsc.TableForDef(svcRD.getById("resources"),
		connection=conn)
	rscTable.addRow({
		"sourceRD": "deleted",
		"resId": fakeId,
		"shortName": "deleted",
		"title": "Ex "+ivoid,
		"description": "This is a sentinel for a record once published"
			" by this registry but now dropped.",
		"owner": None,
		"dateUpdated": datetime.datetime.utcnow(),
		"recTimestamp": datetime.datetime.utcnow(),
		"deleted": True,
		"ivoid": ivoid,
		"authors": ""})

	setTable = rsc.TableForDef(svcRD.getById("sets"),
		connection=conn)
	setTable.addRow({
		"sourceRD": "deleted",
		"resId": fakeId,
		"setName": "ivo_managed",
		"renderer": "custom",
		"deleted": True})


################ UI stuff

def findAllRDs():
	"""returns ids of all RDs (inputs and built-in) known to the system.
	"""
	rds = []
	inputsDir = base.getConfig("inputsDir")
	for dir, dirs, files in os.walk(inputsDir):

		if "DACHS_PRUNE" in files:
			dirs = []   #noflake: deliberately manipulating loop variable
			continue

		for file in files:
			if file.endswith(".rd"):
				rds.append(os.path.splitext(
					utils.getRelativePath(os.path.join(dir, file), inputsDir))[0])

	for name in pkg_resources.resource_listdir('gavo',
			"resources/inputs/__system__"):
		if not name.endswith(".rd"):  # ignore VCS files (and possibly others:-)
			continue
		rds.append(os.path.splitext("__system__/%s"%name)[0])
	return rds


def findPublishedRDs():
	"""returns the ids of all RDs which have been published before.
	"""
	with base.getTableConn() as conn:
		return [r['sourcerd'] for r in conn.queryToDicts(
			"select distinct sourcerd from dc.resources where not deleted")]


def getRDs(args):
	"""returns a list of RDs from a list of RD ids or paths.
	"""
	from gavo import rscdesc
	allRDs = []
	for rdPath in args:
		try:
			allRDs.append(
				rscdef.getReferencedElement(rdPath, forceType=rscdesc.RD))
		except:
			base.ui.notifyError("RD %s faulty, ignored.\n"%rdPath)
	return allRDs


def parseCommandLine():
	import argparse
	parser = argparse.ArgumentParser(
		description="Publish services from an RD")
	parser.add_argument("-k", "--keep-timestamps",
		help="Preserve the time stamp of the last record modification."
		" This may sometimes be desirable with minor updates to an RD"
		" that don't justify a re-publication to the VO.",
		action="store_true", dest="keepTimestamp")
	parser.add_argument("-u", "--unpublish", help="Unpublish all"
		" resources coming from this RD",
		dest="unpublish", action="store_true")
	parser.add_argument("rd", type=str, nargs="+",
		help="RDs to publish; you can give ids or file paths.  Use the"
		" magic value ALL to check all published RDs, ALL_RECURSE to look"
		" for RDs in the file system (check twice for detritus before doing"
		" that later thing).")
	return parser.parse_args()


def main():
	"""handles the user interaction for gavo publish.
	"""
	from gavo import rscdesc #noflake: register cache
	args = parseCommandLine()

	if len(args.rd)==1 and args.rd[0]=="ALL":
		args.rd = findPublishedRDs()
	elif len(args.rd)==1 and args.rd[0]=="ALL_RECURSE":
		args.rd = findAllRDs()

	updateServiceList(getRDs(args.rd),
		keepTimestamp=args.keepTimestamp,
		unpublish=args.unpublish)
	base.tryRemoteReload("__system__/services")
