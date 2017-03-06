# -*- coding: utf-8 -*-

# Copyright © 2017 Kiri Choi
# Based on Spyder by Spyder Project Contributors and
# AutoPEP8 plugin by Joseph Martinot-Lagarde
# Licensed under the terms of the MIT License

"""openSBML plugin"""

from __future__ import print_function, division

import os
import re
from spyder.config.base import get_translation
from spyder.config.main import CONF
from spyder.plugins import SpyderPluginMixin
from spyder.py3compat import getcwd
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QApplication, QMessageBox
from qtpy.compat import getopenfilenames
from spyder.utils import encoding, sourcecode
from spyder.utils.qthelpers import create_action
from spyder.widgets.sourcecode.codeeditor import CodeEditor

try:
    import tellurium as te
except ImportError:
    raise Exception("Cannot find Tellurium. Please install Tellurium scripts first")

_ = get_translation("opensbml", dirname="spyder_opensbml")

class DummyDock(object):

    def close(self):
        pass

class openSBML(SpyderPluginMixin):
    "Open sbml files and translate into antimony string"
    
    CONF_SECTION = 'openSBML'
    CONFIGWIDGET_CLASS = None
    
    def __init__(self, main):
        super(openSBML, self).__init__(main)
        self.dockwidget = DummyDock()
        
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
        editorwindow = None #Used in editor.load
        processevents=True  #Used in editor.load
        editor = self.main.editor
        basedir = getcwd()
        if CONF.get('workingdir', 'editor/open/browse_scriptdir'):
            c_fname = editor.get_current_filename()
            if c_fname is not None and c_fname != editor.TEMPFILE_PATH:
                basedir = os.path.dirname(c_fname)
        editor.redirect_stdio.emit(False)
        parent_widget = editor.get_current_editorstack()
        selectedfilter = ''
        filters = 'SBML files (*.sbml *.xml);;All files (*.*)'
        filenames, _selfilter = getopenfilenames(parent_widget,
                                     _("Open SBML file"), basedir, filters,
                                     selectedfilter=selectedfilter)
        editor.redirect_stdio.emit(True)
        if filenames:
            filenames = [os.path.normpath(fname) for fname in filenames]
            if CONF.get('workingdir', 'editor/open/auto_set_to_basedir'):
                directory = os.path.dirname(filenames[0])
                editor.emit(Signal("open_dir(QString)"), directory)
        else:
            #The file dialog box was closed without selecting a file.
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
        
        for index, filename in enumerate(filenames):
            p = re.compile( '(.xml$|.sbml$)')
            pythonfile = p.sub( '_antimony.py', filename)
            if (pythonfile == filename):
                pythonfile = filename + "_antimony.py"
            current_editor = editor.set_current_filename(pythonfile, editorwindow)
            if current_editor is not None:
                # -- TODO:  Do not open an already opened file
                pass
            else:
                # -- Not an existing opened file:
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
                #if (current_editor is not None):
                #    editor.register_widget_shortcuts("Editor", current_editor)
                
                current_es.analyze_script()

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

