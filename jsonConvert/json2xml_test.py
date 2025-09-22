# -*- coding: utf-8 -*-

from __future__ import absolute_import
import os
import sys
from time import localtime
from datetime import datetime


# from Code.json2xml.testFromjs2xml import Controller

from test_PLCControler import PLCControler
from plcopen.types_enums import ComputeConfigurationResourceName
from plcopen.VariableInfoCollector import _VariableInfos
from PLCGenerator import *
from util.ProcessLogger import ProcessLogger

from IT import ITdataCvter
from IT import ydscode_template, generate_ydspycode, njucode_template, \
generate_njupycode, fmlcode_template, generate_fmlpycode, generate_detectpycode, detect_template,\
    terminal_detect_template, generate_TerminalDetectPycode


from OT import OTdataCvter, TEMPLATE_DATA

import json
import logging
import traceback

import requests
from config import URL, PORT, ST_UPLOAD_ROUTE, IT_UPLOAD_ROUTE

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class Wire:
    # wires need points, refLocalId and formalParameter
    def __init__(self, points, refLocalId, formalParameter = ''):
        self.points = []
        self.SetPoints(points)
        self.refLocalId = refLocalId
        self.formalParameter = formalParameter

    def SetPoints(self, points):
        for point in points:
            self.points.append(Point(point[0], point[1]))

    def GetPoints(self):
        return self.points

    def GetConnectedInfos(self):
        return self.refLocalId, self.formalParameter

class Connector:
    def __init__(self, parent, name, type, position, negated=False, edge="none", onlyone=False):
        self.ParentBlock = parent 
        # self.Controler = controler # PLCControler or ProjectControler
        self.Name = name # ''
        self.Type = type
        self.Pos = Point(position[0], position[1])
        self.Wires = []
        self.OneConnected = onlyone
        # if self.Controler.IsOfType("BOOL", type):
        #     self.Negated = negated
        #     self.Edge = edge
        # else:
        #     self.Negated = False
        #     self.Edge = "none"
        if type == "BOOL":
            self.Negated = negated
            self.Edge = edge
        else:
            self.Negated = False
            self.Edge = "none"
        self.Valid = True
        self.Value = None
        self.Forced = False
        self.ValueSize = None
        self.ComputedValue = None
        self.Selected = False
        self.Highlights = []

    def SetNegated(self, negated):
        self.Negated = negated

    def SetEdge(self, edge):
        self.Edge = edge

    def SetWires(self, wires):
        for w in wires:
            wire = Wire(w["points"], w["refLocalId"], w["formalParameter"])

            if wire not in self.Wires:
                self.Wires.append(wire)

    # Returns the connector negated property
    def IsNegated(self):
        return self.Negated

    # Returns the connector edge property
    def GetEdge(self):
        return self.Edge

    # Returns the connector relative position
    def GetRelPosition(self):
        return self.Pos

    def GetWires(self):
        return self.Wires

    def GetName(self):
        return self.Name

class _ActionInfos(object):
    __slots__ = ["qualifier", "type", "value", "duration", "indicator"]

    def __init__(self, *args):
        for attr, value in zip(self.__slots__, args):
            setattr(self, attr, value if value is not None else "")

    def copy(self):
        return _ActionInfos(*[getattr(self, attr) for attr in self.__slots__])

class ProjectController(PLCControler):

    def __init__(self, data):
        PLCControler.__init__(self)
        self.data = data
        self.time = datetime(*localtime()[:6])
        self.start()

    def start(self):
        self.CreateNewProject(
            {"projectName": self.data["contentHeader"],
                "productName": "Unnamed",
                "productVersion": "1",
                "companyName": "Unknown",
                "creationDateTime": self.time})

        # set default scaling properties
        self.SetProjectProperties(properties={"scaling": {'FBD': (10, 10)}})
        self.SetProjectProperties(properties={"scaling": {'LD': (10, 10)}})
        self.SetProjectProperties(properties={"scaling": {'SFC': (10, 10)}})

    def Createxml(self):
        self.AddPou2xml(self.data["pou"])
        self.AddConfig2xml(self.data["config"])

    def AddPou2xml(self, pou):
        for func in pou["function"]:
            values = {'language': func["language"], 'pouName': func["name"], 'pouType': func["type"], 'returnType': func["returnType"]}
            tagname = self.ProjectAddPou(values["pouName"], values["pouType"], values["language"])
            self.SetPouInterfaceReturnType(values["pouName"], values["returnType"])
            self.AddVariable2xml(tagname, func["variable"])
            self.AddBody2xml(tagname, func["body"], values["language"])

        for fb in pou["functionBlock"]:
            values = {'language': fb["language"], 'pouName': fb["name"], 'pouType': fb["type"]}
            tagname = self.ProjectAddPou(values["pouName"], values["pouType"], values["language"])
            self.AddVariable2xml(tagname, fb["variable"])
            self.AddBody2xml(tagname, fb["body"], values["language"])
        
        # for fb in pou["libFB"]:
        #     values = {'language': fb["language"], 'pouName': fb["name"], 'pouType': fb["type"]}
        #     tagname = self.ProjectAddPou(values["pouName"], values["pouType"], values["language"])
        #     self.AddVariable2xml(tagname, fb["variable"])
        #     self.AddBody2xml(tagname, fb["body"], values["language"])

        for pgm in pou["program"]:
            values = {'language': pgm["language"], 'pouName': pgm["name"], 'pouType': pgm["type"]}
            tagname = self.ProjectAddPou(values["pouName"], values["pouType"], values["language"])
            self.AddVariable2xml(tagname, pgm["variable"])
            self.AddBody2xml(tagname, pgm["body"], values["language"])
        
        


    def AddConfig2xml(self, config):
        config_name = config["name"]
        self.ProjectAddConfiguration(config_name)

        # Add Resources to Configuration
        for i in range(len(config["resource"])):
            res = config["resource"][i]
            res_name = res["name"]
            self.ProjectAddConfigurationResource(config_name, res_name)
            resource_tagname = ComputeConfigurationResourceName(config_name, res_name)

            # set configuation
            task = res["task"]
            instance = res["instance"]
            self.SetEditedResourceInfos(resource_tagname, task, instance)

            # add global variables
            if "variable" in res:
                Variables = []
                for variable in res["variable"]:
                    row_content = _VariableInfos(variable["name"], 'Global',variable["option"],variable["location"],
                                variable["initialValue"],variable["edit"],variable["documentation"],variable["type"],variable["tree"],variable["number"])
                    Variables.append(row_content)
                self.SetConfigurationResourceGlobalVars(config_name, res_name, Variables)
                

    def AddVariable2xml(self, tagname, Variable):
        Variables = []
        for variable in Variable:
            row_content = _VariableInfos(variable["name"], variable["class"],variable["option"],variable["location"],
                        variable["initialValue"],variable["edit"],variable["documentation"],variable["type"],variable["tree"],variable["number"])
            Variables.append(row_content)

        words = tagname.split("::")
        self.SetPouInterfaceVars(words[1], Variables)

    def AddBody2xml(self, tagname, body, language):
        if language == "ST" or language == "IL":
            self.SetEditedElementText(tagname, body)
        elif language == "FBD":
            self.AddbodyVariables(tagname, body, "FBD")
            self.AddbodyBlocks(tagname, body)
            self.AddbodyConnections(tagname, body)
            self.AddbodyComment(tagname, body)
        elif language == "LD":
            self.AddbodyVariables(tagname, body, "LD")
            self.AddbodyBlocks(tagname, body)
            self.AddbodyConnections(tagname, body)
            self.AddbodyPowerRails(tagname, body)
            self.AddbodyCoil(tagname, body)
            self.AddbodyContact(tagname, body)
            self.AddbodyComment(tagname, body)
        elif language == "SFC":
            self.AddbodyVariables(tagname, body, "SFC")
            self.AddbodyBlocks(tagname, body)
            self.AddbodyConnections(tagname, body)
            self.AddbodyPowerRails(tagname, body)
            self.AddbodyContact(tagname, body)
            self.AddbodyStep(tagname, body)
            self.AddbodyDivergence(tagname, body)
            self.AddbodyTransition(tagname, body)
            self.AddbodyActionblock(tagname, body)
            self.AddbodyJump(tagname, body)
            self.AddbodyComment(tagname, body)

    # add graphical elements variale block to the project
    def AddbodyVariables(self, tagname, body, language = "FBD"):
        for values in body["variable"]:
            self.AddEditedElementVariable(tagname, values['id'], values["class"])

            infos = {}
            infos["name"] = values["expression"]
            if language == "FBD":
                infos["executionOrder"] = values['executionOrder']
            infos["x"], infos["y"] = values["x"], values["y"]
            infos["width"], infos["height"] = (values["width"], values["height"])
            infos["connectors"] = {'inputs': [], 'outputs': []}
            inputs, outputs = values["connectors"]["inputs"], values["connectors"]["outputs"]

            if (len(inputs) > 0):
                for k in range(len(inputs)):
                    input = inputs[k]
                    connector = Connector(values, "", values['var_type'], input["pos"], False, "none", False)
                    wire = input["wire"]
                    if wire != [{}]:
                        connector.SetWires(wire)
                    infos["connectors"]["inputs"].append(connector)

            if (len(outputs) > 0):
                for k in range(len(outputs)):
                    connector = Connector(values, "", values['var_type'], outputs[k]["pos"], False, "none", False)
                    infos["connectors"]["outputs"].append(connector)

            self.SetEditedElementVariableInfos(tagname, values['id'], infos)

    # add graphical elements block to the project
    def AddbodyBlocks(self, tagname, body):
        for values in body["block"]:
            self.AddEditedElementBlock(tagname, values['id'], values["type"], values.get("name", None))

            inputs, outputs = values["connectors"]["inputs"], values["connectors"]["outputs"]
            infos = {}
            infos["type"] = values["type"]
            infos["name"] = values["name"]
            # if self.CurrentLanguage == "FBD":
            # infos["executionOrder"] = values['executionOrder']
            infos["x"], infos["y"] = values["x"], values["y"]
            infos["width"], infos["height"] = (values["width"], values["height"])
            infos["connectors"] = {'inputs': [], 'outputs': []}

            for input in inputs:
                connector = Connector(values, input["name"], input["type"], input["pos"], onlyone=True)
                wire = input["wire"]
                if wire != {}:
                    connector.SetWires(wire)
                # none negated rising falling
                if input["modifier"] == "negated": 
                    connector.SetNegated(True)
                elif input["modifier"] != "none":
                    connector.SetEdge(input["modifier"])
                infos["connectors"]["inputs"].append(connector)

            for output in outputs:
                connector = Connector(values, output["name"], output["type"], output["pos"])
                # none negated rising falling
                if output["modifier"] == "negated": 
                    connector.SetNegated(True)
                elif output["modifier"] != "none":
                    connector.SetEdge(output["modifier"])
                infos["connectors"]["outputs"].append(connector)

            self.SetEditedElementBlockInfos(tagname, values['id'], infos)

    # add graphical elements connection to the project
    def AddbodyConnections(self, tagname, body):
        for values in body["connection"]:
            self.AddEditedElementConnection(tagname, values['id'], values["type"])
            
            infos = {}
            infos["name"] = values["name"]
            infos['x'], infos['y'] = values["x"], values["y"]
            infos["width"], infos["height"] = (values["width"], values["height"])
            if values['type'] == 0:
                input = values["connectors"]
                wire = input["wire"]
                connector = Connector(values, input["name"], input["type"], input["pos"], onlyone=True)
                connector.SetWires(wire)
            else:
                ouput = values["connectors"]
                connector = Connector(values, ouput["name"], ouput["type"], ouput["pos"])

            infos["connector"] = connector
            self.SetEditedElementConnectionInfos(tagname, values['id'], infos)

    # add graphical elements power rail to the project
    def AddbodyPowerRails(self, tagname, body):
        for values in body["powerrail"]:
            self.AddEditedElementPowerRail(tagname, values['id'], values["type"])

            inputs, outputs = values["connectors"]["inputs"], values["connectors"]["outputs"]
            infos = {}
            infos["id"] = values["id"]
            infos["x"], infos["y"] = values["x"], values["y"]
            infos["width"], infos["height"] = (values["width"], values["height"])
            infos["connectors"] = {'inputs': [], 'outputs': []}

            for input in inputs:
                connector = Connector(values, '', None, input["pos"], onlyone=True)
                wire = input["wire"]
                if wire != {}:
                    connector.SetWires(wire)
                infos["connectors"]["inputs"].append(connector)

            for output in outputs:
                connector = Connector(values, '', None, output["pos"])
                infos["connectors"]["outputs"].append(connector)

            self.SetEditedElementPowerRailInfos(tagname, values['id'], infos)

    # add graphical elements coil to the project
    def AddbodyCoil(self, tagname, body):
        for values in body['coil']:
            self.AddEditedElementCoil(tagname,values['id'])

            infos = {}
            infos["name"] = values["variable"]
            infos["type"] = values["modifier"]
            infos["x"], infos["y"] = values["x"], values["y"]
            infos["width"], infos["height"] = values["width"], values["height"]
            infos["connectors"] = {'inputs': [], 'outputs': []}

            inputs, outputs = values["connectors"]["inputs"], values["connectors"]["outputs"]

            if (len(inputs) > 0):
                for input in inputs:
                    connector = Connector(values, "", None, input["pos"])
                    wire = input["wire"]
                    if wire != {}:
                        connector.SetWires(wire)
                    infos["connectors"]["inputs"].append(connector)

            if (len(outputs) > 0):
                for output in outputs:
                    connector = Connector(values, "", None, output["pos"])
                    infos["connectors"]["outputs"].append(connector)

            self.SetEditedElementCoilInfos(tagname, values['id'], infos)

    # add graphical elements contact to the project
    def AddbodyContact(self, tagname, body):
        for values in body['contact']:
            self.AddEditedElementContact(tagname,values['id'])

            infos = {}
            infos["name"] = values["variable"]
            infos["type"] = values["modifier"]
            infos["x"], infos["y"] = values["x"], values["y"]
            infos["width"], infos["height"] = values["width"], values["height"]
            infos["connectors"] = {'inputs': [], 'outputs': []}

            inputs, outputs = values["connectors"]["inputs"], values["connectors"]["outputs"]

            if (len(inputs) > 0):
                for input in inputs:
                    connector = Connector(values, "", None, input["pos"])
                    wire = input["wire"]
                    if wire != {}:
                        connector.SetWires(wire)
                    infos["connectors"]["inputs"].append(connector)

            if (len(outputs) > 0):
                for output in outputs:
                    connector = Connector(values, "", None, output["pos"])
                    infos["connectors"]["outputs"].append(connector)

            self.SetEditedElementContactInfos(tagname, values['id'], infos)

    # add graphical elements step to the project
    def AddbodyStep(self, tagname, body):
        for values in body["step"]:
            self.AddEditedElementStep(tagname, values['id'])

            inputs = values["connectors"]["inputs"]
            outputs = values["connectors"]["outputs"]
            action = values["connectors"]["action"]

            infos = {}
            infos["name"] = values["name"]
            infos["initial"] = values["initial"]
            infos["x"], infos["y"] = values["x"], values["y"]
            infos["width"], infos["height"] = (values["width"], values["height"])
            infos["connectors"] = {'inputs': [], 'outputs': []}
            infos["action"] = None

            for input in inputs:
                connector = Connector(values, '', None, input["pos"], onlyone=True)
                wire = input["wire"]
                if wire != {}:
                    connector.SetWires(wire)
                infos["connectors"]["inputs"].append(connector)

            for output in outputs:
                connector = Connector(values, '', None, output["pos"])
                infos["connectors"]["outputs"].append(connector)

            for act in action:
                connector = Connector(values, '', None, act["pos"])
                infos["action"] = connector

            self.SetEditedElementStepInfos(tagname, values['id'], infos)

    # add graphical elements divergence to the project
    def AddbodyDivergence(self, tagname, body):
        for values in body["divergence"]:
            self.AddEditedElementDivergence(tagname, values['id'], values["type"])

            inputs = values["connectors"]["inputs"]
            outputs = values["connectors"]["outputs"]

            infos = {}
            infos["x"], infos["y"] = values["x"], values["y"]
            infos["width"], infos["height"] = (values["width"], values["height"])
            infos["connectors"] = {'inputs': [], 'outputs': []}

            for input in inputs:
                connector = Connector(values, '', None, input["pos"], onlyone=True)
                wire = input["wire"]
                if wire != {}:
                    connector.SetWires(wire)
                infos["connectors"]["inputs"].append(connector)

            for output in outputs:
                connector = Connector(values, '', None, output["pos"])
                infos["connectors"]["outputs"].append(connector)

            self.SetEditedElementDivergenceInfos(tagname, values['id'], infos)

    # add graphical elements transition to the project
    def AddbodyTransition(self, tagname, body):
        for values in body["transition"]:
            self.AddEditedElementTransition(tagname, values['id'])

            inputs = values["connectors"]["inputs"]
            outputs = values["connectors"]["outputs"]
            connection = values["connection"]

            infos = {}
            infos["type"] = values["type"]
            infos["priority"] = values["priority"]
            infos["condition"] = values["condition"]
            infos["connection"] = None
            infos["x"], infos["y"] = values["x"], values["y"]
            infos["width"], infos["height"] = (values["width"], values["height"])
            infos["connectors"] = {'inputs': [], 'outputs': []}

            for input in inputs:
                connector = Connector(values, '', None, input["pos"], onlyone=True)
                wire = input["wire"]
                if wire != [{}]:
                    connector.SetWires(wire)
                infos["connectors"]["inputs"].append(connector)

            for output in outputs:
                connector = Connector(values, '', None, output["pos"])
                infos["connectors"]["outputs"].append(connector)

            if connection != None:
                connector = Connector(values, '', None, (0, 0), onlyone=True)
                connector.SetWires(connection)
                infos["connection"] = connector

            self.SetEditedElementTransitionInfos(tagname, values['id'], infos)

    # add graphical elements action block to the project
    def AddbodyActionblock(self, tagname, body):
        for values in body["actionblock"]:
            self.AddEditedElementActionBlock(tagname, values['id'])

            input = values["connectors"]
            action = values["action"]

            infos = {}
            infos["x"], infos["y"] = values["x"], values["y"]
            infos["width"], infos["height"] = (values["width"], values["height"])
            infos["actions"] = []

            connector = Connector(values, '', None, input["pos"], onlyone=True)
            wire = input["wire"]
            if wire != [{}]:
                connector.SetWires(wire)
            infos["connector"] = connector

            for act in action:
                actionInfo = _ActionInfos(act["qualifier"], act["type"], act["value"], act["duration"], act["indicator"])
                infos["actions"].append(actionInfo)

            self.SetEditedElementActionBlockInfos(tagname, values['id'], infos)

    # add graphical elements jump to the project
    def AddbodyJump(self, tagname, body):
        for values in body["jump"]:
            self.AddEditedElementJump(tagname, values['id'])

            input = values["connectors"]

            infos = {}
            infos["target"] = values["target"]
            infos["x"], infos["y"] = values["x"], values["y"]
            infos["width"], infos["height"] = (values["width"], values["height"])

            connector = Connector(values, '', None, input["pos"], onlyone=True)
            wire = [input["wire"]]
            if wire != [{}]:
                connector.SetWires(wire)
            infos["connector"] = connector

            self.SetEditedElementJumpInfos(tagname, values['id'], infos)
    
    # add graphical elements commemt to the project
    def AddbodyComment(self, tagname, body):
        for values in body["comment"]:
            self.AddEditedElementComment(tagname, values['id'])
            self.SetEditedElementCommentInfos(tagname, values['id'], values)

def getITtype(elements):
    for key, value in elements.items():
        if value['type'] == 'Program':
            return 'NJU'
        if value['type'] == 'Arm':
            return 'FML'
        if value['type'] == 'scheduler':
            return 'YDS'
        if value['type'] == 'Detect' and value['name'] == 'steel':
            return 'steel'
        if value['type'] == 'Detect' and value['name'] == 'TerminalDet':
            return 'TerminalDet'
    return False

def main():
    # 从 stdin 读取所有数据
    raw = sys.stdin.read()
    # print(raw)
    data = json.loads(raw)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    ProjectPath = os.path.join(current_dir, 'program')
    if not os.path.exists(ProjectPath):
        os.makedirs(ProjectPath)

    OT_data = OTdataCvter(data, TEMPLATE_DATA)

    try:
        URL = data['plant'][0]
    except:
        print('No plant URL found')
        URL = ''

    with open(os.path.join(ProjectPath, 'config.json'), 'w') as f:
        json.dump({"planturl":URL}, f)


    if OT_data == {}:
        print('OT data is empty')
        pass
    else:
        try:
            Controller = ProjectController(OT_data)
            Controller.Createxml()
            Controller.SaveXMLFile(os.path.join(ProjectPath, 'plc.xml'))

            program_filepath = os.path.join(ProjectPath, "generated_plc.st")

            errors = []
            warnings = []
            ProgramChunks = GenerateCurrentProgram(Controller, Controller.Project, errors, warnings)
            program_text = "".join([item[0] for item in ProgramChunks])

            programfile = open(program_filepath, "w")
            programfile.write(program_text.encode("utf-8"))
            programfile.close() 
            print('OT data converted successfully')
            log_path = os.path.join(ProjectPath, 'log.txt')
            with open(log_path, 'w') as f:
                f.write('Compiled')
        except Exception as e:
            print('Error in OT data conversion')
            print(traceback.format_exc())
            

    code_index = []

    # IT
    try:
        IT_data = data['IT']
        if IT_data == {}:
            print('IT data is empty')
            pass
        else:
            for i in range(len(IT_data)):
                elements = ITdataCvter(IT_data[i]['IT_code'])
                IT_flag = getITtype(elements)
                print(IT_flag)
                if IT_flag == 'NJU':
                    code = generate_njupycode(elements, njucode_template)
                    with open(os.path.join(ProjectPath, 'ITprogram' + str(i) + '.py'), 'w') as f:
                        f.write(code)
                elif IT_flag == 'YDS':
                    codes = generate_ydspycode(elements, ydscode_template)
                    for j in range(len(codes)):
                        code = codes[j]
                        with open(os.path.join(ProjectPath, 'ITprogram' + str(j) + '.py'), 'w') as f:
                            f.write(code)
                        code_index.append('ITprogram' + str(i) + '.py')
                elif IT_flag == 'FML':
                    code = generate_fmlpycode(elements, fmlcode_template)
                    with open(os.path.join(ProjectPath, 'ITprogram' + str(i) + '.py'), 'w') as f:
                        f.write(code)
                elif IT_flag == 'steel':
                    code = generate_detectpycode(elements, detect_template)
                    with open(os.path.join(ProjectPath, 'ITprogram' + str(i) + '.py'), 'w') as f:
                        f.write(code)
                    code_index.append('ITprogram' + str(i) + '.py')
                elif IT_flag == 'TerminalDet':
                    # terminal_detect_template, generate_TerminalDetectPycode
                    code = generate_TerminalDetectPycode(elements, terminal_detect_template)
                    with open(os.path.join(ProjectPath, 'ITprogram' + str(i) + '.py'), 'w') as f:
                        f.write(code)
                    code_index.append('ITprogram' + str(i) + '.py')
    except Exception as e:
        print('Error in IT data conversion')
        print(traceback.format_exc())
    

if __name__ == "__main__":
    main()
