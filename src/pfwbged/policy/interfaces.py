from zope.interface import Interface

from plone.theme.interfaces import IDefaultPloneLayer


class IPfwbgedPolicyLayer(IDefaultPloneLayer):
    """Marker interface that defines a Zope 3 browser layer."""


class IIncomingMailAttributed(Interface):
    """Marker interface added to a task.
    """

class IDocumentsFolder(Interface):
    """Marker interface for the main documents folder"""


class ISubpoolFolder(Interface):
    """Marker interface for folders in the main documents folder"""


class IFoldersFolder(Interface):
    """Marker interface for the main folders folder"""
