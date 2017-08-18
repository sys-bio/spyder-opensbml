# -*- coding: utf-8 -*-

# Copyright © 2017 Kiri Choi
# Based on Spyder by Spyder Project Contributors and
# AutoPEP8 plugin by Joseph Martinot-Lagarde
# Licensed under the terms of the MIT License

"""openSBML plugin"""

from __future__ import print_function, division

import os
import re
from spyder.config.base import get_translation, PYTEST
from spyder.config.utils import (get_filter, get_edit_filters, 
                                 get_edit_filetypes)
from spyder.plugins import SpyderPluginMixin, SpyderDockWidget
from spyder.py3compat import getcwd, to_text_string
from qtpy.QtWidgets import (QApplication, QMessageBox, QFileDialog, QAction)
from qtpy.compat import getopenfilenames, from_qvariant
from spyder.utils import encoding, sourcecode
from spyder.utils.qthelpers import create_action
from spyder.widgets.sourcecode.codeeditor import CodeEditor

try:
    import tellurium as te
except ImportError:
    raise Exception("Cannot find Tellurium. Please install Tellurium scripts first")

_ = get_translation("opensbml", dirname="spyder_opensbml")

class openSBML(SpyderPluginMixin):
    "Open sbml files and translate into antimony string"
    
    CONF_SECTION = 'openSBML'
    CONFIGWIDGET_CLASS = None
    
    def __init__(self, main):
        super(openSBML, self).__init__(main)
        self.dockwidget = SpyderDockWidget(self.get_plugin_title(), main)
        self.dockwidget.hide()
        
    # --- SpyderPluginWidget API ----------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _("Open SBML")
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        opensbml_act = create_action(self.main, _("Open SBML file"),
                                   triggered=self.run_opensbml) 
        self.main.file_menu_actions.insert(5, opensbml_act)

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        pass

    # --- Public API ----------------------------------------------------------
    def run_opensbml(self, filenames=None, goto=None, word='', editorwindow=None,
             processevents=True):
        """Prompt the user to load a SBML file, translate to antimony, and 
        display in a new window"""
        editor = self.main.editor
        editor0 = editor.get_current_editor()
        if editor0 is not None:
            position0 = editor0.get_position('cursor')
            filename0 = editor.get_current_filename()
        else:
            position0, filename0 = None, None
        if not filenames:
            # Recent files action
            action = editor.sender()
            if isinstance(action, QAction):
                filenames = from_qvariant(action.data(), to_text_string)
        if not filenames:
            basedir = getcwd()
            if editor.edit_filetypes is None:
                editor.edit_filetypes = get_edit_filetypes()
            if editor.edit_filters is None:
                editor.edit_filters = get_edit_filters()

            c_fname = editor.get_current_filename()
            if c_fname is not None and c_fname != editor.TEMPFILE_PATH:
                basedir = os.path.dirname(c_fname)
            editor.redirect_stdio.emit(False)
            parent_widget = editor.get_current_editorstack()
            if filename0 is not None:
                selectedfilter = get_filter(editor.edit_filetypes,
                                            os.path.splitext(filename0)[1])
            else:
                selectedfilter = ''
            if not PYTEST:
                customfilters = 'SBML files (*.sbml *.xml);;All files (*.*)'
                filenames, _sf = getopenfilenames(
                                    parent_widget,
                                    _("Open SBML file"), basedir,
                                    customfilters,
                                    selectedfilter=selectedfilter,
                                    options=QFileDialog.HideNameFilterDetails)
            else:
                # Use a Qt (i.e. scriptable) dialog for pytest
                dialog = QFileDialog(parent_widget, _("Open SBML file"),
                                     options=QFileDialog.DontUseNativeDialog)
                if dialog.exec_():
                    filenames = dialog.selectedFiles()
            editor.redirect_stdio.emit(True)
            if filenames:
                filenames = [os.path.normpath(fname) for fname in filenames]
            else:
                return
            
        focus_widget = QApplication.focusWidget()
        if editor.dockwidget and not editor.ismaximized and\
           (not editor.dockwidget.isAncestorOf(focus_widget)\
            and not isinstance(focus_widget, CodeEditor)):
            editor.dockwidget.setVisible(True)
            editor.dockwidget.setFocus()
            editor.dockwidget.raise_()

        def _convert(fname):
            fname = os.path.abspath(encoding.to_unicode_from_fs(fname))
            if os.name == 'nt' and len(fname) >= 2 and fname[1] == ':':
                fname = fname[0].upper()+fname[1:]
            return fname

        if hasattr(filenames, 'replaceInStrings'):
            # This is a QStringList instance (PyQt API #1), converting to list:
            filenames = list(filenames)
        if not isinstance(filenames, list):
            filenames = [_convert(filenames)]
        else:
            filenames = [_convert(fname) for fname in list(filenames)]
            
        if isinstance(goto, int):
            goto = [goto]
        elif goto is not None and len(goto) != len(filenames):
            goto = None
            
        for index, filename in enumerate(filenames):
            p = re.compile( '(.xml$|.sbml$)')
            pythonfile = p.sub( '_antimony.py', filename)
            if (pythonfile == filename):
                pythonfile = filename + "_antimony.py"            
            # -- Do not open an already opened file
            current_editor = editor.set_current_filename(pythonfile, editorwindow)
            if current_editor is None:
                # -- Not a valid filename:
                if not os.path.isfile(filename):
                    continue
                # --
                current_es = editor.get_current_editorstack(editorwindow)

                # Creating the editor widget in the first editorstack (the one
                # that can't be destroyed), then cloning this editor widget in
                # all other editorstacks:
                finfo, newname = self.load_and_translate(filename, pythonfile, editor)
                finfo.path = editor.main.get_spyder_pythonpath()
                editor._clone_file_everywhere(finfo)
                current_editor = current_es.set_current_filename(newname)

                current_es.analyze_script()
            if goto is not None: # 'word' is assumed to be None as well
                current_editor.go_to_line(goto[index], word=word)
                position = current_editor.get_position('cursor')
                editor.cursor_moved(filename0, position0, filename, position)
            if (current_editor is not None):
                current_editor.clearFocus()
                current_editor.setFocus()
                current_editor.window().raise_()
            if processevents:
                QApplication.processEvents()
        
    def load_and_translate(self, sbmlfile, pythonfile, editor, set_current=True):
        """
        Read filename as combine archive, unzip, translate, reconstitute in 
        Python, and create an editor instance and return it
        *Warning* This is loading file, creating editor but not executing
        the source code analysis -- the analysis must be done by the editor
        plugin (in case multiple editorstack instances are handled)
        """
        widgeteditor = editor.editorstacks[0]
        sbmlfile = str(sbmlfile)
        widgeteditor.starting_long_process.emit(_("Loading %s...") % sbmlfile)
        text, enc = encoding.read(sbmlfile)
        sbmlstr = te.readFromFile(sbmlfile)
        text = "import tellurium as te\n\nr = te.loada('''\n" + str(te.sbmlToAntimony(sbmlstr)) + "''')"
        finfo = widgeteditor.create_new_editor(pythonfile, enc, text, set_current, new=True)
        index = widgeteditor.data.index(finfo)
        widgeteditor._refresh_outlineexplorer(index, update=True)
        widgeteditor.ending_long_process.emit("")
        if widgeteditor.isVisible() and widgeteditor.checkeolchars_enabled \
         and sourcecode.has_mixed_eol_chars(text):
            name = os.path.basename(pythonfile)
            QMessageBox.warning(self, widgeteditor.title,
                                _("<b>%s</b> contains mixed end-of-line "
                                  "characters.<br>Spyder will fix this "
                                  "automatically.") % name,
                                QMessageBox.Ok)
            widgeteditor.set_os_eol_chars(index)
        widgeteditor.is_analysis_done = False
        finfo.editor.set_cursor_position('eof')
        finfo.editor.insert_text(os.linesep)
        return finfo, sbmlfile

