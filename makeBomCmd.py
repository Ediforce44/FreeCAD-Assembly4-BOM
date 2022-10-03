#!/usr/bin/env python3
# coding: utf-8
# 
# makeBomCmd.py 
#
# parses the Asm4 Model tree and creates a list of parts



import os
import json

import PySide
from PySide import QtGui, QtCore
from PySide.QtGui import *
from PySide.QtCore import *

import FreeCADGui as Gui
import FreeCAD as App

import Asm4_libs as Asm4
import infoPartCmd
import InfoKeys

import math

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
        self.BOM.clear()
        self.Verbose=str()
        self.PartsList = {}
        self.listParts(self.model)
        self.inSpreadsheet()
        self.cutOptFiles()
        self.UI.show()
        self.BOM.setPlainText(self.Verbose)

### def listParts use of Part info Edit
    def extendAttrDict(self, dictMain, dictExtension):
        for objectName in dictExtension:
            if objectName in dictMain:
                dictMain[objectName] += dictExtension[objectName]
            else:
                dictMain[objectName] = dictExtension[objectName]

    def calculateCountingAttr(self, object, quantity):
        try:
            price = self.PartsList[object.Label][self.infoKeysUser.get('PricePerPiece').get('userData')]
            self.PartsList[object.Label]['PriceTotal'] = float(price) * quantity
            pass
        except:
            print('Can not determine the price of part: ' + object.Label)

    def makeModelInfo(self, model, partList):
        _modelName = model.Document.Label
        self.PartsList[_modelName] = dict()
        for prop in self.infoKeysUser:
            self.PartsList[_modelName][self.infoKeysUser.get(prop).get('userData')] = ''

        self.PartsList[_modelName][self.infoKeysUser.get('ModelName').get('userData')] = _modelName
        self.PartsList[_modelName]['Quantity'] = 1
        #PricePerPiece
        price = 0
        for objectName in partList:
            try:
                price += float(self.PartsList[objectName][self.infoKeysUser.get('PricePerPiece').get('userData')]) * partList[objectName]
            except:
                price = 'Unkown'
                self.Verbose += 'Error in calculating price for model: ' + _modelName + '\n'
                break
        self.PartsList[_modelName][self.infoKeysUser.get('PricePerPiece').get('userData')] = price
        #Weight
        weight = 0
        for objectName in partList:
            try:
                weight += float(self.PartsList[objectName][self.infoKeysUser.get('Weight').get('userData')]) * partList[objectName]
            except:
                weight = 'Unkown'
                self.Verbose += 'Error in calculating weight for model: ' + _modelName + '\n'
                break
        self.PartsList[_modelName][self.infoKeysUser.get('Weight').get('userData')] = weight

    def listParts(self,object,level=0):
        file = open(ConfUserFilejson, 'r')
        self.infoKeysUser = json.load(file).copy()
        file.close()
        if object == None:
            return
        if self.PartsList == None:
            self.PartsList = {}
        # Required for Model attributes
        objectList = {}
        # research App::Part because the partInfo attribute is on
        if object.TypeId=='App::Link':
            self.extendAttrDict(objectList, self.listParts(object.LinkedObject,level+1))
        else:
            if object.TypeId=='App::Part':
                # write PartsList
                if object.Label == 'Model' or object.Type == 'Assembly':
                    if True:
                     # write model into PartList
                        for objname in object.getSubObjects():
                            subobj = object.Document.getObject( objname[0:-1] )
                            self.extendAttrDict(objectList, self.listParts(subobj,level+1))
                        if object.Document.Label in self.PartsList:
                            self.PartsList[object.Document.Label]['Quantity'] += 1
                        else:
                            self.makeModelInfo(object, objectList)
                else:
                    entryName = object.Document.Label + "::" + object.Label
                    # test if the part already exist on PartsList
                    if entryName in self.PartsList:
                        try:
                            self.PartsList[entryName]['Quantity'] += 1
                        except:
                            self.PartsList[entryName]['Quantity'] = 1
                    else:
                        # if not exist , create a dict() for this part
                        self.PartsList[entryName] = dict()
                        refreshed = False
                        for prop in self.infoKeysUser:
                            if self.infoKeysUser.get(prop).get('active'):
                                try:
                                    # try to get partInfo in part
                                    getattr(object,self.infoKeysUser.get(prop).get('userData'))
                                except AttributeError:
                                    # If partInfo is not complete all non-custom attributes will be reseted
                                    self.Verbose+='You haven\'t filled the attribute field of this Part:'+ entryName +'\n'
                                    crea(self,object)
                                    self.Verbose+='Attribute create for:'+ entryName +'\n'
                                    fill(object)
                                    self.Verbose+='Attribute auto filled for:'+ entryName +'\n'
                                    refreshed = True
                                    break
                        if not refreshed:
                            refresh(object)
                            self.Verbose+='AutoAttributes have been recalculated for: ' + entryName + '\n'
                        for prop in self.infoKeysUser:
                            self.PartsList[entryName][self.infoKeysUser.get(prop).get('userData')] = getattr(object,self.infoKeysUser.get(prop).get('userData'))
                        self.Verbose += '\n'
                        
                        self.PartsList[entryName]['Quantity'] = 1

                    self.calculateCountingAttr(object, int(self.PartsList[entryName]['Quantity']))

                    if entryName in objectList:
                        objectList[entryName] += 1
                    else:
                        objectList[entryName] = 1

                    # look for sub-objects
                    for objname in object.getSubObjects():
                        subobj = object.Document.getObject( objname[0:-1] )
                        self.extendAttrDict(objectList, self.listParts(subobj,level+1))

        return objectList
        self.Verbose+='Your Bill of Materials is Done\n'

### def Copy - Copy on Spreadsheet

    def applySimpleMask(self, dataDict, mask, constantDict={}):
        newData = {}
        for i, _ in enumerate(dataDict):
            nextEntry = {}
            if dataDict[i][self.infoKeysUser.get('PartName').get('userData')] == '':
                # Skip all parts with empty PartName (especially Models)
                continue
            notFound = True
            for dataKey in dataDict[i]:
                if dataKey in mask:
                    nextEntry[dataKey] = dataDict[i][dataKey]
                    notFound = False
            if notFound:
                nextEntry[dataKey] = ''
            for constantKey in constantDict:
                nextEntry[constantKey] = constantDict[constantKey]
            newData.append(nextEntry)
        return newData 
    
    def applyMask(self, dataDict, maskDict, constantDict={}):
        newData = []
        for i, _ in enumerate(dataDict):
            nextEntry = {}
            if dataDict[i][self.infoKeysUser.get('PartName').get('userData')] == '':
                # Skip all parts with empty PartName (especially Models)
                continue
            for newLabel in maskDict:
                notFound = True
                for dataKey in dataDict[i]:
                    if dataKey == maskDict[newLabel]:
                        nextEntry[newLabel] = dataDict[i][dataKey]
                        notFound = False
                if notFound:
                    nextEntry[newLabel] = ''
            for constantKey in constantDict:
                nextEntry[constantKey] = constantDict[constantKey]
            newData.append(nextEntry)
        return newData 

    def seperateByThickness(self, dataDict):
        seperatedParts = dict()
        for i, _ in enumerate(dataDict):
            partThickness = str(dataDict[i][self.infoKeysUser.get('Thickness').get('userData')]).replace(' ', '')
            if partThickness == '':
                continue
            try:
                partThickness = str(math.ceil(float(partThickness)))
            except:
                pass
            if partThickness in seperatedParts:
                seperatedParts[partThickness].append(dataDict[i])
            else:
                seperatedParts[partThickness] = [dataDict[i]]
        return seperatedParts

    def createCustListCSVFile(self, filePath, data, seperator=','):
        try:
            file = open(filePath, 'w')
            try:
                line = ''
                for key in data[0]:
                    line += str(key) + seperator
                line = line[:-len(seperator)]
                file.write(line)
                for i, _ in enumerate(data):
                    line = '\n'
                    for value in data[i].values():
                        line += str(value) + seperator
                    line = line[:-len(seperator)]
                    file.write(line)
            except Exception:
                App.Console.PrintError("Error write Cut-List file: " + filePath +"\n")
            finally:
                file.close()
        except Exception:
            App.Console.PrintError("Error Open file: "+ filePath +"\n")

    def cutOptFiles(self):
        document = App.ActiveDocument
        plist = self.PartsList
        if len(plist) == 0:
            return
        def wrow(drow: [str], row: int):
            for i, d in enumerate(drow):
                if row == 0:
                    spreadsheet.set(str(chr(ord('a') + i)).upper() + str(row + 1), infoPartCmd.decodeXml(str(d)))
                else:
                    spreadsheet.set(str(chr(ord('a') + i)).upper() + str(row + 1), str(d))
        
        # Get file path for the Cut-List csv files
        dirPath = App.ConfigGet("UserHomePath")
        try:
            dirPath = QFileDialog.getExistingDirectory(None, QString.fromLocal8Bit("Select a folder for the Cut-List files"), dirPath) # PyQt4
            #                                                                     "here the text displayed on windows" "here the filter (extension)"   
        except Exception:
            dirPath = PySide.QtGui.QFileDialog.getExistingDirectory(None, "Select a folder for the Cut-List files", dirPath)
        finally: 
            if dirPath == '':
                dirPath = App.ConfigGet("UserHomePath")

        # Prepare PartList for seperating
        data = list(plist.values())
        cutOptMask = {
            'Length' : self.infoKeysUser.get('DimX').get('userData'),
            'Width' : self.infoKeysUser.get('DimY').get('userData'),
            'Qty' : 'Quantity',
            'Label' : self.infoKeysUser.get('PartName').get('userData')}
        
        groupedParts = self.seperateByThickness(data)

        for thickness in groupedParts:
            cutlistName = 'CutList_' + str(thickness)
            filteredData = self.applyMask(groupedParts[thickness], cutOptMask, {'Enabled' : 1})
            #Spreadsheets
            if not hasattr(document, cutlistName):
                spreadsheet = document.addObject('Spreadsheet::Sheet', cutlistName)
            else:
                spreadsheet = getattr(document, cutlistName)
            spreadsheet.Label = cutlistName
            spreadsheet.clearAll()
            wrow(filteredData[0].keys(), 0)
            for i, _ in enumerate(filteredData):
                wrow(filteredData[i].values(), i+1)
            #CSV Files
            filePath = dirPath + '/' + cutlistName + '.csv'
            self.createCustListCSVFile(filePath, filteredData, ',')

        document.recompute()

        self.Verbose += 'Cust-List spreadsheet and CSV files has been successfully created\n'
        self.Verbose += '\n'

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
        self.Verbose+= '\n'


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
