CBZ_regex = r"^(?P<Title>.+?)( - c(?P<ChapterNum>\d+))?( \(v(?P<VolumeNum>\d+)\))? - p(?P<Page>\d+(-\d+)?)( \[(?P<ChapterName>.+?)\])?( {(?P<Publisher>.+?)})? ?(?P<Extension>\.\w+)$"

configuration_explanation = """#Use the text box to configure which files are placed into which chapters of the CBC file.
#Chapters should be in the format "filename.cbz : chapter name"
#Pages should be formatted with tabs between the original and the new filename "\toriginal_filename\t=>\tnew_filename"
#Example:
#
#001.cbz : Chapter 1 : Departure
#\tRoxy Gets Serious [Departure] 001.jpg\t=>\t001.jpg
#\tRoxy Gets Serious [Departure] 002.jpg\t=>\t002.jpg
#\t. . .
#002.cbz : Chapter 2 : The Town of Rikarisu
#\tRoxy Gets Serious [The Town of Rikarisu] 037.jpg\t=>\t037.jpg
#\tRoxy Gets Serious [The Town of Rikarisu] 038.jpg\t=>\t038.jpg
#\t. . .
"""

if False:
    get_icons = get_resources = None

from qt.core import (
    QDialog,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QDialogButtonBox,
    QTextEdit,
    QTextCursor,
)
from calibre.gui2 import error_dialog, info_dialog
from calibre.gui2.add import Adder

from urllib.parse import urlparse
import os
from zipfile import ZipFile
import re
from pathlib import Path


def CBZ_Cleaner(string):
    string = string.replace("[dig]", "")
    string = string.replace("[Cover]", "")
    string = string.replace("[Seven Seas]", "")
    string = string.replace("[danke-Empire]", "")
    string = string.replace("{HQ}", "")
    string = string.replace("[Omake]", "")
    string = string.replace("[ToC]", "")
    string = " ".join(string.split())
    return string


def image_filter(name):
    extension = name[name.rfind(".") :].lower()
    return extension in [".png", ".jpg", ".jpeg", ".gif", ".tiff", ".bmp"]


class Folder_Selection_Dialog(QDialog):
    def __init__(self, gui, icon, do_user_config):
        QDialog.__init__(self, gui)
        self.setAcceptDrops(True)
        self.gui = gui
        self.do_user_config = do_user_config

        self.db = gui.current_db

        self.l = QVBoxLayout()
        self.setLayout(self.l)

        self.setWindowTitle("Select folder(s):")
        self.setWindowIcon(icon)

        self.label = QLabel("Path(s) to folder(s):")
        self.l.addWidget(self.label)

        self.selected_folder = QTextEdit()
        self.selected_folder.setAcceptRichText(False)
        self.selected_folder.setTabStopDistance(40)
        self.l.addWidget(self.selected_folder)

        self.label.setBuddy(self.selected_folder)

        self.about_button = QPushButton("Open Folder Picker", self)
        self.about_button.clicked.connect(self.open_folder_picker)
        self.l.addWidget(self.about_button)

        buttonBox = QDialogButtonBox()
        buttonBox.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept_wrapper)
        buttonBox.rejected.connect(self.reject)
        self.l.addWidget(buttonBox)

        self.resize(800, 500)

    def create_cbc_file(self, input_file):
        if not (os.path.isdir(input_file)):
            error_dialog(
                self.gui,
                "Cannot create CBZ/CB7",
                'Given path "' + input_file + '" is not a folder',
                show=True,
            )
            return False

        os.chdir(input_file)

        files = os.listdir(input_file)
        files_list = list(filter(image_filter, files))

        if len(files_list) < 1:
            error_dialog(
                self.gui,
                "Cannot convert CBZ/CB7",
                "No image files in given archive",
                show=True,
            )
            return False

        cleaned_files = list(map(CBZ_Cleaner, files_list))

        if re.match(CBZ_regex, cleaned_files[0]):
            results = list(map(re.compile(CBZ_regex).search, cleaned_files))
            filename = Path(input_file).with_suffix(".cbc")

            if results[0]:
                title = results[0].group("Title")

            chapters = {}
            for index, reg_ex_result in enumerate(results):
                chapter_num = "unnumbered"
                if reg_ex_result and reg_ex_result.group("ChapterNum"):
                    chapter_num = reg_ex_result.group("ChapterNum")
                else:
                    re_result = re.search(
                        r"(c(h?(apter)?)).??(?P<chapter>\d+)", cleaned_files[index]
                    )
                    if re_result and re_result.group("chapter"):
                        chapter_num = re_result.group("chapter")

                chapter_name = ""
                if reg_ex_result and reg_ex_result.group("ChapterName"):
                    chapter_name = reg_ex_result.group("ChapterName")

                page_num = ""
                if reg_ex_result and reg_ex_result.group("Page"):
                    page_num = reg_ex_result.group("Page")
                else:
                    re_result = re.search(
                        r"(p|page|pg).??(?P<page>\d+)", cleaned_files[index]
                    )
                    if re_result and re_result.group("page"):
                        page_num = re_result.group("page")
                    else:
                        page_num = str(index).zfill(3)

                if reg_ex_result and reg_ex_result.group("Extension"):
                    Extension = reg_ex_result.group("Extension")
                else:
                    Extension = re.search(
                        r"(?P<extension>\.\w+$)", cleaned_files[index]
                    ).group("extension")

                if chapter_num and (chapter_num in chapters):
                    chapter = chapters[chapter_num]
                    chapter["pages"].append([files_list[index], page_num + Extension])
                elif chapter_num:
                    chapters[chapter_num] = {}
                    chapter = chapters[chapter_num]
                    chapter["name"] = "Chapter " + chapter_num
                    if chapter_name:
                        chapter["name"] = chapter_name
                    chapter["pages"] = []
                    chapter["pages"].append([files_list[index], page_num + Extension])
                else:
                    continue
        else:
            filename = os.path.basename(input_file) + ".cbc"
            chapters = {"unnumbered": {"name": "", "pages": []}}
            for index, file in enumerate(files_list):
                chapter_num = "unnumbered"

                re_result = re.search(r"(c(h?(apter)?)).??(?P<chapter>\d+)", file)
                if re_result and re_result.group("chapter"):
                    chapter_num = re_result.group("chapter")

                chapter_name = ""

                page_num = ""
                re_result = re.search(r"(p|page|pg).??(?P<page>\d+)", file)
                if re_result and re_result.group("page"):
                    page_num = re_result.group("page")
                else:
                    page_num = str(index).zfill(3)

                    Extension = re.search(r"(?P<extension>\.\w+$)", file).group(
                        "extension"
                    )

                if chapter_num and (chapter_num in chapters):
                    chapter = chapters[chapter_num]
                    chapter["pages"].append([files_list[index], page_num + Extension])
                elif chapter_num:
                    chapters[chapter_num] = {}
                    chapter = chapters[chapter_num]
                    chapter["name"] = "Chapter " + chapter_num
                    if chapter_name:
                        chapter["name"] = chapter_name
                    chapter["pages"] = []
                    chapter["pages"].append([files_list[index], page_num + Extension])
                else:
                    chapters["unnumbered"]["pages"].append([file, file])

        dialog = QDialog(self.gui)
        dialog.setWindowTitle('Configure Chapters for "' + filename + '"')
        l = QVBoxLayout()
        dialog.setLayout(l)
        text = QTextEdit()
        text.setAcceptRichText(False)
        text.setTabStopDistance(40)
        text.append(configuration_explanation)
        l.addWidget(text)
        buttonBox = QDialogButtonBox()
        buttonBox.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.rejected.connect(dialog.reject)
        l.addWidget(buttonBox)

        if ("unnumbered" in chapters) and (len(chapters) < 2):
            for page in chapters["unnumbered"]["pages"]:
                text.append("\t" + page[0] + "\t=>\t" + page[1])
        else:
            for chapter_num in chapters:
                text.append(
                    chapter_num
                    + ".cbz: Chapter "
                    + chapter_num.lstrip("0")
                    + " : "
                    + chapters[chapter_num]["name"]
                )
                for page in chapters[chapter_num]["pages"]:
                    text.append("\t" + page[0] + "\t=>\t" + page[1])

        cursor = text.textCursor()
        cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor, 1)
        text.setTextCursor(cursor)
        dialog.resize(1000, 500)

        retval = dialog.exec_()
        if retval != QDialog.Accepted:
            return False

        chapter_config = text.toPlainText()

        cbc_files = []

        source_folder = os.getcwd()
        new_folder = os.getcwd()

        cbc_obj = None
        while os.path.isdir(new_folder):
            try:
                if os.path.isfile(os.path.join(new_folder, filename)):
                    os.remove(os.path.join(new_folder, filename))
                cbc_obj = ZipFile(os.path.join(new_folder, filename), "w")
                break
            except FileNotFoundError:
                os.chdir(os.path.dirname(new_folder))
                new_folder = os.getcwd()

        if not (cbc_obj):
            error_dialog(
                self.gui,
                "Cannot create CBZ/CB7",
                "No image files in given archive",
                show=True,
            )
            return False

        if os.path.isfile(os.path.join(new_folder, "comics.txt")):
            os.remove(os.path.join(new_folder, "comics.txt"))
        comics = open(os.path.join(new_folder, "comics.txt"), "w")

        zipObj = None
        for line in chapter_config.split("\n"):
            if line.startswith("\t"):
                split = line.split("\t")
                if zipObj:
                    zipObj.write(
                        os.path.join(source_folder, split[1].strip()), split[3].strip()
                    )
                else:
                    cbc_obj.write(
                        os.path.join(source_folder, split[1].strip()), split[3].strip()
                    )
            elif line.startswith("#"):
                continue
            elif len(line) == 0:
                continue
            else:
                comics.write(line + "\n")
                split = line.split(":")
                if zipObj:
                    zipObj.close()
                zipObj = ZipFile(os.path.join(new_folder, split[0].strip()), "w")
                cbc_files.append(os.path.join(new_folder, split[0].strip()))
        if zipObj:
            zipObj.close()

        comics.close()

        cbc_obj.write(os.path.join(new_folder, "comics.txt"), "comics.txt")
        for file in cbc_files:
            cbc_obj.write(file, os.path.basename(file))

        cbc_obj.close()

        return_path = os.path.abspath(filename)

        if len(cbc_files) < 1:
            p = Path(return_path)
            updated = p.with_suffix(".cbz")
            if os.path.isfile(updated):
                os.remove(updated)
            p.rename(updated)
            return_path = os.path.abspath(updated)

        if os.path.isfile(os.path.join(new_folder, "comics.txt")):
            os.remove(os.path.join(new_folder, "comics.txt"))
        for file in cbc_files:
            if os.path.isfile(file):
                os.remove(file)

        return return_path

    def accept_wrapper(self):
        self.accept()
        text = self.selected_folder.toPlainText()
        zipped_files = []
        failed = []
        for line in text.split("\n"):
            stripped = line.removeprefix("file:///").removeprefix("/")
            if stripped:
                zipped_file = self.create_cbc_file(stripped)
                if zipped_file:
                    zipped_files.append(zipped_file)
                else:
                    failed.append(stripped)

        def complete(adder):
            added_ids = adder.added_book_ids
            if os.path.isfile(zipped_file):
                os.remove(zipped_file)
            db = self.gui.current_db.new_api
            success_msg = (
                "Successfully added "
                + str(len(adder.added_book_ids))
                + " books to the Calibre library:"
            )
            for book_id in added_ids:
                success_msg += "\n\t" + db.field_for("title", book_id)

            if len(failed) > 0:
                success_msg += (
                    "\n\nFailed to add"
                    + str(len(adder.added_book_ids))
                    + " books to the Calibre library:"
                )
                for failure in failed:
                    success_msg += "\n\t" + failure

            info_dialog(
                self,
                "Added Books",
                success_msg,
                show=True,
            )

        Adder(
            zipped_files,
            db=self.gui.current_db,
            parent=self.gui,
            callback=complete,
            pool=self.gui.spare_pool(),
        )

    def dragEnterEvent(self, e):
        mimeData = e.mimeData()
        if mimeData.hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        mimeData = e.mimeData()
        if mimeData.hasUrls():
            # e.acceptProposedAction()
            urlList = mimeData.urls()
            url = urlList[0].toString()
            path = urlparse(url).path.strip("file:///").strip("/")
            self.selected_folder.append(path)

    def open_folder_picker(self):
        filedialog = QFileDialog()
        dir = filedialog.getExistingDirectory(
            self,
            "Open Directory",
            "/home",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )
        self.selected_folder.append(dir)
