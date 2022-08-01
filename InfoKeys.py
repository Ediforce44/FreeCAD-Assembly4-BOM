#!/usr/bin/env python3
# coding: utf-8
#
# LGPL
#
# libraries for FreeCAD's Assembly 4 workbench

import os, json, math

import FreeCAD as App
import infoPartCmd


# Autofilling info ref
partInfo =[     'ModelName',           \
                'PartName',            \
                'SketchLength',        \
                'Thickness',            \
                'DimX',                 \
                'DimY',                 \
                'DimZ',                 \
                'Volume',               \
                'Density',              \
                'Weight',               \
                'PricePerPiece'
]

infoToolTip = { 'ModelName':'Label/Name of Document',          \
                'PartName':'Label/Name of Part',               \
                'SketchLength':'Length/\"Perimeter+\" of Sketch/Shape',  \
                'Thickness':'Length of the Pad of the Shape',   \
                'DimX':'Length in X-Dimension',                 \
                'DimY':'Length in Y-Dimension',                 \
                'DimZ':'Length in Z-Dimension',                 \
                'Volume':'Volume of the Part',                  \
                'Density':'Density of the Material in g/cm^2',  \
                'Weight':'Weight of one Part (DimX, DimY, DimZ)',   \
                'PricePerPiece':'Price of one Part'
}

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
    for prop in partInfo:
        partInfoDef.setdefault(prop,{'userData':prop,'active':True})
    try:
        os.mkdir(ConfUserDir)
    except:
        pass
    file = open(ConfUserFilejson, 'x')
    json.dump(partInfoDef,file)
    file.close()
    

### now user configuration is :
file = open(ConfUserFilejson, 'r')
infoKeysUser = json.load(file).copy()
file.close()

def infoDefault(self):
    ### auto filling module
    ### load infoKeysUser    
    file = open(ConfUserFilejson, 'r')
    infoKeysUser = json.load(file).copy()
    file.close()
    ### part variable creation
    try :
        self.TypeId
        PART=self
    except AttributeError:
        PART=self.part
    ### you have PART    
    DOC=PART.Document
    ### you have DOC
    
    ### start all autoinfofield
    try :
        ModelName(self,PART,DOC)
    except NameError :
        print('there is no DOC for this part : ',PART.FullName )
    try :
        PartName(self,PART)
    except NameError :
        print('there is no Part' )
    try :
        setAttributeToValue(self, PART, 'Density', 0.66)
    except:
        print('Error for attribute Density : ',PART.FullName )

    calculateSizeInfo(self)

    try :
        setAttributeToValue(self, PART,'PricePerPiece', 0)
    except:
        print('Error for attribute PricePerPiece : ',PART.FullName )

def calculateSizeInfo(self):
    PART = self
    ### research
    for i in range(len(PART.Group)):
        if PART.Group[i].TypeId == 'PartDesign::Body' :
            BODY=PART.Group[i]
            ### you have BODY
            for i in range(len(BODY.Group)):
                if BODY.Group[i].TypeId == 'PartDesign::Pad' :
                    PAD=BODY.Group[i]
                    ### you have PAD
                    try :
                        SKETCH=PAD.Profile[0]
                        ### you have SKETCH
                    except NameError :
                        print('there is no Sketch on a Pad of : ',PART.FullName )
    try :    
        Thickness(self,PART,PAD)
    except NameError :
        print('there is no PAD for this Part : ',PART.FullName )
    try :
        SketchLength(self,PART,SKETCH)
    except NameError :
        print('ShapeLength : there is no Sketch for this Part : ',PART.FullName )
    try :
        Dimensions(self,PART,BODY)
    except:
        print('there is no Shape on Volume : ',PART.FullName )
    try :
        Weight(self, PART)
    except:
        print('Error for attribute Weight : ',PART.FullName )

def addAttrValueToModel(model, attrName, valueToAdd):
    try:
        newValue = float(valueToAdd)
        if hasattr(model, attrName):
            newValue += float(getattr(model, attrName))
        setAttributeToValue(model, model, attrName, newValue)
    except:
        print('Error in attribute calculation for a model')

def setAttributeToValue(self, PART, attrName, value):
    ###you can use DOC - PART - BODY - PAD - SKETCH
    auto_info_field = infoKeysUser.get(str(attrName)).get('userData')
    try:
        ### if the command comes from makeBom write autoinfo directly on Part
        self.TypeId
        setattr(PART,auto_info_field,str(value))
    except AttributeError:
        ### if the command comes from infoPartUI write autoinfo on autofilling field on UI
        try :
        ### if field is active
            for i in range(len(self.infoTable)):
                if self.infoTable[i][0]== auto_info_field :
                    self.infos[i].setText(str(auto_info_fill))
        except AttributeError:
        ### if field is not active
            pass

def Weight(self,PART):
    ###you can use DOC - PART - BODY - PAD - SKETCH
    auto_info_field = infoKeysUser.get('Weight').get('userData')
    auto_info_fill = round(int(getattr(PART,'Volume')) * float(getattr(PART,'Density')))
    try:
        ### if the command comes from makeBom write autoinfo directly on Part
        self.TypeId
        setattr(PART,auto_info_field,str(auto_info_fill))
    except AttributeError:
        ### if the command comes from infoPartUI write autoinfo on autofilling field on UI
        try :
        ### if field is active
            for i in range(len(self.infoTable)):
                if self.infoTable[i][0]== auto_info_field :
                    self.infos[i].setText(str(auto_info_fill))
        except AttributeError:
        ### if field is not active
            pass

def Dimensions(self,PART, BODY):
###you can use DOC - PART - BODY - PAD - SKETCH
    auto_info_field_x = infoKeysUser.get('DimX').get('userData')
    auto_info_field_y = infoKeysUser.get('DimY').get('userData')
    auto_info_field_z = infoKeysUser.get('DimZ').get('userData')
    auto_info_field_volume = infoKeysUser.get('Volume').get('userData')
    bbc = BODY.Shape.BoundBox
    _realX = round(bbc.XLength, 2)
    _realY = round(bbc.YLength, 2)
    _realZ = round(bbc.ZLength, 2)
    _thickness = float(getattr(PART, infoKeysUser.get('Thickness').get('userData')))
    #Swap dimensions to be more uniform (for cutlist)
    _x = math.ceil(_realX)
    _y = math.ceil(_realY)
    _z = math.ceil(_realZ)
    if _realX == _thickness:
        _z = _x
        _x = math.ceil(_realZ)
    elif _realY == _thickness:
        _z = _y
        _y = math.ceil(_realZ)
    elif _realZ == _thickness:
        pass
    auto_info_fill_x = str(_x)
    auto_info_fill_y = str(_y)
    auto_info_fill_z = str(_z)
    auto_info_fill_volume = str(math.ceil(_x * _y * _z / 1000))
    try:
        ### if the command comes from makeBom write autoinfo directly on Part
        self.TypeId
        setattr(PART,auto_info_field_x,str(auto_info_fill_x))
        setattr(PART,auto_info_field_y,str(auto_info_fill_y))
        setattr(PART,auto_info_field_z,str(auto_info_fill_z))
        setattr(PART,auto_info_field_volume,str(auto_info_fill_volume))
    except AttributeError:
        ### if the command comes from infoPartUI write autoinfo on autofilling field on UI
        try :
        ### if field is active
            for i in range(len(self.infoTable)):
                if self.infoTable[i][0]== auto_info_field_x :
                    self.infos[i].setText(str(auto_info_fill_x))
                elif self.infoTable[i][0]== auto_info_field_y :
                    self.infos[i].setText(str(auto_info_fill_y))
                elif self.infoTable[i][0]== auto_info_field_z :
                    self.infos[i].setText(str(auto_info_fill_z))
                elif self.infoTable[i][0]== auto_info_field_volume :
                    self.infos[i].setText(str(auto_info_fill_volume))
        except AttributeError:
        ### if field is not active
            pass


"""
how make a new autoinfofield :

ref newautoinfofield name in partInfo[]

make a description in infoToolTip = {}

put newautoinfofield name in infoDefault() at the end with the right arg (PAD,SKETCH...)

write new def like that :

def newautoinfofieldname(self,PART(option : DOC , BODY , PAD , SKETCH):
###you can use DOC - PART - BODY - PAD - SKETCH
    auto_info_field = infoKeysUser.get('newautoinfofieldname').get('userData')
    auto_info_fill = newautoinfofield information
    try:
        ### if the command comes from makeBom write autoinfo directly on Part
        self.TypeId
        setattr(PART,auto_info_field,str(auto_info_fill))
    except AttributeError:
        ### if the command comes from infoPartUI write autoinfo on autofilling field on UI
        try :
        ### if field is active
            for i in range(len(self.infoTable)):
                if self.infoTable[i][0]== auto_info_field :
                    self.infos[i].setText(str(auto_info_fill))
        except AttributeError:
        ### if field is not active
            pass

"""

def SketchLength(self,PART,SKETCH):
###you can use DOC - PART - BODY - PAD - SKETCH
    auto_info_field = infoKeysUser.get('SketchLength').get('userData')
    try :
        auto_info_fill = round(SKETCH.Shape.Length,1)
    except AttributeError:
        return
    try:
        ### if the command comes from makeBom write autoinfo directly on Part
        self.TypeId
        setattr(PART,auto_info_field,str(auto_info_fill))
    except AttributeError:
        ### if the command comes from infoPartUI write autoinfo on autofilling field on UI
        try :
        ### if field is active
            for i in range(len(self.infoTable)):
                if self.infoTable[i][0]== auto_info_field :
                    self.infos[i].setText(str(auto_info_fill))
        except AttributeError:
        ### if field is not active
            pass
            

def Thickness(self,PART,PAD):
###you can use DOC - PART - BODY - PAD - SKETCH
    auto_info_field = infoKeysUser.get('Thickness').get('userData')
    try :
        auto_info_fill = str(PAD.Length).replace('mm','')
    except AttributeError:
        return
    try:
        ### if the command comes from makeBom write autoinfo directly on Part
        self.TypeId
        setattr(PART,auto_info_field,str(auto_info_fill))
    except AttributeError:
        ### if the command comes from infoPartUI write autoinfo on autofilling field on UI
        try :
        ### if field is active
            for i in range(len(self.infoTable)):
                if self.infoTable[i][0]== auto_info_field :
                    self.infos[i].setText(str(auto_info_fill))
        except AttributeError:
        ### if field is not active
            pass


        
def ModelName(self,PART,DOC):
    docLabel = infoKeysUser.get('ModelName').get('userData')
    try:
        ### if the command comes from makeBom write autoinfo directly on Part
        self.TypeId
        setattr(PART,docLabel,DOC.Label)
    except AttributeError:
        ### if the command comes from infoPartUI write autoinfo on autofilling field on UI
        try :
        ### if field is active
            for i in range(len(self.infoTable)):
                if self.infoTable[i][0]==docLabel:
                    self.infos[i].setText(DOC.Label)
        except AttributeError:
        ### if field is not active
            pass
        
def PartName(self,PART):
    partLabel = infoKeysUser.get('PartName').get('userData')
    try:
        ### if the command comes from makeBom write autoinfo directly on Part
        self.TypeId
        setattr(PART,partLabel,PART.Label)
    except AttributeError:
        ### if the command comes from infoPartUI write autoinfo on autofilling field on UI
        try :
        ### if field is active
            for i in range(len(self.infoTable)):
                if self.infoTable[i][0]== partLabel:
                    self.infos[i].setText(PART.Label)
        except AttributeError:
        ### if field is not active
            pass


    
    pass