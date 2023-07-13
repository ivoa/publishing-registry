"""
Resources that are not services.
"""

#c Copyright 2008-2023, the GAVO project <gavo@ari.uni-heidelberg.de>
#c
#c This program is free software, covered by the GNU GPL.  See the
#c COPYING file in the source distribution.


from gavo import base
from gavo import rscdef
from gavo import svcs
from gavo.base import meta


class NonServiceResource(
		base.Structure,
		base.StandardMacroMixin,
		base.ComputedMetaMixin):
	"""A base class for resources that are not services.
	"""
	def _meta_identifier(self):
		# Special case the authority
		if base.getMetaText(self, "resType")=="authority":
			localPart = ""
		else:
			localPart = "/%s/%s"%(self.rd.sourceId, self.id)
		return "ivo://%s%s"%(base.getConfig("ivoa", "authority"), localPart)
		

class ResRec(rscdef.IVOMetaMixin, NonServiceResource):
	"""A resource for pure registration purposes.

	A Resource without DaCHS defined behaviour.  This can be
	Organizations or Instruments, but possibly also external services
	
	All resources must either have an id (which is used in the construction of
	their IVOID), or you must give an identifier meta item.
	
	You must further set the following meta items:

	   - resType specifying the kind of resource record.  You should not
	     use this element to build resource records for services or tables
	     (use the normal elements, even if the actual resources are external
	     to DaCHS).  resType can be registry, organization, authority,
	     deleted, or anything else for which registry.builders has a
	     handling class.
	   - title
	   - subject(s)
	   - description
	   - referenceURL
	   - creationDate
	
	Additional meta keys (e.g., accessURL for a registry) may be required
	depending on resType.  See the registry section in the operator's guide.

	ResRecs can also have publication children.  These will be turned into
	the appropriate capabilities depending on the value of the render
	attribute.
	"""
	name_ = "resRec"
	_rd = rscdef.RDAttribute()

	_publications = base.StructListAttribute("publications",
		childFactory=svcs.Publication,
		description="Capabilities the record should have (this is empty"
			" for standards, organisations, instruments, etc.)")

	def onElementComplete(self):
		super().onElementComplete()
		self.setMetaParent(self.rd)

	def getPublicationsForSet(self, names):
		"""returns publications for set names in names.

		names must be a python set.
		"""
		for pub in self.publications:
			if pub.sets&names:
				yield pub

	def getTableSet(self):
		for relatedTable in self.iterMeta("tableset"):
			yield base.resolveCrossId(relatedTable.getContent("text"))

	def _meta_sets(self):
		# This is a copy of the corresponding code in svcs.Service.
		# See there for more info.
		sets = set()
		for p in self.publications:
			sets |= p.sets
		return meta.MetaItem.fromSequence(
			[meta.MetaValue(s) for s in sets])


class _FakeRD(object):
	def __init__(self, id):
		self.sourceId = id


class DeletedResource(NonServiceResource):
	"""a remainder of a deleted resource.  These are always built from information
	in the database, since that is the only place they are remembered.
	"""
	resType = "deleted"

	_resTuple = base.RawAttribute("resTuple")

	def _meta_status(self):
		return "deleted"

	def _meta_identifier(self):
		return self.resTuple["ivoid"]

	def completeElement(self, ctx):
		super().completeElement(ctx)
		self.rd = _FakeRD(self.resTuple["sourceRD"])
		self.id = self.resTuple["resId"]
		self.setMeta("_metadataUpdated", self.resTuple["recTimestamp"])
