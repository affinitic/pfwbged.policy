def patchedNamedBlobFileInit(self, data='', contentType='', filename=None):
    if filename:
        contentType = ''
    self._old___init__(data=data, contentType=contentType, filename=filename)
