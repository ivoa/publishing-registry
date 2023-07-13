"""
Common code and definitions for registry support.
"""

#c Copyright 2008-2023, the GAVO project <gavo@ari.uni-heidelberg.de>
#c
#c This program is free software, covered by the GNU GPL.  See the
#c COPYING file in the source distribution.


from gavo import base
from gavo.utils import stanxml


SERVICELIST_ID = "__system__/services"


METADATA_PREFIXES = [
# (prefix, schema-location, namespace)
	("oai_dc", stanxml.schemaURL("OAI-PMH.xsd"),
		"http://www.openarchives.org/OAI/2.0/oai_dc/"),
	("ivo_vor", stanxml.schemaURL("VOResource-v1.0.xsd"),
		"http://www.ivoa.net/xml/RegistryInterface/v1.0"),
]


class OAIError(base.Error):
	"""is one of the standard OAI errors.
	"""

class BadArgument(OAIError): pass
class BadResumptionToken(OAIError): pass
class BadVerb(OAIError): pass
class CannotDisseminateFormat(OAIError): pass
class IdDoesNotExist(OAIError): pass
class NoMetadataFormats(OAIError): pass
class NoSetHierarchy(OAIError): pass
class NoRecordsMatch(OAIError): pass


def getServicesRD():
	return base.caches.getRD(SERVICELIST_ID)


def getResType(resob):
	res = base.getMetaText(resob, "resType", default=None)
	if res is None:
		res = resob.resType
	return res


def getDependencies(rdId, connection=None):
	"""returns a list of RD ids that are need for the generation of RRs
	from rdId.
	"""
	if connection is None:
		with base.getTableConn() as conn:
			return getDependencies(rdId, conn)

	return [r[0] for r in
		connection.query(getServicesRD().getById("res_dependencies")
			.getSimpleQuery(["prereq"], "rd=%(rd)s"), {"rd": rdId})]


__all__ = ["SERVICELIST_ID", "METADATA_PREFIXES",

"getResType", "getServicesRD", "getDependencies",

"OAIError", "BadArgument", "BadResumptionToken", "BadVerb",
"CannotDisseminateFormat", "IdDoesNotExist",
"NoMetadataFormats", "NoSetHierarchy",
"NoRecordsMatch",
]
