"""
VOResource capability/interface elements.

The basic mapping from our RD elements to VOResource elements is that
each renderer on a service translates to a capability with one interface.
Thus, in the module we mostly deal with publication objects.  If you
need the service object, use publication.parent.
"""

#c Copyright 2008-2023, the GAVO project <gavo@ari.uni-heidelberg.de>
#c
#c This program is free software, covered by the GNU GPL.  See the
#c COPYING file in the source distribution.


import urllib.parse

from gavo import base
from gavo import svcs
from gavo import utils
from gavo.base import meta
from gavo.base import osinter
from gavo.protocols import dali
from gavo.protocols import tap
from gavo.registry import tableset
from gavo.registry.model import (
	VOR, VOG, VS, SIA, SCS, SLAP, SSAP, TR, DOC, DaFut)


###################### Helpers (TODO: Move to tableset, I guess)


def _getParamFromColumn(column, rootElement, typeFactory):
	"""helper for get[Table|Input]ParamFromColumn.
	"""
	return rootElement[
			VS.name[column.name],
			VS.description[column.description],
			VS.unit[column.unit],
			VS.ucd[column.ucd],
			typeFactory(column.type)]


def getInputParamFromColumn(column, rootElement=VS.param):
	"""returns a InputParam element for a rscdef.Column.
	"""
	return _getParamFromColumn(column, rootElement,
		tableset.simpleDataTypeFactory)(
			std=(column.std and "true") or "false")


def getInputParams(publication, service):
	"""returns a sequence of vs:param elements for the input of service.
	"""
	inputParams = []
	renderer = svcs.getRenderer(publication.render)
	if hasattr(service, "getInputKeysFor"): # no params on published tables
		for param in service.getInputKeysFor(renderer):
			# there's similar code in vodal.DALRenderer._getMetadataData;
			# If more mess like this turns up, we'll have to think about
			# a mechanism for per-renderer, pre-service processing, parameter
			# mangling.
			if param.type=="file" and renderer.parameterStyle=="dali":
				param = dali.getUploadKeyFor(param)
			inputParams.append(getInputParamFromColumn(param))

	return inputParams


####################### Interfaces

class InterfaceMaker(object):
	"""An encapsulation of interface construction.

	Each interface maker corresponds to a renderer and thus a publication on a
	service.  It knows enough about the characteristics of a renderer to create
	interface stan by just calling.

	This class is abstract.  To build concrete interface makers, at
	least fill out the class variables.  You will probably want
	to override the _makeInterface method for some renderers corresponding
	so specially defined interfaces; the default implementation corresponds
	to the VOResource definition.
	"""
	renderer = None
	interfaceClass = VOR.interface

	def _makeInterface(self, publication):
		accessURL = base.getMetaText(publication, "accessURL",
					macroPackage=publication.parent)

		parts = urllib.parse.urlparse(accessURL)
		map = svcs.getVanityMap().longToShort
		localpart = parts.path[1:]
		if localpart in map:
			# some DAL protocols want ? or & at the end of their accessURLs.
			# Make sure we keep them
			appendChar = ''
			if accessURL[-1] in "?&":
				appendChar = accessURL[-1]
			accessURL = urllib.parse.urlunsplit(parts[:2]+
				(map[localpart],)+parts[3:5])
			accessURL = accessURL+appendChar

		interface = self.interfaceClass[
			VOR.accessURL(use=base.getMetaText(publication, "urlUse"))[
				accessURL],
			VOR.securityMethod(
				standardId=base.getMetaText(publication, "securityId")),
			[VOR.mirrorURL[v.getContent()]
				for v in publication.iterMeta("mirrorURL")
				if v.getContent()!=accessURL],
		]

		try:
			if base.getConfig("ivoa", "registerAlternative"):
				interface[VOR.mirrorURL[osinter.switchProtocol(accessURL)]]
		except ValueError:
			# probably an external URL that we can't switch
			pass

		return interface

	def __call__(self, publication):
		return self._makeInterface(publication)


class StandardParamHTTP(VS.ParamHTTP):
# Use this for when a standard protocol just wants a vs:ParamHTTP interface.
		_a_role = "std"


class VOSIInterface(InterfaceMaker):
	interfaceClass = StandardParamHTTP


class VOSIAvInterface(VOSIInterface):
	renderer = "availability"

class VOSICapInterface(VOSIInterface):
	renderer = "capabilities"

class VOSITMInterface(VOSIInterface):
	renderer = "tableMetadata"


class DALIInterface(InterfaceMaker):
	interfaceClass = DaFut.daliInterface

	def _makeInterface(self, publication):
		# TODO: figure out where I'll get the endpoints in the end; going
		# by publication's render attribute will make this extremely ugly
		# over time.
		res = InterfaceMaker._makeInterface(self, publication)(version="1.1")
		if publication.render!="dali":
			raise NotImplementedError("Don't know how to make DALIInterfaces"
				" for anything but TAP yet.")
	
		return res[
			DaFut.endpoint[TR.name["sync"]],
			DaFut.endpoint[TR.name["async"],
				DaFut.meta(
					property="http://dc.g-vo.org/static/tap-plan")["dachs"]],
			DaFut.endpoint[TR.name["tables"]],
			DaFut.endpoint[TR.name["examples"]]]


class InterfaceWithParams(InterfaceMaker):
	"""An InterfaceMaker on a publication sporting input parameters.

	This corresponds to a ParamHTTP interface.
	"""
	interfaceClass = VS.ParamHTTP

	def _makeInterface(self, publication):
		paramSrc = publication.parent
		if publication.service:
			paramSrc = publication.service

		return InterfaceMaker._makeInterface(self, publication)[
			VS.queryType[base.getMetaText(
				publication, "requestMethod", propagate=False)],
			VS.resultType[base.getMetaText(
				publication, "resultType", propagate=False)],
			getInputParams(publication, paramSrc)
		]


class SIAPInterface(InterfaceWithParams):
	renderer = "siap.xml"
	interfaceClass = SIA.interface

class SIAP2Interface(InterfaceWithParams):
	renderer = "siap2.xml"
	interfaceClass = SIA.interface

class SCSInterface(InterfaceWithParams):
	renderer = "scs.xml"
	interfaceClass = SCS.interface

class SSAPInterface(InterfaceWithParams):
	renderer = "ssap.xml"
	interfaceClass = SSAP.interface

class SLAPInterface(InterfaceWithParams):
	renderer = "slap.xml"
	interfaceClass = SLAP.interface

class DatalinkInterface(InterfaceWithParams):
	renderer = "dlmeta"
	interfaceClass = StandardParamHTTP

class SODASyncInterface(InterfaceMaker):
	# here, we must not inquire parameters, as the core can only
	# tell when it actually has an ID, which we don't have here.
	renderer = "dlget"
	interfaceClass = StandardParamHTTP

class SODAAsyncInterface(SODASyncInterface):
	# same deal as with SODASyncInterface
	renderer = "dlasync"

class EditionInterface(InterfaceMaker):
	renderer = "edition"
	interfaceClass = VOR.WebBrowser

	def _makeInterface(self, publication):
		return InterfaceMaker._makeInterface(self, publication)(
			role="rendered")


class TAPInterface(InterfaceMaker):
# for TAP, result type is tricky, and we don't have good metadata
# on the accepted input parameters (QUERY, etc).  We should really
# provide them when we have extensions...
	renderer = "dali"
	interfaceClass = TR.interface

	def _makeInterface(self, publication):
		return InterfaceMaker._makeInterface(self, publication)(
			version=tap.TAP_VERSION)


class ExamplesInterface(InterfaceMaker):
	renderer = "examples"
	interfaceClass = VOR.WebBrowser


class SOAPInterface(InterfaceMaker):
	renderer = "soap"
	interfaceClass = VOR.WebService

	def _makeInterface(self, publication):
		return InterfaceMaker._makeInterface(self, publication)[
			VOR.wsdlURL[base.getMetaText(publication, "accessURL")+"?wsdl"],
		]


class OAIHTTPInterface(InterfaceMaker):
	renderer = "pubreg.xml"
	interfaceClass = VOG.OAIHTTP

	def _makeInterface(self, publication):
		return InterfaceMaker._makeInterface(self, publication)(role="std")


class WebBrowserInterface(InterfaceMaker):
	"""An InterfaceMaker on a publication to be consumed by a web browser.

	This is abstract since various renderers boil down to this.
	"""
	interfaceClass = VOR.WebBrowser


class FormInterface(WebBrowserInterface):
	renderer = "form"

class QPInterface(WebBrowserInterface):
	renderer = "qp"

class DocformInterface(WebBrowserInterface):
	renderer = "docform"

# Actually, statics, externals and customs could be anything, but if you
# register it, it's better be something a web browser can handle.

class FixedInterface(WebBrowserInterface):
	renderer = "fixed"

class StaticInterface(WebBrowserInterface):
	renderer = "static"

class CustomInterface(WebBrowserInterface):
	renderer = "custom"

class VolatileInterface(WebBrowserInterface):
	renderer = "volatile"

class ExternalInterface(WebBrowserInterface):
	renderer = "external"

class GetProductInterface(WebBrowserInterface):
	renderer = "get"


_getInterfaceMaker = utils.buildClassResolver(InterfaceMaker,
	list(globals().values()), instances=True,
	key=lambda obj: obj.renderer,
	default=InterfaceWithParams())


####################### Capabilities


class CapabilityMaker(object):
	"""An encapsulation of capability construction.

	Each capability (currently) corresponds to a renderer.

	You will want to override (some of) the class variables at the top, plus the
	_makeCapability method (that you'll probably still want to upcall for the
	basic functionality).

	In particular, you will typically want to override capabilityClass
	with a stanxml element spitting out the right standardIds.
		
	Additionally, if the capability should also appear in data collections
	served by a service with the capability, also define auxiliaryId (that's
	an IVOID like ivo://ivoa.net/std/TAP#aux).  These are used in
	getCapabilityElement.

	CapabilityMakers are used by calling them.
	"""
	renderer = None
	capabilityClass = VOR.capability
	auxiliaryId = None

	def _getInterfaceElement(self, publication):
		"""returns the appropriate interface definition(s) for service and
		renderer.
		"""
		if publication.auxiliary and publication.render=="dali":
			# for now, we want to make ParamHTTP auxiliary interfaces
			# for TAP, not the new-fangled DALI ones.
			interfaceMaker = TAPInterface()
		else:
			interfaceMaker = _getInterfaceMaker(publication.render)
		return interfaceMaker(publication)
	
	def _makeCapability(self, publication):
		return self.capabilityClass[
			VOR.description[base.getMetaText(publication, "description",
				propagate=False, macroPackage=publication.parent)],
			self._getInterfaceElement(publication)]

	def __call__(self, publication):
		return self._makeCapability(publication)


class PlainCapabilityMaker(CapabilityMaker):
	"""A capability maker for generic VR.capabilities.

	These essentially just set standardId, in addition to what
	the plain capabilities do.
	"""
	standardId = None

	def _makeCapability(self, publication):
		return CapabilityMaker._makeCapability(self, publication)(
			standardID=self.standardId)


class APICapabilityMaker(CapabilityMaker):
	renderer = "api"


class SIACapabilityMaker(CapabilityMaker):
	renderer = "siap.xml"
	capabilityClass = SIA.capability
	auxiliaryId = "ivo://ivoa.net/std/SIA#aux"

	def _makeCapability(self, publication):
		service = publication.parent
		return CapabilityMaker._makeCapability(self, publication)[
			SIA.imageServiceType[service.getMeta("sia.type", raiseOnFail=True)],
			SIA.maxQueryRegionSize[
				SIA.long[service.getMeta("sia.maxQueryRegionSize.long", default=None)],
				SIA.lat[service.getMeta("sia.maxQueryRegionSize.lat", default=None)],
			],
			SIA.maxImageExtent[
				SIA.long[service.getMeta("sia.maxImageExtent.long", default=None)],
				SIA.lat[service.getMeta("sia.maxImageExtent.lat", default=None)],
			],
			SIA.maxImageSize[
				service.getMeta("sia.maxImageSize", default=None),
			],
			SIA.maxFileSize[
				service.getMeta("sia.maxFileSize", default=None),
			],
			SIA.maxRecords[
				service.getMeta("sia.maxRecords",
					default=str(base.getConfig("ivoa", "dalHardLimit"))),
			],
			SIA.testQuery[
				SIA.pos[
					SIA.long[service.getMeta("testQuery.pos.ra")],
					SIA.lat[service.getMeta("testQuery.pos.dec")],
				],
				SIA.size[
					SIA.long[service.getMeta("testQuery.size.ra")],
					SIA.lat[service.getMeta("testQuery.size.dec")],
				],
			],
		]


class SIAV2CapabilityMaker(SIACapabilityMaker):
	renderer = "siap2.xml"
	capabilityClass = SIA.capability2
	auxiliaryId = "ivo://ivoa.net/std/SIA#query-aux-2.0"


class SCSCapabilityMaker(CapabilityMaker):
	renderer = "scs.xml"
	capabilityClass = SCS.capability

	def _makeCapability(self, publication):
		service = publication.service
		return CapabilityMaker._makeCapability(self, publication)[
			SCS.maxSR[base.getMetaText(service, "maxSR", "180")],
			SCS.maxRecords[str(base.getConfig("ivoa", "dalDefaultLimit")*10)],
			SCS.verbosity["true"],
			SCS.testQuery[
				SCS.ra[service.getMeta("testQuery.ra", raiseOnFail=True)],
				SCS.dec[service.getMeta("testQuery.dec", raiseOnFail=True)],
				SCS.sr[service.getMeta("testQuery.sr", default="0.001")],
			],
		]


class SSACapabilityMaker(CapabilityMaker):
	renderer = "ssap.xml"
	capabilityClass = SSAP.capability

	def _makeCapability(self, publication):
		service = publication.parent
		cap = CapabilityMaker._makeCapability(self, publication)[
			# XXX TODO: see what we need for "full"
			SSAP.complianceLevel[
				service.getMeta("ssap.complianceLevel", default="minimal")]]

		cap[
			SSAP.dataSource[service.getMeta("ssap.dataSource", raiseOnFail=True)],
			SSAP.creationType[service.getMeta("ssap.creationType",
				default="archival")],
			SSAP.supportedFrame["ICRS"],
			SSAP.maxSearchRadius["90"],
			SSAP.maxRecords[str(base.getConfig("ivoa", "dalHardLimit"))],
			SSAP.defaultMaxRecords[str(base.getConfig("ivoa", "dalDefaultLimit"))],
			SSAP.maxAperture["90"],
			SSAP.testQuery[
				SSAP.queryDataCmd[base.getMetaText(service, "ssap.testQuery",
					raiseOnFail=True)]],
		]
		return cap


class SLAPCapabilityMaker(CapabilityMaker):
	renderer = "slap.xml"
	capabilityClass = SLAP.capability

	def _makeCapability(self, publication):
		service = publication.parent
		return CapabilityMaker._makeCapability(self, publication)[
			SLAP.complianceLevel[
				service.getMeta("slap.complianceLevel", default="full")],
			SSAP.dataSource[service.getMeta("slap.dataSource", raiseOnFail=True)],
			SSAP.testQuery[
				SSAP.queryDataCmd[base.getMetaText(service, "slap.testQuery",
					raiseOnFail=True)]],
		]


_tapModelBuilder = meta.ModelBasedBuilder([
	('supportsModel', meta.stanFactory(TR.dataModel), (),
		{"ivoId": "ivoId"})])

class TAPCapabilityMaker(CapabilityMaker):
	renderer = "dali"
	capabilityClass = TR.capability
	auxiliaryId = "ivo://ivoa.net/std/TAP#aux"

	def _getInterfaceElement(self, publication):
		"""for TAP, we return both a 1.0 pseudo-ParamHTTP and a DALIInterface.

		The DALIInterface part is experimental for now.
		"""
		yield TAPInterface()(publication)
		if "dali-interface-in-tap" in base.getConfig("future"):
			yield DALIInterface()(publication)

	def _makeCapability(self, publication):
		res = CapabilityMaker._makeCapability(self, publication)
	
		with base.getTableConn() as conn:
			from gavo.protocols import tap
			from gavo.adql import ufunctions

			res[[
				TR.dataModel(ivoId=dmivoid)[dmname]
					for dmname, dmivoid in conn.query(
						"select dmname, dmivorn from tap_schema.supportedmodels")]]

			udfs = []
			# the extra set() in the next line is to de-dupe UDFs that have
			# legacy aliases (e.g., gavo_specconv vs. ivo_specconv)
			for udf in set(ufunctions.UFUNC_REGISTRY.values()):
				udfs.append({
						"signature": udf.adqlUDF_signature,
						"doc": udf.adqlUDF_doc})
				udfs.extend(udf.adqlUDF_additionalSignatures)

			res[
				# Once we support more than one language, we'll have to
				# revisit this -- the optional features must then become
				# a property of the language.
				[TR.language[
						TR.name[langName],
						[TR.version(ivoId=ivoId)[version]
							for version, ivoId in versions],
						TR.description[description],
						TR.languageFeatures(
							type="ivo://ivoa.net/std/TAPRegExt#features-udf")[
							[TR.feature[
								TR.form[udf["signature"]],
								TR.description[udf["doc"]]]
							for udf in sorted(udfs, key=lambda v: v["signature"])]],

						TR.languageFeatures(
								type="ivo://ivoa.net/std/TAPRegExt#features-adqlgeo")[
							[TR.feature[
								TR.form[funcName]]
							for funcName in ("BOX", "POINT", "CIRCLE", "POLYGON",
									"REGION", "CENTROID", "COORD1", "COORD2",
									"DISTANCE", "CONTAINS", "INTERSECTS", "AREA")]],

						TR.languageFeatures(
								type="ivo://ivoa.net/std/TAPRegExt#features-adql-string")[
							[TR.feature[
								TR.form[funcName]]
							for funcName in ("LOWER", "ILIKE")]],

						TR.languageFeatures(
								type="ivo://ivoa.net/std/TAPRegExt#features-adql-offset")[
							[TR.feature[
								TR.form[funcName]]
							for funcName in ("OFFSET",)]],

						TR.languageFeatures(
								type="ivo://ivoa.net/std/TAPRegExt#features-adql-type")[
							[TR.feature[
								TR.form[funcName]]
							for funcName in ("CAST",)]],

						TR.languageFeatures(
								type="ivo://ivoa.net/std/TAPRegExt#features-adql-unit")[
							[TR.feature[
								TR.form[funcName]]
							for funcName in ("IN_UNIT",)]],

						TR.languageFeatures(
								type="ivo://ivoa.net/std/TAPRegExt#features-adql-common-table")[
							[TR.feature[
								TR.form[funcName]]
							for funcName in ("WITH",)]],

						TR.languageFeatures(
								type="ivo://org.gavo.dc/std/exts#extra-adql-keywords")[
							TR.feature[
								TR.form["TABLESAMPLE"],
								TR.description["Written after a table reference,"
									" TABLESAMPLE(10) will make the database only use"
									" 10% of the rows; these are `somewhat random' in"
									" that the system will use random blocks.  This"
									" should be good enough when just testing queries"
									" (and much better than using TOP n)."]],
							TR.feature[
								TR.form["MOC"],
								TR.description["A geometry function creating MOCs."
									"  It either takes a string argument with an ASCII"
									" MOC ('4/13 17-18 8/3002'), or an order and another"
									" geometry."]],
							TR.feature[
								TR.form["COALESCE"],
								TR.description["This is the standard SQL COALESCE"
									" for providing defaults in case of NULL values."]],
							TR.feature[
								TR.form["VECTORMATH"],
								TR.description["You can compute with vectors here. See"
									" https://wiki.ivoa.net/twiki/bin/view/IVOA/ADQLVectorMath"
									" for an overview of the functions and operators available."],
							],
							TR.feature[
								TR.form["CASE"],
								TR.description["The SQL92 CASE expression"],
							],
						],

						TR.languageFeatures(
								type="ivo://ivoa.net/std/TAPRegExt#features-adql-sets")[
							[TR.feature[
								TR.form[funcName]]
							for funcName in ("UNION", "EXCEPT", "INTERSECT")]]]
					for langName, description, versions
						in tap.getSupportedLanguages()],
				[TR.outputFormat(ivoId=ivoId)[
						TR.mime[mime],
							[TR.alias[alias] for alias in aliases]]
					for mime, aliases, description, ivoId
						in tap.getSupportedOutputFormats()],
				[TR.uploadMethod(ivoId="ivo://ivoa.net/std/TAPRegExt#%s"%proto)
					for proto in tap.UPLOAD_METHODS],
				TR.retentionPeriod[
					TR.default[str(base.getConfig("async", "defaultLifetime"))]],
				TR.executionDuration[
					TR.default[str(base.getConfig("async", "defaultExecTime"))]],
				TR.outputLimit[
					TR.default(unit="row")[
						str(base.getConfig("async", "defaultMAXREC"))],
					TR.hard(unit="row")[
						str(base.getConfig("async", "hardMAXREC"))]],
				TR.uploadLimit[
					TR.hard(unit="byte")[
						str(base.getConfig("web", "maxUploadSize"))]]]
		
		return res


class RegistryCapabilityMaker(CapabilityMaker):
	renderer = "pubreg.xml"
	capabilityClass = VOG.Harvest
	def _makeCapability(self, publication):
		return CapabilityMaker._makeCapability(self, publication)[
			VOG.maxRecords[str(base.getConfig("ivoa", "oaipmhPageSize"))]]


class VOSICapabilityMaker(PlainCapabilityMaker):
	# A common parent for the VOSI cap. makers.  All of those are
	# parallel and only differ by standardID
	capabilityClass = VOG.capability


class VOSIAvCapabilityMaker(VOSICapabilityMaker):
	renderer = "availability"
	standardId = "ivo://ivoa.net/std/VOSI#availability"

class VOSICapCapabilityMaker(VOSICapabilityMaker):
	renderer = "capabilities"
	standardId = "ivo://ivoa.net/std/VOSI#capabilities"

class VOSITMCapabilityMaker(VOSICapabilityMaker):
	renderer = "tableMetadata"
	standardId = "ivo://ivoa.net/std/VOSI#tables"

class ExamplesCapabilityMaker(PlainCapabilityMaker):
	renderer = "examples"
	standardId = "ivo://ivoa.net/std/DALI#examples"

class HiPSCapabilityMaker(PlainCapabilityMaker):
	renderer = "hips"
	standardId = "ivo://ivoa.net/std/hips#hips-1.0"
	interfaceClass = StandardParamHTTP

class SOAPCapabilityMaker(CapabilityMaker):
	renderer = "soap"

class FormCapabilityMaker(CapabilityMaker):
	renderer = "form"

class QPCapabilityMaker(CapabilityMaker):
	renderer = "qp"

class ExternalCapabilityMaker(CapabilityMaker):
	renderer = "external"

class StaticCapabilityMaker(CapabilityMaker):
	renderer = "static"

class VolatileCapabilityMaker(CapabilityMaker):
	renderer = "volatile"

class CustomCapabilityMaker(CapabilityMaker):
	renderer = "custom"

class JPEGCapabilityMaker(CapabilityMaker):
	renderer = "img.jpeg"

class FixedCapabilityMaker(CapabilityMaker):
	renderer = "fixed"

class DocformCapabilityMaker(CapabilityMaker):
	renderer = "docform"

class ProductCapabilityMaker(CapabilityMaker):
	renderer = "get"


class DatalinkCapabilityMaker(CapabilityMaker):
	renderer = "dlmeta"

	class capabilityClass(VOR.capability):
		_a_standardID = "ivo://ivoa.net/std/DataLink#links-1.1"


class SODACapabilityMaker(CapabilityMaker):
	renderer = "dlget"

	class capabilityClass(VOR.capability):
		_a_standardID = "ivo://ivoa.net/std/SODA#sync-1.0"


class SODAAsyncCapabilityMaker(CapabilityMaker):
	renderer = "dlasync"

	class capabilityClass(VOR.capability):
		_a_standardID = "ivo://ivoa.net/std/SODA#async-1.0"


class EditionCapabilityMaker(CapabilityMaker):
	renderer = "edition"

	capabilityClass = DOC.capability

	def _makeCapability(self, publication):
		res = CapabilityMaker._makeCapability(self, publication)

		# if there's sourceURL meta, add an interface
		for su in publication.iterMeta("sourceURL"):
			res[
				VOR.WebBrowser(role="source")[
					VOR.accessURL[su.getContent()]]]

		return res[
			DOC.languageCode[
				base.getMetaText(publication, "languageCode", "en")],
			DOC.locTitle[
				base.getMetaText(publication, "locTitle", None)]]


_getCapabilityMaker = utils.buildClassResolver(CapabilityMaker,
	list(globals().values()), instances=True,
	key=lambda obj: obj.renderer)


def getAuxiliaryCapability(publication):
	"""returns a VR.capability element for an auxiliary publication.

	That's a plain capability with essentially the interface and a
	standardId obtained from the auxiliaryId attribute of the
	capability's normal maker.

	If no auxiliaryId is defined, None is returned (which means no
	capability will be generated).
	"""
	capMaker = _getCapabilityMaker(publication.render)
	if capMaker.auxiliaryId:
		return CapabilityMaker()(publication)(standardID=capMaker.auxiliaryId)


def getCapabilityElement(publication):
	"""returns the appropriate capability definition for a publication object.
	"""
	if publication.auxiliary:
		return getAuxiliaryCapability(publication)
	else:
		try:
			maker = _getCapabilityMaker(publication.render)
		except KeyError:
			raise base.ui.logOldExc(base.ReportableError("Do not know how to"
				" produce a capability for the '%s' renderer"%publication.render))
		return maker(publication)
