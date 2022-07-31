#!/usr/bin/env python3
# coding: utf-8
# 
# makeBomCmd.py 
#
# parses the Asm4 Model tree and creates a list of parts



import os
import json

from PySide import QtGui, QtCore
import FreeCADGui as Gui
import FreeCAD as App

import Asm4_libs as Asm4
import infoPartCmd
import InfoKeys

# protection against update of user configuration

### to have the dir of external configuration file
ConfUserDir = os.path.join(App.getUserAppDataDir(),'Templates')
ConfUserFilename = "Asm4_infoPartConf.json"
ConfUserFilejson = os.path.join(ConfUserDir, ConfUserFilename)


### try to open existing external configuration file of user
try :
    file = open(ConfUserFilejson, 'r')
    file.close()
### else make the default external configuration file
except :
    partInfoDef = dict()
    for prop in InfoKeys.partInfo:
        partInfoDef.setdefault(prop,{'userData':prop + 'User','active':True})
    os.mkdir(ConfUserDir)
    file = open(ConfUserFilejson, 'x')
    json.dump(partInfoDef,file)
    file.close()
    
### now user configuration is :
file = open(ConfUserFilejson, 'r')
infoKeysUser = json.load(file).copy()
file.close()
    
crea = infoPartCmd.infoPartUI.makePartInfo
fill = infoPartCmd.infoPartUI.infoDefault
refresh = infoPartCmd.infoPartUI.refreshSizeInfo
reset = infoPartCmd.infoPartUI.resetCountingAttr


"""
    +-----------------------------------------------+
    |               Helper functions                |
    +-----------------------------------------------+
"""



"""
    +-----------------------------------------------+
    |               prints a parts list             |
    +-----------------------------------------------+
"""

class makeBOM:
    def __init__(self):
        super(makeBOM,self).__init__()
        file = open(ConfUserFilejson, 'r')
        self.infoKeysUser = json.load(file).copy()
        file.close()

    def GetResources(self):
        tooltip  = "Bill of Materials"
        tooltip += "Create the Bill of Materials of an Assembly"
        tooltip += "With the Info and Config of Edit Part Information"
        iconFile = os.path.join( Asm4.iconPath, 'Asm4_PartsList.svg' )
        return {"MenuText": "Create Part List", "ToolTip": tooltip, "Pixmap": iconFile }


    def IsActive(self):
        # return self.checkModel()
        if Asm4.getAssembly() is None:
            return False
        else: 
            return True

    def Activated(self):
        self.UI = QtGui.QDialog()
        # get the current active document to avoid errors if user changes tab
        self.modelDoc = App.ActiveDocument
        # for the compatibility with the old Model
        try :
            self.model = self.modelDoc.Assembly
        except:
            try:
                self.model = self.modelDoc.Model
                print("legacy Assembly4 Model")
            except:
                print("Hum, this might not work")
        self.drawUI()
        self.UI.show()
        self.BOM.clear()
        self.Verbose=str()
        self.PartsList = {}
        ################################### Edited by Ediforce44 #########################################
        # Overwrites user input for the attributes size etc. of an Object
        # - So it is possible to use variables for lengths and the BOM hand in hand
        self.resetCountingInfos(self.model)
        self.calculatePartInfo(self.model)
        ##################################################################################################
        self.listParts(self.model)
        self.inSpreadsheet()
        self.BOM.setPlainText(self.Verbose)

### def listParts use of Part info Edit

    def resetCountingInfos(self, object, level=0):
        # Reset Quantity attribute
        if object.TypeId=='App::Link':
            self.resetCountingInfos(object.LinkedObject,level+1)
        else:
            if object.TypeId=='App::Part':
                if level > 0:
                    if hasattr(object,'Quantity'):
                        reset(object)
                # look for sub-objects
                for objname in object.getSubObjects():
                    subobj = object.Document.getObject( objname[0:-1] )
                    self.resetCountingInfos(subobj,level+1)
        return

    def calculatePartInfo(self,object,level=0):
        file = open(ConfUserFilejson, 'r')
        self.infoKeysUser = json.load(file).copy()
        file.close()
        if object == None:
            return
        # research App::Part because the partInfo attribute is on
        if object.TypeId=='App::Link':
            self.calculatePartInfo(object.LinkedObject,level+1)
        else:
            if object.TypeId=='App::Part':
                if (object.Label != 'Model') and (object.Type != 'Assembly') and (level > 0):
                    try:
                        # try to get partInfo in part
                        for prop in self.infoKeysUser:
                            getattr(object,self.infoKeysUser.get(prop).get('userData'))
                        # Only if partInfo is complete the autoAttributes will get refreshed
                        refresh(object)
                        self.Verbose+='AutoAttributes have been recalculated for: ' + object.Label + '\n'
                    except AttributeError:
                        # If partInfo is not complete all non-custom attributes will be reseted
                        self.Verbose+='You haven\'t filled the attribute field of this Part:'+ object.Label +'\n'
                        crea(self,object)
                        self.Verbose+='Attribute create for:'+ object.Label +'\n'
                        fill(object)
                        self.Verbose+='Attribute auto filled for:'+ object.Label+'\n'
                    self.Verbose += '\n'
                # look for sub-objects
                for objname in object.getSubObjects():
                    subobj = object.Document.getObject( objname[0:-1] )
                    self.calculatePartInfo(subobj,level+1)
        return

    def makeModelInfo(self, model, partList):
        #TODO
        pass

    def listParts(self,object,level=0):
        file = open(ConfUserFilejson, 'r')
        self.infoKeysUser = json.load(file).copy()
        file.close()
        if object == None:
            return
        if self.PartsList == None:
            self.PartsList = {}
        # Required for Model attributes
        objectList = []
        # research App::Part because the partInfo attribute is on
        if object.TypeId=='App::Link':
            objectList.extend(self.listParts(object.LinkedObject,level+1))
        else:
            if object.TypeId=='App::Part':
                # write PartsList
                if object.Label == 'Model' or object.Type == 'Assembly':
                    # look for sub-objects
                    for objname in object.getSubObjects():
                        subobj = object.Document.getObject( objname[0:-1] )
                        objectList.extend(self.listParts(subobj,level+1))
                    if object.Document.Label in self.PartsList:
                        self.PartsList[object.Label]['Quantity'] += 1
                    else:
                        self.PartsList[object.Document.Label] = self.makeModelInfo(object, objectList)
                else:
                    # test if the part already exist on PartsList
                    if object.Label in self.PartsList:
                        self.PartsList[object.Label]['Quantity'] += 1
                        try:
                            price = self.PartsList[object.Label][self.infoKeysUser.get('PricePerPiece').get('userData')]
                            self.PartsList[object.Label]['PriceTotal'] = float(price) * int(self.PartsList[object.Label]['Quantity'])
                        except:
                            pass
                    else:
                        # if not exist , create a dict() for this part
                        self.PartsList[object.Label] = dict()
                        for prop in self.infoKeysUser:
                            try:
                                if self.infoKeysUser.get(prop).get('active'):
                                    # try to get partInfo in part
                                    self.PartsList[object.Label][self.infoKeysUser.get(prop).get('userData')] = getattr(object,self.infoKeysUser.get(prop).get('userData'))
                            except AttributeError:
                                self.Verbose+='FATAL ERROR: PartInfo is not complete for Part:'+ object.Label +'\n'
                        self.PartsList[object.Label]['Quantity'] = 1
                        try:
                            price = self.PartsList[object.Label][self.infoKeysUser.get('PricePerPiece').get('userData')]
                            self.PartsList[object.Label]['PriceTotal'] = price
                        except:
                            pass
                        objectList.append(object.Label)

        return objectList
        self.Verbose+='Your Bill of Materials is Done\n'

### def Copy - Copy on Spreadsheet

    def inSpreadsheet(self):
        # Copies Parts List to Spreadsheet
        document = App.ActiveDocument
        # init plist with dict() PartsList
        plist = self.PartsList
        if len(plist) == 0:
            return
        # BOM on Spreadsheet
        if not hasattr(document, 'BOM'):
            spreadsheet = document.addObject('Spreadsheet::Sheet','BOM')
        else:
            spreadsheet = document.BOM

        spreadsheet.Label = "BOM"
        # clean the BOM
        spreadsheet.clearAll()
        # to write line in spreadsheet
        def wrow(drow: [str], row: int):
            for i, d in enumerate(drow):
                if row==0:
                    spreadsheet.set(str(chr(ord('a') + i)).upper()+str(row+1),infoPartCmd.decodeXml(str(d)))
                else :
                    spreadsheet.set(str(chr(ord('a') + i)).upper()+str(row+1),str(d))
        # to make list of values of dict() plist
        data = list(plist.values())
        # to write first line with keys
        wrow(data[0].keys(),0)
        # to write line by line BoM in Spreadsheet
        for i,_ in enumerate(data):
            wrow(data[i].values(),i+1)
        
        document.recompute()

        self.Verbose+='Your Bill of Materials is Write on BOM Spreadsheet\n'


    def onOK(self):
        document = App.ActiveDocument
        Gui.Selection.addSelection(document.Name,'BOM')
        self.UI.close()


    """
    +-----------------------------------------------+
    |     defines the UI, only static elements      |
    +-----------------------------------------------+
    """
    def drawUI(self):
        # Our main window will be a QDialog
        self.UI.setWindowTitle('Parts List / BOM')
        self.UI.setWindowIcon( QtGui.QIcon( os.path.join( Asm4.iconPath , 'FreeCad.svg' ) ) )
        self.UI.setWindowFlags( QtCore.Qt.WindowStaysOnTopHint )
        self.UI.setModal(False)
        # set main window widgets layout
        self.mainLayout = QtGui.QVBoxLayout(self.UI)

        # Help and Log :
        self.LabelBOML1 = QtGui.QLabel()
        self.LabelBOML1.setText('BoM:\n\nThis tool makes a BoM with the Info and Config of Edit Part Information. \n\nIf you have auto-infoField in your Config you can use BoM directly.\nBoM complete automatically your auto-infoField.\n\n')
        self.LabelBOML2 = QtGui.QLabel()
        self.LabelBOML2.setText("<a href='https://github.com/Zolko-123/FreeCAD_Assembly4/tree/master/Examples/ConfigBOM/README.md'>-=Tuto=-</a>")
        self.LabelBOML2.setOpenExternalLinks(True)
        self.LabelBOML3 = QtGui.QLabel()
        self.LabelBOML3.setText('\n\nLog :')

        self.mainLayout.addWidget(self.LabelBOML1)
        self.mainLayout.addWidget(self.LabelBOML2)
        self.mainLayout.addWidget(self.LabelBOML3)
        
        # The Log (Verbose) is a plain text field
        self.BOM = QtGui.QPlainTextEdit()
        self.BOM.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        self.mainLayout.addWidget(self.BOM)

        # the button row definition
        self.buttonLayout = QtGui.QHBoxLayout()
        
        # OK button
        self.OkButton = QtGui.QPushButton('OK')
        self.OkButton.setDefault(True)
        self.buttonLayout.addWidget(self.OkButton)
        self.mainLayout.addLayout(self.buttonLayout)

        # finally, apply the layout to the main window
        self.UI.setLayout(self.mainLayout)

        # Actions
        self.OkButton.clicked.connect(self.onOK)

# add the command to the workbench
Gui.addCommand( 'Asm4_makeBOM', makeBOM() )
