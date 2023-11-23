IVOA publishing registry code
=============================

While one does not absolutely have to run a publishing registry to `get
into the IVOA Registry`_\ [#reg]_, larger data centres certainly will
want to do that.  As per `Registry Interfaces`_, in principle this does
not require much more than a server speaking `OAI-PMH`_.  However,
assembling the various building blocks has proven to be somewhat
tedious.  This repository's eventual goal is to provide a solid code
base to run a VO-compliant OAI-PMH service with minimal work to
deployers.

.. _OAI-PMH: https://en.wikipedia.org/wiki/Open_Archives_Initiative_Protocol_for_Metadata_Harvesting
.. _Registry Interfaces: http://ivoa.net/documents/RegistryInterface/
.. _get into the IVOA Registry: https://wiki.ivoa.net/twiki/bin/view/IVOA/GettingIntoTheRegistry

In a first step, we collect the server code in use at the various
places.   Let's see what that yields.

Pointers to out-of-repo resources:

* The CDS uses pyoai_
* CADC has a java-based, containerable publishing registry; see
  https://github.com/opencadc/reg/

.. pyoai: https://pypi.org/project/pyoai/

The `generation of VOResource records`_ is explicitly out of scope for
this project; this is far too tightly linked to each data centre's
representation of its resources' metadata.

.. _generation of VOResource records: https://dc.zah.uni-heidelberg.de/purx/q/enroll/info#write-registry-records-from-scratch


Contributed Code
----------------

* DaCHS: this is simply the content of the gavo.registry module as of
  DaCHS 2.8.  Due to its tight integration into the publishing suite
  DaCHS_, it is unlikely that much of this is readily re-usable in
  generic code.  In particular, the resource records are always created
  on the fly in that software.  Most of the code in this directory
  exactly deals with that and hence is, strictly speaking, out of scope.
  Still, a glance at oaiinter may help.

.. _DaCHS: https://soft.g-vo.org/dachs

.. [#reg] If you are unsure what this is talking about, have a look at http://adsabs.harvard.edu/abs/2014A%26C.....7..101D
