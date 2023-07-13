"""
The schema and XML namespaces for OAI/VOR documents.
"""

#c Copyright 2008-2023, the GAVO project <gavo@ari.uni-heidelberg.de>
#c
#c This program is free software, covered by the GNU GPL.  See the
#c COPYING file in the source distribution.


from gavo import base
from gavo.utils.stanxml import Element, schemaURL, registerPrefix, xsiPrefix


class Error(base.Error):
	pass


# See stanxml for the root of all the following evil.
# If you change schemaURL here, you will quite certainly have
# to fix testtricks.VO_SCHEMATA as well.
registerPrefix("oai", "http://www.openarchives.org/OAI/2.0/",
	schemaURL("OAI-PMH.xsd"))
registerPrefix("oai_dc", "http://www.openarchives.org/OAI/2.0/oai_dc/",
	schemaURL("oai_dc.xsd"))
registerPrefix("ri",
	"http://www.ivoa.net/xml/RegistryInterface/v1.0",
	schemaURL("RegistryInterface.xsd"))
registerPrefix("vg", "http://www.ivoa.net/xml/VORegistry/v1.0",
	schemaURL("VORegistry.xsd"))
registerPrefix("vr", "http://www.ivoa.net/xml/VOResource/v1.0",
	schemaURL("VOResource.xsd"))
registerPrefix("dc", "http://purl.org/dc/elements/1.1/",
	schemaURL("simpledc20021212.xsd"))
registerPrefix("vs", "http://www.ivoa.net/xml/VODataService/v1.1",
	schemaURL("VODataService.xsd"))
registerPrefix("cs", "http://www.ivoa.net/xml/ConeSearch/v1.0",
	schemaURL("ConeSearch.xsd"))
registerPrefix("sia", "http://www.ivoa.net/xml/SIA/v1.1",
	schemaURL("SIA.xsd"))
registerPrefix("slap", "http://www.ivoa.net/xml/SLAP/v1.0",
	schemaURL("SLAP.xsd"))
registerPrefix("ssap", "http://www.ivoa.net/xml/SSA/v1.1",
	schemaURL("SSA.xsd"))
registerPrefix("tr", "http://www.ivoa.net/xml/TAPRegExt/v1.0",
	schemaURL("TAPRegExt.xsd"))
registerPrefix("vstd", "http://www.ivoa.net/xml/StandardsRegExt/v1.0",
	schemaURL("StandardsRegExt.xsd"))
registerPrefix("doc", "http://www.ivoa.net/xml/DocRegExt/v1",
	schemaURL("DocRegExt.xsd"))
registerPrefix("voe", "http://www.ivoa.net/xml/VOEventRegExt/v2",
	schemaURL("VOEventRegExt.xsd"))
registerPrefix("g-colstat", "http://dc.g-vo.org/ColStats-1",
	schemaURL("Colstats.xsd"))
registerPrefix("eudc", "http://schema.eudat.eu/schema/kernel-1",
	schemaURL("eudat-core.xsd"))
registerPrefix("dachs", "http://docs.g-vo.org/schemata/DaCHS.xsd",
	schemaURL("DaCHS.xsd"))


class _ResourceNameMixin(object):
	_a_ivoId = None
	_name_a_ivoId = "ivo-id"


class OAI(object):
	"""is a container for classes modelling OAI elements.
	"""
	class OAIElement(Element):
		_prefix = "oai"

	class PMH(OAIElement):
		name_ = "OAI-PMH"
	
	class responseDate(OAIElement): pass

	class request(OAIElement):
		_mayBeEmpty = True
		_a_verb = None
		_a_metadataPrefix = None

	class metadata(OAIElement): pass

	class Identify(OAIElement): pass

	class ListIdentifiers(OAIElement): pass

	class ListRecords(OAIElement): pass

	class GetRecord(OAIElement): pass
	
	class ListMetadataFormats(OAIElement): pass

	class ListSets(OAIElement):
			_mayBeEmpty = True

	class header(OAIElement):
		_a_status = None

	class error(OAIElement):
		_mayBeEmpty = True
		_a_code = None

	class record(OAIElement): pass

	class identifier(OAIElement): pass
	
	class datestamp(OAIElement): pass
	
	class setSpec(OAIElement): pass

	class repositoryName(OAIElement): pass
	
	class baseURL(OAIElement): pass
	
	class adminEmail(OAIElement): pass
	
	class earliestDatestamp(OAIElement): pass
	
	class deletedRecord(OAIElement): pass
	
	class granularity(OAIElement): pass

	class description(OAIElement): pass
	
	class protocolVersion(OAIElement): pass

	class metadataFormat(OAIElement): pass

	class metadataPrefix(OAIElement): pass
	
	class schema(OAIElement): pass

	class metadataNamespace(OAIElement): pass

	class set(OAIElement): pass
	
	class setName(OAIElement): pass

	class setDescription(OAIElement): pass

	class resumptionToken(OAIElement): pass
		# optional attributes not supported here
		# The string value in here has a structure; see oaiinter.


class OAIDC:
	"""is a container for OAI's Dublin Core metadata model.
	"""
	class OAIDCElement(Element):
		_prefix = "oai_dc"
	
	class dc(OAIDCElement):
		pass


class VOR:
	"""is a container for classes modelling elements from VO Resource.
	"""
	class VORElement(Element):
		_prefix = "vr"
		_local = True

	class Resource(VORElement):
# This is "abstract" in that only derived elements may be present
# in an instance document (since VOR doesn't define any global elements).
# Typically, this will be vr:Resource elements with some funky xsi:type
		_a_created = None
		_a_updated = None
		_a_status = None
		name_ = "Resource"
		_local = False
		_additionalPrefixes = frozenset(["vr", "ri", "xsi"])

		def __repr__(self):
			# see if we can find out our identifier -- that's going to help
			# in debugging.
			identifier = "(unknown)"
			for child in self.iterChildrenWithName("identifier"):
				identifier = child.text_
				break

			return "<%s: %s>"%(
				self.__class__.__name__.split(".")[-1],
				identifier)


	class Organisation(Resource):
		_a_xsi_type = "vr:Organisation"
		
	class Service(Resource):
		_a_xsi_type = "vr:Service"

	class validationLevel(VORElement):
		_a_validatedBy = None
	
	class title(VORElement): pass
	
	class shortName(VORElement): pass

	class ResourceName(VORElement):
		_a_ivoId = None
		_name_a_ivoId = "ivo-id"
		_a_altIdentifier = None

	class identifier(VORElement): pass

	class altIdentifier(VORElement): pass

	class curation(VORElement): pass
	
	class content(VORElement): pass

	class creator(VORElement): pass
	
	class contributor(ResourceName): pass
	
	class date(VORElement):
		_a_role = None

	class version(VORElement): pass
	
	class contact(VORElement): pass
	
	class publisher(ResourceName): pass

	class facility(VORElement): pass

	class instrument(ResourceName): pass
	
	class name(VORElement): pass
	
	class address(VORElement): pass
	
	class email(VORElement): pass
	
	class telephone(VORElement): pass
	
	class logo(VORElement): pass
	
	class subject(VORElement): pass
	
	class description(VORElement): pass
	
	class source(VORElement):
		_a_format = None
	
	class referenceURL(VORElement): pass
	
	class type(VORElement): pass
	
	class contentLevel(VORElement): pass
	
	class relationship(VORElement):
		def _setupNode(self):
			self.__isEmpty = None
			self._setupNodeNext(VOR.relationship)

		def isEmpty(self):
			# special rule: a relationship is empty if there's no relatedResource
			# in them (this is a simplification of "don't count relationshipType
			# since it's always non-empty").
			if self._isEmptyCache is None:
				self._isEmptyCache = True
				for c in self.iterChildrenOfType(VOR.relatedResource):
					self._isEmptyCache = False
					break
			return self._isEmptyCache

	class relationshipType(VORElement): pass
	
	class relatedResource(VORElement):
		_a_ivoId = None
		_name_a_ivoId = "ivo-id"

	class rights(VORElement):
		_a_rightsURI = None
	
	class capability(VORElement):
		name_ = "capability"
		_additionalPrefixes = xsiPrefix
		_a_standardID = None
	
	class interface(VORElement):
		name_ = "interface"
		_additionalPrefixes = xsiPrefix
		_a_version = None
		_a_role = None
		_a_qtype = None

	class WebBrowser(interface):
		_a_xsi_type = "vr:WebBrowser"
	
	class WebService(interface):
		_a_xsi_type = "vr:WebService"

	class wsdlURL(VORElement): pass

	class accessURL(VORElement):
		_a_use = None
	
	class mirrorURL(VORElement): pass

	class securityMethod(VORElement):
		def isEmpty(self):
			return self.standardId is None
		_a_standardId = None
	

class RI:
	"""is a container for classes modelling elements from IVOA Registry Interface.
	"""
	class RIElement(Element):
		_prefix = "ri"
	
	class VOResources(RIElement): pass

	class Resource(VOR.Resource):
		_prefix = "ri"


class VOG:
	"""is a container for classes modelling elements from VO Registry.
	"""
	class VOGElement(Element):
		_prefix = "vg"
		_local = True

	class Resource(RI.Resource):
		_a_xsi_type = "vg:Registry"
		_additionalPrefixes = frozenset(["vg", "xsi"])

	class Authority(RI.Resource):
		_a_xsi_type = "vg:Authority"
		_additionalPrefixes = frozenset(["vg", "xsi"])

	class capability(VOR.capability):
		_a_standardID = "ivo://ivoa.net/std/Registry"
	
	class Harvest(capability):
		_a_xsi_type = "vg:Harvest"
		_additionalPrefixes = frozenset(["vg", "xsi", "vs"])

	class Search(VOGElement):
		_a_xsi_type = "vg:Search"
		_additionalPrefixes = frozenset(["vg", "xsi", "vs"])

	class OAIHTTP(VOR.interface):
		_a_xsi_type = "vg:OAIHTTP"
		# namespace declaration has happened in enclosing element

	class OAISOAP(VOR.interface):
		_a_xsi_type = "vg:OAISOAP"
		# namespace declaration has happened in enclosing element

	class full(VOGElement): pass
	
	class managedAuthority(VOGElement): pass
	
	class validationLevel(VOGElement): pass
	
	class description(VOGElement): pass
	
	class interface(VOGElement): pass
	
	class maxRecords(VOGElement): pass

	class extensionSearchSupport(VOGElement): pass
	
	class optionalProtocol(VOGElement): pass
	
	class managingOrg(VOGElement, _ResourceNameMixin): pass

	
class DC:
	"""is a container for classes modelling elements from Dublin Core.
	"""
	class DCElement(Element):
		_prefix = "dc"

	class contributor(DCElement): pass

	class coverage(DCElement): pass

	class creator(DCElement): pass

	class date(DCElement): pass

	class description(DCElement): pass

	class format(DCElement): pass

	class identifier(DCElement): pass

	class language(DCElement): pass

	class publisher(DCElement): pass

	class relation(DCElement): pass

	class rights(DCElement): pass

	class source(DCElement): pass

	class subject(DCElement): pass

	class title(DCElement): pass

	class type(DCElement): pass


class VS:
	"""A container for classes modelling elements from VODataService 1.2.
	"""
	class VSElement(Element):
		_prefix = "vs"
		_local = True

	class DataCollection(RI.Resource):
		_a_xsi_type = "vs:DataCollection"
		_additionalPrefixes = frozenset(["vs", "xsi"])

	class tableset(VSElement):
		_additionalPrefixes = xsiPrefix
		_childSequence = ["schema"]
	
	class schema(VSElement):
		_childSequence = ["name", "title", "description", "utype",
			"table"]
	
	class title(VSElement): pass
	class utype(VSElement): pass
	class nrows(VSElement): pass
	
	class table(VSElement):
		_a_type = None
		_childSequence = ["name", "title", "description", "utype",
			"nrows", "column", "foreignKey"]

	class foreignKey(VSElement):
		_childSequence = ["targetTable", "fkColumn", "description", "utype"]
	
	class targetTable(VSElement): pass
	
	class fkColumn(VSElement):
		_childSequence = ["fromColumn", "targetColumn"]

	class fromColumn(VSElement): pass
	class targetColumn(VSElement): pass
	class flag(VSElement): pass
	class regionOfRegard(VSElement): pass

	class facility(VSElement): pass
	
	class instrument(VSElement): pass
	
	class coverage(VSElement): pass

	class footprint(VSElement):
		_a_ivoId = None
		_name_a_ivoId = "ivo-id"

	class waveband(VSElement): pass

	class spectral(VSElement): pass

	class spatial(VSElement): pass

	class temporal(VSElement): pass

	class format(VSElement):
		_a_isMIMEType = None
	
	class accessURL(VSElement): pass
	
	class ParamHTTP(VOR.interface):
		_a_xsi_type = "vs:ParamHTTP"
		_additionalPrefixes = frozenset(["vg", "xsi"])

	class resultType(VSElement): pass
	
	class queryType(VSElement): pass

	class param(VSElement):
		_a_std = "false"
	
	class name(VSElement): pass
	
	class description(VSElement): pass

	class unit(VSElement): pass
	
	class ucd(VSElement): pass

	class Service(VOR.Resource): pass

	class DataResource(Service):
		_a_xsi_type = "vs:DataResource"
		_additionalPrefixes = frozenset(["vs", "xsi"])

	class DataService(DataResource):
		_a_xsi_type = "vs:DataService"

	class CatalogResource(DataResource):
		_a_xsi_type = "vs:CatalogResource"

	class CatalogService(CatalogResource):
		_a_xsi_type = "vs:CatalogService"
		_additionalPrefixes = frozenset(["vs", "xsi"])

	class ServiceReference(VSElement):
		_a_ivoId = None
		_name_a_ivoId = "ivo-id"

	# column for now contains our prototype g-colstat attributes;
	# these ought to be removed as we leave the prototyping state.
	# In particular, the _additionalPrefixes should go again then
	class column(VSElement):
		_additionalPrefixes = frozenset(["g-colstat"])
		_a_minValue = None
		_name_a_minValue = "g-colstat:min-value"
		_a_maxValue = None
		_name_a_maxValue = "g-colstat:max-value"
		_a_median = None
		_name_a_median = "g-colstat:median"
		_a_percentile03 = None
		_name_a_percentile03 = "g-colstat:percentile03"
		_a_percentile97 = None
		_name_a_percentile97 = "g-colstat:percentile97"
		_a_fillFactor = None
		_name_a_fillFactor = "g-colstat:fillFactor"

	class dataType(VSElement):
		name_ = "dataType"
		_additionalPrefixes = xsiPrefix
		_a_arraysize = None
		_a_delim = None
		_a_extendedSchema = None
		_a_extendedType = None
		_a_xsi_type = None

	class dataType(dataType):
		name_ = "dataType"

	class voTableDataType(dataType):
		name_ = "dataType"
		_a_xsi_type = "vs:VOTableType"

	class tapType(dataType):
		name_ = "dataType"
		_a_size = None
		_a_xsi_type = "vs:TAPType"


class SIA(object):
	"""A container for classes modelling elements for describing simple
	image access services.
	"""
	class SIAElement(Element):
		_prefix = "sia"
		_local = True

	class interface(VOR.interface):
		_prefix = "sia"
		_a_role = "std"
		_additionalPrefixes = frozenset(["vs", "xsi"])
		_a_xsi_type = "vs:ParamHTTP"

	class capability(VOR.capability):
		_a_standardID = 	"ivo://ivoa.net/std/SIA"
		_a_xsi_type = "sia:SimpleImageAccess"
		_additionalPrefixes = frozenset(["sia", "xsi"])

	class capability2(capability):
		# an artificial class to let me fix the standard id for SIAPv2
		_a_standardID =	"ivo://ivoa.net/std/SIA#query-2.0"

	class imageServiceType(SIAElement): pass
	
	class maxQueryRegionSize(SIAElement): pass
	
	class maxImageExtent(SIAElement): pass
	
	class maxImageSize(SIAElement): pass

	class maxFileSize(SIAElement): pass

	class maxRecords(SIAElement): pass

	class long(SIAElement): pass
	
	class lat(SIAElement): pass

	class testQuery(SIAElement): pass
	
	class pos(SIAElement): pass
	
	class size(SIAElement): pass

	
class SCS(object):
	"""A container for elements describing Simple Cone Search services.
	"""
	class SCSElement(Element):
		_prefix = "cs"
		_local = True

	class interface(VOR.interface):
		_prefix = "cs"
		_a_role = "std"
		_a_xsi_type = "vs:ParamHTTP"
		_additionalPrefixes = frozenset(["xsi", "vs"])

	class capability(VOR.capability):
		_a_standardID = 	"ivo://ivoa.net/std/ConeSearch"
		_a_xsi_type = "cs:ConeSearch"
		_additionalPrefixes = frozenset(["xsi", "vs"])
	
	class maxSR(SCSElement): pass
	
	class maxRecords(SCSElement): pass
	
	class verbosity(SCSElement): pass

	class testQuery(SCSElement): pass
	class ra(SCSElement): pass
	class dec(SCSElement): pass
	class sr(SCSElement): pass
	class extras(SCSElement): pass


class SSAP(object):
	"""A container for the elements of the SSA registry extension.
	"""
	class SSAElement(Element):
		_prefix = "ssap"
		_local = True
	
	class capability(VOR.capability):
		_a_standardID = "ivo://ivoa.net/std/SSA"
		_a_xsi_type = "ssap:SimpleSpectralAccess"
		_additionalPrefixes = frozenset(["xsi", "vs"])

	class interface(VOR.interface):
		_prefix = "ssap"
		_a_role = "std"
		_additionalPrefixes = frozenset(["vs", "xsi"])
		_a_xsi_type = "vs:ParamHTTP"

	class complianceLevel(SSAElement): pass
	class dataSource(SSAElement): pass
	class creationType(SSAElement): pass
	class maxSearchRadius(SSAElement): pass
	class maxRecords(SSAElement): pass
	class defaultMaxRecords(SSAElement): pass
	class maxAperture(SSAElement): pass
	class maxFileSize(SSAElement): pass
	class supportedFrame(SSAElement): pass
	class testQuery(SSAElement): pass
	class queryDataCmd(SSAElement): pass


class SLAP(object):
	"""A container for the elements of the SSA registry extension.
	"""
	class SLAPElement(Element):
		_prefix = "slap"
		_local = True
	
	class capability(VOR.capability):
		_a_standardID = "ivo://ivoa.net/std/SLAP"
		_a_xsi_type = "slap:SimpleLineAccess"
		_additionalPrefixes = frozenset(["xsi", "vs"])

	class interface(VOR.interface):
		_a_role = "std"
		_additionalPrefixes = frozenset(["vs", "xsi"])
		_a_xsi_type = "vs:ParamHTTP"

	class complianceLevel(SLAPElement): pass
	class dataSource(SLAPElement): pass
	class testQuery(SLAPElement): pass
	class queryDataCmd(SLAPElement): pass


class TR(object):
	"""A container for elements describing TAP services.
	"""
	class TRElement(Element):
		_prefix = "tr"
		_local = True

	class interface(VOR.interface):
		_a_role = "std"
		_a_xsi_type = "vs:ParamHTTP"
		_additionalPrefixes = frozenset(["xsi", "vs"])

	class daliInterface(VOR.interface):
		name_ = "interface"
		_a_role = "std"
		_a_xsi_type = "tr:DALIInterface"
		_additionalPrefixes = frozenset(["xsi"])

	class capability(VOR.capability):
		_a_standardID = 	"ivo://ivoa.net/std/TAP"
		_a_xsi_type = "tr:TableAccess"
		_additionalPrefixes = frozenset(["tr", "xsi"])

	class endpoint(TRElement):
		pass
	
	class meta(TRElement):
		_a_about = None
		_a_property = None
		_a_resource = None

	class dataModel(TRElement):
		_a_ivoId = None
		_name_a_ivoId = "ivo-id"

	class label(TRElement):
		pass

	class language(TRElement):
		_a_LANG = None
	
	class outputFormat(TRElement):
		_a_FORMAT = None
		_a_mime = None
		_a_ivoId = None
		_name_a_ivoId = "ivo-id"
	
	class uploadMethod(TRElement):
		_mayBeEmpty = True
		_a_protocol = None
		_a_ivoId = None
		_name_a_ivoId = "ivo-id"

	class default(TRElement):
		_a_unit = None

	class hard(TRElement):
		_a_unit = None

	class version(TRElement):
		_a_ivoId = None
		_name_a_ivoId = "ivo-id"

	class languageFeatures(TRElement):
		_a_type = None

	class alias(TRElement): pass
	class description(TRElement): pass
	class executionDuration(TRElement): pass
	class mime(TRElement): pass
	class name(TRElement): pass
	class parameter(TRElement): pass
	class protocol(TRElement): pass
	class retentionPeriod(TRElement): pass
	class outputLimit(TRElement): pass
	class form(TRElement): pass
	class uploadLimit(TRElement): pass
	class feature(TRElement): pass


class VSTD(object):
	"""A container for elements from StandardsRegExt.
	"""
	class VSTDElement(Element):
		_prefix = "vstd"
		_local = True

	class endorsedVersion(VSTDElement):
		_a_status = "n/a"
		_a_use = "preferred"
	
	class Standard(RI.Resource):
		_a_xsi_type = "vstd:Standard"
		_additionalPrefixes = frozenset(["vstd", "xsi"])

	class deprecated(VSTDElement): pass
	class key(VSTDElement): pass
	class description(VSTDElement): pass
	class name(VSTDElement): pass


class DOC(object):
	"""A container for elements from DocRegExt.
	"""
	class DOCElement(Element):
		_prefix = "doc"
		_local = True

	class Document(RI.Resource):
		_a_xsi_type = "doc:Document"
		_additionalPrefixes = frozenset(["doc", "xsi"])

	class capability(DOCElement):
		_a_xsi_type = "doc:Edition"
		_a_languageCode = None
		_a_locTitle = None

	class languageCode(DOCElement): pass
	class locTitle(DOCElement): pass


class DaFut(object):
	"""A container for XSD elements we want to push into other schemas
	one of these days ("DaCHS Future").
	"""
	class DaFutElement(Element):
		_prefix = "dachs"
		_local = True

	class daliInterface(VOR.interface):
		name_ = "interface"
		_a_role = "std"
		_a_xsi_type = "dachs:DALIInterface"
		_additionalPrefixes = frozenset(["xsi"])

	class endpoint(DaFutElement):
		pass
	
	class meta(DaFutElement):
		_a_about = None
		_a_property = None
		_a_resource = None
