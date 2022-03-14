from calibre.customize import InterfaceActionBase

class InterfacePluginDemo(InterfaceActionBase):
    name                = 'Folder to File'
    description         = 'Creates a CBZ / CBC file from a folder of images and adds it to your Calibre library'
    supported_platforms = ['windows', 'osx', 'linux']
    author              = 'Kristopher Barber'
    version             = (1, 0, 0)
    minimum_calibre_version = (5, 0, 0)
    actual_plugin       = 'calibre_plugins.Folder_to_File.ui:Folder_to_File_Interface'

    def is_customizable(self):
        return False


