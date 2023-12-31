"""
Functions returning xmlstan for various OAI/VOR documents.

This comprises basic VOResource elements; capabilities and interfaces
(i.e. everything to do with renderers) are in registry.capabilities.

All this only becomes difficult when actually generating VOResource
metadata (OAI is plain).  For every type of VO resource (CatalogService,
Registry, etc), there's a XYResourceMaker, all inheriting ResourceMaker.

The decision what VOResource type a given service has is passed
using common.getResType; this means the resType meta is tried first,
using resob.resType as a fallback.
"""

#c Copyright 2008-2023, the GAVO project <gavo@ari.uni-heidelberg.de>
#c
#c This program is free software, covered by the GNU GPL.  See the
#c COPYING file in the source distribution.


# DataCollection mess: In rev 3769, we experimentally pushed out
# CatalogService records instead of DataCollections, trying to have
# capabilities for them.  That didn't turn out well even though
# we didn't do that for SIA and frieds: All-VO discovery of a
# given service type is a very typical use case.  So, we backed
# that out again in rev. 3883, though the support code remains.
#
# Then, in rev. 3891, we went back to CatalogService records, only
# this time we only pushed out capabilities with "auxiliary" standard ids.


from gavo import base
from gavo import stc
from gavo import svcs
from gavo import utils
from gavo.base import meta
from gavo.registry import common
from gavo.registry import capabilities
from gavo.registry import identifiers
from gavo.registry import tableset
from gavo.registry import servicelist
from gavo.registry.model import (
	OAI, VOR, VOG, DC, RI, VS, OAIDC, VSTD, DOC)

MS = base.makeStruct

SF = meta.stanFactory
_defaultSet = set(["ivo_managed"])
# Set this to False to disable some lame "don't fail" error handlings;
# this will raise more exceptions and is not recommended in the actual
# OAI interface (where *some* info is better than none at all).
VALIDATING = False


################## ModelBasedBuilders for simple metadata handling

def _build_source(children, localattrs=None):
# in source, we try to recognize bibcodes automatically, hence we have
# this manual builder.
	src = str(children[0])
	attrs = {}
	if utils.couldBeABibcode(src):
		attrs["format"] = "bibcode"
	return VOR.source(**attrs)[src]


def _build_dateFromNews(children, localattrs={}):
# _news was designed to be non-VOResource, but it turned out it's
# really useful to specify dates.  So, contrary to our principle, there's
# an underscore-starting meta here, anyway.
	if utils.dateRE.match(localattrs.get("date", "")):
		return [VOR.date(role=localattrs.get("role", "updated"))[
			localattrs["date"]]]


_vrResourceBuilder = meta.ModelBasedBuilder([
	('title', SF(VOR.title)),
	('shortName', SF(VOR.shortName)),
	('identifier', SF(VOR.identifier)),
	('doi', lambda args, localattrs=None: VOR.altIdentifier["doi:"+args[0]]),
	(None, SF(VOR.curation), [
		('publisher', SF(VOR.publisher), (), {
				"ivoId": "ivoId"}),
		('creator', SF(VOR.creator), [
			('name', SF(VOR.name)),
			('altIdentifier', SF(VOR.altIdentifier)),
			('logo', SF(VOR.logo)),]),
		('contributor', SF(VOR.contributor), (), {
				"ivoId": "ivoId"}),
		('_dataUpdated', SF(VOR.date, role="updated")),
		('date', SF(VOR.date), (), {
				"role": "role"}),
		('_news', _build_dateFromNews, (), {
				"role": "role",
				"date": "date"}),
		('version', SF(VOR.version)),
		('contact', SF(VOR.contact), [
			('name', SF(VOR.name), (), {
				"ivoId": "ivoId"}),
			('address', SF(VOR.address)),
			('email', SF(VOR.email)),
			('telephone', SF(VOR.telephone)),]),]),
	(None, SF(VOR.content), [
		('subject', SF(VOR.subject)),
		('description', SF(VOR.description)),
		('source', _build_source),
		('referenceURL', SF(VOR.referenceURL)),
		('type', SF(VOR.type)),
		('contentLevel', SF(VOR.contentLevel)),] + [
		# old-style relationship terms from VOResource 1.0 f
		# plan: after a while, make the update mapping in here
			(None, SF(lambda t=vorTerm:
				VOR.relationship[VOR.relationshipType[t]]), [
			(metaName, SF(VOR.relatedResource), (), {
					"ivoId": "ivoId"})])
			for metaName, vorTerm in [
				("servedBy", "IsServedBy"),
				("serviceFor", "IsServiceFor"),
				("derivedFrom", "IsDerivedFrom"),
				("relatedTo", "related-to"),
				("mirrorOf", "IsIdenticalTo"),
				("uses", "Cites")]
		] + [
		# new-style relationship terms from VOResource 1.1
			(None, SF(lambda term=term:
				VOR.relationship[VOR.relationshipType[term]]), [
			(term[0].lower()+term[1:], SF(VOR.relatedResource), (), {
					"ivoId": "ivoId"})])
			for term in [
				"Cites",
				"IsSupplementTo",
				"IsSupplementedBy",
				"IsContinuedBy",
				"Continues",
				"IsNewVersionOf",
				"IsPreviousVersionOf",
				"IsPartOf",
				"HasPart",
				"IsSourceOf",
				"IsDerivedFrom",
				"IsIdenticalTo",
				"IsServiceFor",
				"IsServedBy"]])
])


_dcBuilder = meta.ModelBasedBuilder([
	('title', SF(DC.title)),
	('identifier', SF(DC.identifier)),
	('creator', None, [
		('name', SF(DC.creator))]),
	('contributor', None, [
		('name', SF(DC.contributor))]),
	('description', SF(DC.description)),
	('language', SF(DC.language)),
	('rights', SF(DC.rights), ()),
	('publisher', SF(DC.publisher)),
	])


_oaiHeaderBuilder = meta.ModelBasedBuilder([
	('identifier', SF(OAI.identifier)),
	('_metadataUpdated', SF(OAI.datestamp)),
	('sets', SF(OAI.setSpec))])


_orgMetaBuilder = meta.ModelBasedBuilder([
	('facility', SF(VOR.facility)),# XXX TODO: look up ivo-ids?
	('instrument', SF(VOR.instrument), (),
		{"altIdentifier": "altIdentifier", "ivoId": "ivoId"}),
])


_standardsMetaBuilder = meta.ModelBasedBuilder([
	('endorsedVersion', SF(VSTD.endorsedVersion), (), {
			'status': 'status',
			'use': 'use'}),
	('deprecated', SF(VSTD.deprecated), ()),
	('key', SF(VSTD.key), [
		('name', SF(VSTD.name), []),
		('description', SF(VSTD.description), [])])])


def _stcResourceProfile(metaValue, localattrs=None):
# This is a helper for the coverageMetaBuilder; it expects
# STC-S and will return an STC resource profile for literal
# embedding.
	if not metaValue:
		return None
	try:
		return stc.astToStan(
			stc.parseSTCS(metaValue[0]),
			stc.STC.STCResourceProfile)
	except Exception as exc:
		if VALIDATING:
			raise
		base.ui.notifyError("Coverage profile '%s' bad while generating "
			" registry (%s).  It is left out."%(metaValue, str(exc)))


def _build_footprintURL(children, localattrs):
	# a service that has a spatial coverage can spit out
	# MOCs using the coverage renderer.
	#
	# Unfortunately, getting a URL from coverage information breaks
	# our abstractions.  I'd like to get rid of footprintURL anyway,
	# so this is another case for stealing variables from upstack.
	# It turns out the macroPackage in the enclosing frame actually
	# is the service or table we're building for.  And if that thing
	# can build URLs, that's what we're looking for.  If it can't
	# it can't produce footprint MOCs in the first place, so we
	# can return None.
	carrier = utils.stealVar("macroPackage")
	if isinstance(carrier, svcs.Service):
		return VS.footprint(ivoId="ivo://ivoa.net/std/moc")[
			carrier.getURL("coverage")]


_coverageMetaBuilder = meta.ModelBasedBuilder([
	('coverage', SF(VS.coverage), [
		('profile', _stcResourceProfile),
		('spatial', SF(VS.spatial)),
		('temporal', SF(VS.temporal)),
		('spectral', SF(VS.spectral)),
		# resources that have spatial coverage get a footprint url in
		# addition to the spatial coverage at least for a while.
		('spatial', _build_footprintURL),
		('waveband', SF(VS.waveband)),
		('regionOfRegard', SF(VS.regionOfRegard)),
	])])


def getResourceArgs(resob):
	"""returns the mandatory attributes for constructing a Resource record
	for service in a dictionary.
	"""
	return {
		"created": base.getMetaText(resob, "creationDate", propagate=True),
		"updated": base.getMetaText(resob, "_metadataUpdated", propagate=True),
		"status": base.getMetaText(resob, "status"),
	}


def getOAIHeaderElementForRestup(restup):
	if isinstance(restup, OAI.OAIElement):
		return restup
	status = None
	if restup["deleted"]:
		status = "deleted"
	return OAI.header(status=status)[
		OAI.identifier[identifiers.computeIdentifierFromRestup(restup)],
		OAI.datestamp[restup["recTimestamp"].strftime(utils.isoTimestampFmt)],
		[
			OAI.setSpec[setName]
				for setName in servicelist.getSetsForResource(restup)]]


###################### Direct children of OAI.PMH

def _getOAIURL(registryService):
	"""returns the OAI-PHM access URL for a registry service.

	We don't want to just use getURL(pubreg) since the publication
	may (and for the publishing registry does) have an accessURL meta.
	"""
	oaiAccessURL = registryService.getURL("pubreg.xml")
	for pub in registryService.publications:
		if pub.render=="pubreg.xml":
			oaiAccessURL = base.getMetaText(
				pub, "accessURL", macroPackage=pub.parent)
			break
	return oaiAccessURL


def getIdentifyElement(registryService):
	"""returns OAI Identify stanxml.

	registryService is the registry we're identifying, i.e. typically
	__system__/services#registry
	"""
	return OAI.Identify[
		OAI.repositoryName[base.getMetaText(registryService, "title")],
		OAI.baseURL[_getOAIURL(registryService)],
		OAI.protocolVersion["2.0"],
		OAI.adminEmail[base.getMetaText(registryService, "contact.email")],
		OAI.earliestDatestamp["1970-01-01T00:00:00Z"],
		OAI.deletedRecord["transient"],
		OAI.granularity["YYYY-MM-DDThh:mm:ssZ"],
		OAI.description[
			getVORMetadataElement(registryService),
		],
	]


def getListIdentifiersElement(restups):
	"""returns an OAI ListIdentifiers element for the rec tuples recs.
	"""
	return OAI.ListIdentifiers[
		[getOAIHeaderElementForRestup(restup) for restup in restups],
	]


def getListMetadataFormatsElement():
	return OAI.ListMetadataFormats[[
		OAI.metadataFormat[
			OAI.metadataPrefix[prefix],
			OAI.schema[schema],
			OAI.metadataNamespace[ns],
		] for prefix, schema, ns in common.METADATA_PREFIXES]
	]


def getListSetsElement():
	return OAI.ListSets[[
		# XXX TODO: Add some kind of description, in particular when we define
		# real local sets.
		OAI.set[
			OAI.setSpec[set["setName"]],
			OAI.setName[set["setName"]],
		]
	for set in servicelist.getSets()]]


def getResourceElement(resob, setNames, metadataMaker):
	"""helps get[VO|DC]ResourceElement.
	"""
	if isinstance(resob, OAI.OAIElement):
		return resob
	status = None
	if base.getMetaText(resob, "status")=="deleted":
		status = "deleted"
	return OAI.record[
		OAI.header(status=status)[
			_oaiHeaderBuilder.build(resob)],
		OAI.metadata[
			metadataMaker(resob, setNames)
		]
	]


def getDCMetadataElement(resob, setNames):
	return OAIDC.dc[_dcBuilder.build(resob)]


def getDCResourceElement(resob, setNames=_defaultSet):
	return getResourceElement(resob, setNames, getDCMetadataElement)


def getDCListRecordsElement(resobs, setNames,
		makeRecord=getDCResourceElement):
	"""returns stanxml for ListRecords in dublin core format.

	resobs is a sequence of res objects.
	makeRecord(resob, setNames) -> stanxml is a function that returns
	an OAI.record element.  For ivo_vor metadata prefixes, this is overridden.
	by getVOListRecordsElement.
	"""
	recs = OAI.ListRecords()
	for resob in resobs:
		try:
			recs[makeRecord(resob, setNames)]
		except base.NoMetaKey as msg:
			base.ui.notifyError("Cannot create registry record for %s#%s"
			" because mandatory meta %s is missing"%(
				resob.rd.sourceId, resob.id, msg))
		except Exception as msg:
			base.ui.notifyError("Cannot create registry record %s.  Reason: %s"%(
				resob, msg))
	return recs


def getDCGetRecordElement(resob):
	return OAI.GetRecord[
		getDCResourceElement(resob)]


################### VOResource metadata element creation

class ResourceMaker(object):
	"""A base class for the generation of VOResource elements.

	These have a resType attribute specifying which resource type
	they work for.	These types are computed by the getResourceType
	helper function.

	The makeResource function below tries the ResourceMakers in turn
	for the "best" one that matches.

	If you create new ResourceMakers, you will have to enter them
	*in the correct sequence* in the _resourceMakers list below.

	ResourceMaker instances are called with a resob argument and a set
	of set names.  You will want to override the _makeResource(resob)
	-> xmlstan method and probably the resourceClass element.
	"""
	resourceClass = RI.Resource
	resType = None

	def _loadDependencies(self, resob):
		"""loads all RDs dependent on resob.rd (if present).

		The dependencies are taken from the dc.res_dependencies table.  There,
		they are typically introduced by served-by relationships (see also
		service.declareServes.
		"""
		if not hasattr(resob.rd, "cached dependencies"):
			deps = common.getDependencies(resob.rd.sourceId)
			setattr(resob.rd, "cached dependencies", deps)
		else:
			deps = getattr(resob.rd, "cached dependencies")
		for dep in deps:
			base.caches.getRD(dep)


	def _makeResource(self, resob, setNames):
		self._loadDependencies(resob)
		res = self.resourceClass(**getResourceArgs(resob))[
			VOR.validationLevel(validatedBy=str(resob.getMeta("validatedBy")))[
				resob.getMeta("validationLevel")],
			_vrResourceBuilder.build(resob),]
		# Registry interface mandates ri:Resource (rather than, say, vr:Resource)
		# even in OAI.  No idea why, but let's just force it.
		res._prefix = "ri"
		return res

	def __call__(self, resob, setNames):
		return self._makeResource(resob, setNames)


_rightsBuilder = meta.ModelBasedBuilder([
	('rights', SF(VOR.rights), (), {
		'rightsURI': 'rightsURI'}),])


class ServiceResourceMaker(ResourceMaker):
	"""A ResourceMaker adding rights and capabilities.
	"""
	resourceClass = VS.DataService
	resType = "nonTabularService"

	def _makeResource(self, service, setNames):
		res = ResourceMaker._makeResource(self, service, setNames)[
			_rightsBuilder.build(service)]
		return res[[
					capabilities.getCapabilityElement(pub)
				for pub in service.getPublicationsForSet(setNames)]]


class DataServiceResourceMaker(ServiceResourceMaker):
	"""A ResourceMaker for DataServices.

	These are services that may have instrument, facility, and coverage
	metas but have no associated tables.  This is not generated by the
	service classifier currently since we always have a table.  You can
	force generation of such records via setMeta("resType", "dataService").
	"""
	resourceClass = VS.DataService
	resType = "dataService"

	def _makeResource(self, service, setNames):
		return ServiceResourceMaker._makeResource(self, service, setNames)[
			_orgMetaBuilder.build(service),
			_coverageMetaBuilder.build(service)]


class CatalogServiceResourceMaker(DataServiceResourceMaker):
	resourceClass = VS.CatalogService
	resType = "catalogService"
	def _makeResource(self, service, setNames):
		return DataServiceResourceMaker._makeResource(self, service, setNames)[
			tableset.getTablesetForService(service)]


_registryMetaBuilder = meta.ModelBasedBuilder([
	('managedAuthority', SF(VOG.managedAuthority)),])

	
class RegistryResourceMaker(ServiceResourceMaker):
	resourceClass = VOG.Resource
	resType = "registry"

	def _makeResource(self, registry, setNames):
		return ServiceResourceMaker._makeResource(self, registry, setNames) [
				VOG.full[base.getMetaText(registry, "full", "false")],
				_registryMetaBuilder.build(registry),
				tableset.getTablesetForService(registry)]


class OrgResourceMaker(ResourceMaker):
	resourceClass = VOR.Organisation
	resType = "organization"
	def _makeResource(self, registry, setNames):
		return ResourceMaker._makeResource(self, registry, setNames) [
			_orgMetaBuilder.build(registry)]


class AuthResourceMaker(ResourceMaker):
	resourceClass = VOG.Authority
	resType = "authority"
	def _makeResource(self, registry, setNames):
		return ResourceMaker._makeResource(self, registry, setNames) [
			VOG.managingOrg(
				ivoId=base.getMetaText(registry, "managingOrg.ivo-id", default=None))[
					base.getMetaText(registry, "managingOrg")]]


class StandardsResourceMaker(ResourceMaker):
	resourceClass = VSTD.Standard
	resType = "standard"
	def _makeResource(self, registry, setNames):
		return ResourceMaker._makeResource(self, registry, setNames) [
			_standardsMetaBuilder.build(registry)]


class DocResourceMaker(CatalogServiceResourceMaker):
	resourceClass = DOC.Document
	resType = "document"


class DeletedResourceMaker(ResourceMaker):
	resType = "deleted"
	def _makeResource(self, res, setNames):
		return []


class DataCollectionResourceMaker(ResourceMaker):
	"""A base class for Table- and DataResourceMaker.
	"""
	resourceClass = VS.CatalogResource

	def _makeTableset(self, schemas):
		return tableset.getTablesetForSchemaCollection(schemas)

	def _makeResourceForSchemas(self, metaCarrier, schemas, setNames):
		"""returns xmlstan for schemas within metaCarrier.

		metaCarrier has to provide all the VOR metadata.  schemas is a
		sequence of triples of (rd, tables); rd is used to define a
		VODataService schema, tables is a sequence of TableDefs that
		define the tables within that schema.
		"""
		res = ResourceMaker._makeResource(self, metaCarrier, setNames)[[
					capabilities.getCapabilityElement(pub)
				for pub in metaCarrier.getPublicationsForSet(setNames)],
			_orgMetaBuilder.build(metaCarrier),
			_coverageMetaBuilder.build(metaCarrier),
			self._makeTableset(schemas)]
		return res


class TableResourceMaker(DataCollectionResourceMaker):
	"""A ResourceMaker for rscdef.TableDef items (yielding reformed
	DataCollections)
	"""
	resType = "table"

	def _makeResource(self, td, setNames):
		return DataCollectionResourceMaker._makeResourceForSchemas(
			self, td, [(td.rd, [td])], setNames)


class DataResourceMaker(DataCollectionResourceMaker):
	"""A ResourceMaker for rscdef.DataDescriptor items (yielding reformed
	DataCollections)
	"""
	resType = "data"

	def _makeResource(self, dd, setNames):
		return DataCollectionResourceMaker._makeResourceForSchemas(
			self, dd, [(dd.rd, set(dd.iterTableDefs()))], setNames)


_getResourceMaker = utils.buildClassResolver(ResourceMaker,
	list(globals().values()), instances=True,
	key=lambda obj: obj.resType)


def getVORMetadataElement(resob, setNames=_defaultSet):
	return _getResourceMaker(common.getResType(resob))(resob, setNames)


def getVOResourceElement(resob, setNames=_defaultSet):
	"""returns a stanxml for Resource in VOR format.

	There's trouble here in that we have set management on the level of
	renderers (capabilities).  Thus, to come up with capabilities for
	a given ivorn, we have to know what set is queried.  However,
	OAI GetRecord doesn't specify sets.  So, we provide a default
	set of ivo_managed, assuming that the registry is only interested
	in records actually VO-registred.  This may fly into our face,
	but I can't see a way around it given the way our services are
	described.
	"""
	return getResourceElement(resob, setNames, getVORMetadataElement)


def getVOListRecordsElement(resobs, setNames):
	return getDCListRecordsElement(resobs, setNames,
		getVOResourceElement)


def getVOGetRecordElement(resob):
	return OAI.GetRecord[
		getVOResourceElement(resob)]
