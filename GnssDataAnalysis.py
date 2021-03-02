# -*- coding: utf-8 -*-
"""
Created on Sat Feb 27 13:30:17 2021

@author: yacht
"""

import numpy as np
import pandas as pd
import os
import datetime
from pyproj import Proj
from jismesh.utils import to_meshcode
import matplotlib.pyplot as plt
import PySimpleGUI as sg


#################################################
#           The parameter user changes          #
#################################################
# Selsect data directory; data must be a csv format
'''
path = "C:\\Users\\yacht\\Dropbox\\20210222_Noto" #data path
#path = "D:\\Vebots\\2021GNSStest\\20210222_Noto"
Area_number = 10

SaveCsvFileOn = False
CreateFileDfName = "AnalysisResult.csv"

FigOn = False
FigPath = "C:\\Users\\yacht\\Dropbox\\20210222_Noto\\Figure\\"

CleansingFileOn = False
CleansingPath = "C:\\Users\\yacht\\Dropbox\\20210222_Noto\\Cleansing\\"
'''

#https://www.gsi.go.jp/sokuchikijun/semidyna03.html

#################################################
#                Key functions                  #
#################################################
def MakeFileNameDictionary(Number,FileNameList):
    Dictionary={} #dictionary
    for i in range(Number):
        t = i+1
        index_name = "%d_" %t
        Dictionary[t] = [s for s in FileNameList if index_name in s] 

    result = Dictionary    
    
    return result

def CheckGGA(df):
    df_Format = df["Format"].values    
    judge_ref = len(df_Format)
    judge = len([s for s in df_Format if "GGA" in s])
    #print(judge_ref)
    #print(judge)
    if(judge_ref!=judge):
        result = False
        df = df.query('Format.str.contains("GGA")', engine='python') 
    else:
        result = True
        df = df
    
    return result,df

def DropNanCastData(df):
    df = df.dropna(subset=["Status"]) 
    df = df.dropna(subset=["Latitude"]) 
    df = df.dropna(subset=["Longitude"]) 
    
    df["Status"] = df["Status"].astype(np.int64)
    df["Latitude"] = df["Latitude"].astype(np.float64)
    df["Longitude"] = df["Longitude"].astype(np.float64)
    
    result = df
    
    return result

def PositioningTime(df): 
    df = df[df["Status"] != 0]
    
    df_Time = df["Time"].values
    df_Time = np.array(df_Time, dtype=np.float64)
    
    if len(df_Time)==0:
        #print("This data is not containing valid data")
        return False
    
    result = df_Time[len(df_Time)-1] - df_Time[0]
    result = datetime.timedelta(seconds=result)    
    
    return result

def CalculateFixRatio(df):
    df = df[df["Status"] != 0]
    
    df_Time = df["Time"].values
    df_Time = np.array(df_Time, dtype=np.float64)
    
    if len(df_Time)==0:
        #print("This data is not containing valid data")
        return False
    
    df_Status = df["Status"].values
    df_Status = np.array(df_Status, dtype=np.int64)
    
    df_Status_fix = np.count_nonzero(df_Status == 4)
    df_Status_whole = len(df_Status)
    #print(df_Status_fix)
    #print(df_Status_whole)
    result = df_Status_fix / df_Status_whole
    
    return result

def CalculateTimeToFirstFix(df): #[sec]
    df = df[df["Status"] != 0]
    
    df_Status = df["Status"].values
    df_Status = np.array(df_Status, dtype=np.int64)
    
    FixIndex = np.where(df_Status==4)[0]
    if len(FixIndex)==0:
       #print("This data is never fixed... :-(")
       return False
          
    #print(df)   
    df_Time = df["Time"].values
    df_Time = np.array(df_Time, dtype=np.float64)
    
    StartTime = df_Time[0]
    FirstFixTime = df_Time[FixIndex[0]]
    result = FirstFixTime - StartTime
    #print("StartTime ",df_Time[0])
    #print("FirstFixTime ",df_Time[FixIndex[0]])    
        
    return result

def dmm2deg(df_lat_dmm,df_lon_dmm):
    df_lat_deg = ((df_lat_dmm/100) - np.floor(df_lat_dmm/100)) *5/3 + np.floor(df_lat_dmm/100)
    df_lon_deg = ((df_lon_dmm/100) - np.floor(df_lon_dmm/100)) *5/3 + np.floor(df_lon_dmm/100)
    
    result = (df_lat_deg, df_lon_deg)    
    
    return result

def deg2utm(df_lat_deg, df_lon_deg):
    utmzone = int(df_lon_deg[0]//6+31)
    converter = Proj(proj='utm', zone=utmzone, ellps='WGS84')
    df_X, df_Y = converter(df_lon_deg, df_lat_deg)
    
    result = (df_X,df_Y,utmzone)    
    
    return result


def CalculateAccuracy(df): #std [cm]
    df = df[df["Status"] == 4]
    
    df_lat = df["Latitude"].values
    df_lon = df["Longitude"].values
    if len(df_lat) == 0:
        #print("This data is not fixed")
        FalseResult = (False,False)
        return FalseResult
    
    df_lat,df_lon = dmm2deg(df_lat,df_lon)
    df_X,df_Y,utmzone = deg2utm(df_lat, df_lon)
    
    X_std = np.std(df_X)*100
    Y_std = np.std(df_Y)*100
    result = (X_std,Y_std)
        
    return result


def current2epoch(df_lat,df_lon): #今期→元期 #https://www.gsi.go.jp/sokuchikijun/semidyna03.html
    meshcode = to_meshcode(df_lat[0],df_lon[0],2)
    #print(meshcode)
    meshcode = str(meshcode)
    df = pd.read_table("SemiDyna2020.par",header=11) #このファイル，カンマでもタブでもなくてほんとにきもぽよ
    #print(df)
    df_str = df.iloc[:,0].values
    #print(df_str)
    df_target = [s for s in df_str if meshcode in s]
    #print(df_target[0])
    df_target_index = np.where(df_str==df_target[0])[0][0]
    #print(df_target_index)
    
    target = df.iloc[int(df_target_index),:].values[0]
    target = target.split("  ")
    Lat_sec_DynaPara = float(target[1])
    Lon_sec_DynaPara = float(target[2])
    
    Lat_deg_DynaPara = Lat_sec_DynaPara /3600
    Lon_deg_DynaPara = Lon_sec_DynaPara /3600
    print(Lat_deg_DynaPara)
    print(Lon_deg_DynaPara)
    
    print("Before",df_lat[0])
    df_lat = df_lat - Lat_deg_DynaPara #足すと元期→今期，引くと今期→元期
    df_lon = df_lon - Lon_deg_DynaPara
    print("After",df_lat[0])
    result = (df_lat,df_lon)
    
    return result

def CalculateAveragePosition(df,type="RTK"):
    df = df[df["Status"] == 4]
    
    df_lat = df["Latitude"].values
    df_lon = df["Longitude"].values
    if len(df_lat) == 0:
        print("This data is not fixed")
        FalseResult = (False,False)
        return FalseResult
            
    df_lat,df_lon = dmm2deg(df_lat,df_lon)
    
    if type == "RTK":
        print("RTK")
    elif type == "CLAS":
        print("CLAS")
        df_lat,df_lon = current2epoch(df_lat,df_lon)
    else:
        print("Not define such type of GNSS.")
    
    df_X,df_Y,utmzone = deg2utm(df_lat, df_lon)
    
    X_ave = np.average(df_X)
    Y_ave = np.average(df_Y)
    
    result = (X_ave,Y_ave)
    
    return result


def ShowPositioning(df,figpath,figname):
    DirExist = os.path.isdir(figpath)
    if DirExist == False:
        #print("Such data path doesn't exist!")
        return False
    
    df = df[df["Status"] == 4]
    
    df_lat = df["Latitude"].values
    df_lon = df["Longitude"].values
    if len(df_lat) == 0:
        print("This data is not fixed")
        return True
    
    df_lat,df_lon = dmm2deg(df_lat,df_lon)
    df_X,df_Y,utmzone = deg2utm(df_lat, df_lon)
    X_ave = np.average(df_X)
    Y_ave = np.average(df_Y)
    
    fig = plt.figure() #figを作らないでいきなりpltを作るとグラフがバグる（謎）
    plt.scatter(df_X,df_Y,c="blue")
    plt.scatter(X_ave,Y_ave,c="red")
    plt.xlim([np.min(df_X)-0.2,np.max(df_X)+0.2])
    plt.ylim([np.min(df_Y)-0.2,np.max(df_Y)+0.2])
    
    plt.title(figname)
    #plt.show()
    name = figpath + figname
    plt.close(fig)
    fig.savefig("%s.png" %name)
    
    return True

def CreateCleansingFile(df,filepath,filename):
    DirExist = os.path.isdir(filepath)
    #print(DirExist)
    if DirExist == False:
        #print("Such data path doesn't exist!")
        return False
    
    df = df[df["Status"] == 4]
    
    df_lat = df["Latitude"].values
    df_lon = df["Longitude"].values
    if len(df_lat) == 0:
        #print("This data is not fixed")
        del df_lat
        del df_lon
        return True
    
    df_lat,df_lon = dmm2deg(df_lat,df_lon)
    df_X,df_Y,utmzone = deg2utm(df_lat, df_lon)
    
    df = df.assign(Lat=df_lat,Lon=df_lon,UTM_X=df_X,UTM_Y=df_Y)
    """# view vs. copy problem occurred...
    df["Lat(deg)"] = df_lat
    df["Lon(deg)"] = df_lon
    df["UTM_X"] = df_X
    df["UTM_Y"] = df_Y
    """
    filename = filepath + filename + "modified.csv"
    df.to_csv(filename)
    
    return True


#################################################
#                 Main program                  #
#################################################
def main(DataPath,AreaNumber,FigPath,CleansingPath,FigOn,CleansingOn,SemiDynamicOn):

    header = ["Format","Time","Latitude","LatType","Longitude","LonType",
              "Status","Satellite","LevelAccuracy","Altitude(sea)","M(sea)",
              "Altitude(geoid)","M(geoid)","DGPS use","checksum"]
    CreateFileDf = pd.DataFrame(columns = ["Positioning time",
                                           "Fix ratio",
                                           "Time to first fix [s]",
                                           "X std [cm]",
                                           "Y std [cm]",
                                           "X ave",
                                           "Y ave"])
    CreateFileDfName = "AnalysisResult.csv"
    
    #Make a list of all files　 
    DirExist = os.path.isdir(DataPath)
    if DirExist == False:
        print("Such data path doesn't exist!")
        return False
    os.chdir(DataPath)
    files = os.listdir(DataPath)
    #ftype = type(files)
    #flen = len(files)
    #print(files)
    #print("file type is %s" % ftype)
    #print("file length = %s" % flen)
    
    if SemiDynamicOn:
        if os.path.isfile("SemiDyna2020.par") == False:
            print("SemiDyna2020.par file doesn't exist!")
            return False
    
    AreaFile = MakeFileNameDictionary(AreaNumber,files) #print(AreaFile[1][0]) [AreaName][Number]
    conter = 0
    for j in range(AreaNumber): #The number of area
        h = j + 1
        
        for i in range(len(AreaFile[h])): #The number of receivers in an area
            conter = conter +1
            df = pd.read_csv(AreaFile[h][i],names=header)
            print(AreaFile[h][i])
            
            if CheckGGA(df)[0] != True:    
                df = CheckGGA(df)[1]
                #print("This data contains other than GGA format.")
                #print("Extract only GGA from it.")
            
            df = DropNanCastData(df)
            #print(df)
            
            positioningTime = PositioningTime(df)
            #print("Positioning time",positioningTime)
            
            Fix_ratio = CalculateFixRatio(df)
            #print("Fix ratio: ", Fix_ratio)
            
            TTFF = CalculateTimeToFirstFix(df)
            #print("TTFF:",TTFF, "sec")
            
            X_std,Y_std = CalculateAccuracy(df)
            #print("X_std:",X_std, "cm")
            #print("Y_std:",Y_std, "cm")
            
            if SemiDynamicOn:
                if "aqloc" in AreaFile[h][i]:
                    X_ave,Y_ave = CalculateAveragePosition(df,"CLAS")
                elif  "magellan" in AreaFile[h][i]:
                    X_ave,Y_ave = CalculateAveragePosition(df,"CLAS")
                else:
                    X_ave,Y_ave = CalculateAveragePosition(df,"RTK")
            else:
                X_ave,Y_ave = CalculateAveragePosition(df,"RTK")
            #print("X_ave:",X_ave)
            #print("Y_ave:",Y_ave)
            
            if FigOn == True:                
                if ShowPositioning(df,FigPath,AreaFile[h][i]) != True:
                    return False
                
            if CleansingOn == True:
                if CreateCleansingFile(df,CleansingPath,AreaFile[h][i]) != True:
                    return False
                
            CreateFileDf.loc[AreaFile[h][i]] = [positioningTime,
                                                Fix_ratio,
                                                TTFF,
                                                X_std,
                                                Y_std,
                                                X_ave,
                                                Y_ave]
            #if conter == 2:
            #   break
            #print("\n")
        #break   
        
    #print(CreateFileDf)
    
    CreateFileDf.to_csv(CreateFileDfName)
    print("Done write a csv file. Bye...")
    
    return True
    
#################################################
#                GUI functions                  #
#################################################
# Configure an option
sg.theme('Dark Blue 3')
layout = [
    [sg.Text('GNSS analysis as a form of .csv')],
    [sg.Text('Data path', size=(20, 1)),
         sg.InputText('D:\\Vebots\\2021GNSStest\\20210222_Noto',key='DataPath')],
    [sg.Text('Area number', size=(20, 1)), 
         sg.InputText("10",key='AreaNumber')],
    [sg.Text('Figure path (option)', size=(20, 1)), 
         sg.InputText('D:\\Vebots\\2021GNSStest\\20210222_Noto\\Figure\\',key='FigPath')],
    [sg.Text('Fix data file path (option)', size=(20, 1)), 
         sg.InputText('D:\\Vebots\\2021GNSStest\\20210222_Noto\\Cleansing\\',key='CleansingPath')], 
    [sg.Checkbox('Fig on', default=False,key='FigOn')],
    [sg.Checkbox('Fix data on', default=False,key='CleansingOn')],
    [sg.Checkbox('Semi dynamic on', default=False,key='SemiDynamicOn')],
    [sg.Submit(button_text='Execute')]
]

# Make a window
window = sg.Window('GNSS analysis', layout)

# Event loop
while True:
    event, values = window.read()

    if event is None:
        print('exit')
        break

    if event == 'Execute':
        success = main(values['DataPath'],int(values['AreaNumber']),values['FigPath'],
             values['CleansingPath'],values['FigOn'],values['CleansingOn'],values['SemiDynamicOn'])
        
        # Popup
        if success == True:
            sg.popup('Done making result.',title='Success')
        else:
            sg.popup('Failed',title='Failed')
# Discard a window and exit
window.close()



