if False:
    get_icons = get_resources = None

from calibre.gui2.actions import InterfaceAction
from calibre_plugins.Folder_to_File.main import Folder_Selection_Dialog


class Folder_to_File_Interface(InterfaceAction):

    name = "Folder to File"
    action_spec = (
        "Import Folder",
        None,
        "Add a folder of images to your Calibre library",
        "Ctrl+Shift+F",
    )

    def genesis(self):
        icon = get_icons("images/Folder_to_File.png")
        self.qaction.setIcon(icon)
        self.qaction.triggered.connect(self.show_dialog)

    def show_dialog(self):
        base_plugin_object = self.interface_action_base_plugin
        do_user_config = base_plugin_object.do_user_config

        d = Folder_Selection_Dialog(self.gui, self.qaction.icon(), do_user_config)
        d.show()
