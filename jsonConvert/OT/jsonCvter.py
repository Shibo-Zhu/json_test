import json
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DATA = {"pou": {"program": [],"function":[],"functionBlock":[],"libFB":[]}, "config": {},"contentHeader": "LD_Language"}
STANDARD_FB = ['SR', 'RS', 'SEMA', 'R_TRIG', 'F_TRIG', 'CTU', 'CTU_DINT', 'CTU_LINT', 'CTU_UDINT', 'CTU_ULINT', 'CTD', 'CTD_DINT', 'CTD_LINT', 'CTD_UDINT', 'CTD_ULINT', 'CTUD', 'CTUD_DINT', 'CTUD_LINT', 'CTUD_UDINT', 'CTUD_ULINT', 'TP', 'TON', 'TOF']

def getsourcePoint(block, port=None):
    point = []
    try:
        point.append(block['position']['x']+int(block['portPosition']['outPorts'][0]['out']['x']))
        point.append(block['position']['y']+int(block['portPosition']['outPorts'][0]['out']['y']))
    except: 
        for outport in block['portPosition']['outPorts']:
            if port in outport:
                point.append(block['position']['x']+int(outport[port]['x']))
                point.append(block['position']['y']+int(outport[port]['y']))
    return point    

def gettargetPoint(block, port=None):
    point = []
    try:
        point.append(block['position']['x']+int(block['portPosition']['inPorts'][0]['in']['x']))
        point.append(block['position']['y']+int(block['portPosition']['inPorts'][0]['in']['y']))
    except:
        for inport in block['portPosition']['inPorts']:
            if port in inport:
                point.append(block['position']['x']+int(inport[port]['x']))
                point.append(block['position']['y']+int(inport[port]['y']))
    return point

def OTdataCvter(front_data, template_data):
    if front_data['pou']['program'] == []:
        return {}
    for res in front_data['config']['resource']:
        for var in res['variable']:
            for key in var:
                if var[key] == '...':
                    var[key] = ''

        for task in res['task']:
            if task['Triggering'] == 'cyclic':
                task['Triggering'] = 'Cyclic'
            for key in task:
                if task[key] == '...':
                    task[key] = ''
                

    template_data['config'] = front_data['config']
    template_data['contentHeader'] = front_data['contentHeader']

    for prog in front_data['pou']['program']:
        
        for var in prog['variable']:
            for key in var:
                if var[key] == '...':
                    var[key] = ''
        if prog['language'] == 'ST' or prog['language'] == 'IL':
            tem_prog = {}
            tem_prog['name'] = prog['name']
            tem_prog['language'] = prog['language']
            tem_prog['type'] = prog['type']
            tem_prog['variable'] = prog['variable']
            tem_prog['body'] = prog['code'] 
            template_data['pou']['program'].append(tem_prog)
        elif prog['language'] == 'LD':
            tem_prog = {}
            tem_prog['name'] = prog['name']
            tem_prog['language'] = prog['language']
            tem_prog['type'] = prog['type']
            tem_prog['variable'] = prog['variable']

            # LeftRail_id, RightRail_id
            LeftRail_id = -1
            RightRail_id = -2
            # LeftRail_point, RightRail_point
            LeftRail_point = []
            RightRail_point = []
            
            # body
            body = {"comment":[], "powerrail":[], "coil":[], "contact":[], "block":[], "connection":[], "variable":[]}
            elements = {}
            code = prog['code']
            blocks = code['blocks']
            links = code['links']
            blockid = []
            for i in range(len(blocks)):
                blockid.append(blocks[i]['id'])
                blocks[i]['id'] = i + 1

            edited_block = []
            edited_sourceblock = []
            edited_targetblock = []
            for link in links:
                sourceID = blockid.index(link['SourceID']['id']) + 1
                targetID = blockid.index(link['TargetID']['id']) + 1
                sourcePort = link['SourceID']['port']
                targetPort = link['TargetID']['port']
                
                link['SourceID']['id'] = sourceID
                link['TargetID']['id'] = targetID

                sourceblock = blocks[sourceID-1]
                targetblock = blocks[targetID-1]

                if sourceblock['type'] in ['Variable', 'LeftRail', 'RightRail', 'Coil', 'Contact']:
                    sourcePort = ''
                else:
                    sourcePort = link['SourceID']['port']

                targetPort = link['TargetID']['port']

                sourcePoint = getsourcePoint(sourceblock, sourcePort)
                targetPoint = gettargetPoint(targetblock, targetPort)

                # sourcePoint = []
                # sourcePoint.append(sourceblock['position']['x']+sourceblock['portPosition']['outPorts'][0]['out']['x'])
                # sourcePoint.append(sourceblock['position']['y']+sourceblock['portPosition']['outPorts'][0]['out']['y'])
                # targetPoint = []
                # targetPoint.append(targetblock['position']['x']+targetblock['portPosition']['inPorts'][0]['in']['x'])
                # targetPoint.append(targetblock['position']['y']+targetblock['portPosition']['inPorts'][0]['in']['y'])

                edited_inPort = []

                if sourceblock['type'] == 'LeftRail':
                    if LeftRail_id == -1:
                        LeftRail_id = sourceID
                        LeftRail_point = [sourceblock['position']['x'],sourceblock['position']['y']]
                        edited_sourceblock.append(sourceID)
                        blockinfo = {'_type':sourceblock['type'], 'class':sourceblock['type'],'id': sourceID, 'x': sourceblock['position']['x'], 'y': sourceblock['position']['y'],
                                        'width': sourceblock['size']['width'], 'height': sourceblock['size']['height'], 'type': 0,
                                        'connectors': {'inputs': [], 'outputs': [{"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']]}]}}
                        # body['powerrail'].append(blockinfo)
                        elements[str(sourceID)] = blockinfo
                    else:
                        sourceID = LeftRail_id
                        blockinfo=elements[str(LeftRail_id)]
                        blockinfo['height'] =  blockinfo['height'] + sourceblock['size']['height']
                        blockinfo['connectors']['outputs'].append({"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']+blockinfo['height']]})
                        sourcePoint = [LeftRail_point[0],LeftRail_point[1]+sourceblock['portPosition']['outPorts'][0]['out']['y']+blockinfo['height']]
                        

                if targetblock['type'] == 'RightRail':
                    edited_targetblock.append(targetID)
                    blockinfo = {'_type':targetblock['type'], 'class':targetblock['type'], 'id': targetID, 'x': targetblock['position']['x'], 'y': targetblock['position']['y'],
                                    'width': targetblock['size']['width'], 'height': targetblock['size']['height'], 'type': 1,
                                    'connectors': {'inputs': [{"wire":[{"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[targetblock['portPosition']['inPorts'][0]['in']['x'],targetblock['portPosition']['inPorts'][0]['in']['y']]}], 'outputs': []}}
                    # body['powerrail'].append(blockinfo)
                    elements[str(targetID)] = blockinfo

                    # print(body)

                if sourceblock['type'] == 'Contact':
                    if sourceID in edited_sourceblock:
                        pass
                    edited_sourceblock.append(sourceID)
                    if sourceID not in edited_block:
                        edited_block.append(sourceID)
                        blockinfo = {'_type':targetblock['type'], 'class':sourceblock['type'], 'id': sourceID, 'x': sourceblock['position']['x'], 'y': sourceblock['position']['y'],
                                        'width': sourceblock['size']['width'], 'height': sourceblock['size']['height'], 'modifier': sourceblock['modifier'], 'variable': sourceblock['name'],
                                        'connectors': {'inputs': [], 'outputs': [{"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']]}]}}
                    else:
                        # output donot care more than one
                        blockinfo = elements[str(sourceID)]
                        blockinfo['connectors']['outputs'].append({"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']]})
                    elements[str(sourceID)] = blockinfo

                if targetblock['type'] == 'Contact': 
                    
                    if targetID not in edited_block:
                        edited_block.append(targetID)
                        edited_targetblock.append(targetID)
                        blockinfo = {'_type':targetblock['type'], 'class':targetblock['type'], 'id': targetID, 'x': targetblock['position']['x'], 'y': targetblock['position']['y'],
                                        'width': targetblock['size']['width'], 'height': targetblock['size']['height'], 'modifier': targetblock['modifier'], 'variable': targetblock['name'],
                                        'connectors': {'inputs': [{"wire":[{"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[targetblock['portPosition']['inPorts'][0]['in']['x'],targetblock['portPosition']['inPorts'][0]['in']['y']]}], 'outputs': []}}
                    elif targetID in edited_sourceblock and targetID not in edited_targetblock:
                        edited_targetblock.append(targetID)
                        blockinfo = elements[str(targetID)]
                        blockinfo['connectors']['inputs'].append({"wire":[{"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[targetblock['portPosition']['inPorts'][0]['in']['x'],targetblock['portPosition']['inPorts'][0]['in']['y']]})
                    elif targetID in edited_targetblock:
                        blockinfo = elements[str(targetID)]
                        blockinfo['connectors']['inputs'][0]['wire'].append({"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID})
                    elements[str(targetID)] = blockinfo

                if sourceblock['type'] == 'Coil':
                    if sourceID in edited_sourceblock:
                        pass
                    edited_sourceblock.append(sourceID)
                    if sourceID not in edited_block:
                        edited_block.append(sourceID)
                        blockinfo = {'_type':sourceblock['type'], 'class':sourceblock['type'], 'id': sourceID, 'x': sourceblock['position']['x'], 'y': sourceblock['position']['y'],
                                        'width': sourceblock['size']['width'], 'height': sourceblock['size']['height'], 'modifier': sourceblock['modifier'], 'variable': sourceblock['name'],
                                        'connectors': {'inputs': [], 'outputs': [{"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']]}]}}
                    else:
                        blockinfo = elements[str(sourceID)]
                        blockinfo['connectors']['outputs'].append({"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']]})

                    elements[str(sourceID)] = blockinfo

                if targetblock['type'] == 'Coil':
                    
                    if targetID not in edited_block:
                        edited_block.append(targetID)
                        edited_targetblock.append(targetID)
                        blockinfo = {'_type':targetblock['type'], 'class':targetblock['type'], 'id': targetID, 'x': targetblock['position']['x'], 'y': targetblock['position']['y'],
                                        'width': targetblock['size']['width'], 'height': targetblock['size']['height'], 'modifier': targetblock['modifier'], 'variable': targetblock['name'],
                                        'connectors': {'inputs': [{"wire":[{"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[targetblock['portPosition']['inPorts'][0]['in']['x'],targetblock['portPosition']['inPorts'][0]['in']['y']]}], 'outputs': []}}
                    elif targetID in edited_sourceblock and targetID not in edited_targetblock:
                        edited_targetblock.append(targetID)
                        blockinfo = elements[str(targetID)]

                        blockinfo['connectors']['inputs'].append({"wire":[{"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[targetblock['portPosition']['inPorts'][0]['in']['x'],targetblock['portPosition']['inPorts'][0]['in']['y']]})
                    elif targetID in edited_targetblock:
                        blockinfo = elements[str(targetID)]
                        blockinfo['connectors']['inputs'][0]['wire'].append({"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID})
                    elements[str(targetID)] = blockinfo

                if sourceblock['type'] == 'Variable':
                    if sourceID in edited_sourceblock:
                        pass
                    edited_sourceblock.append(sourceID)
                    if sourceID not in edited_targetblock:
                        edited_block.append(sourceID)
                        blockinfo = {'_type':sourceblock['type'], 'type':sourceblock['type'],'class':sourceblock['modifier'], 'id': sourceID, 'x': sourceblock['position']['x'], 'y': sourceblock['position']['y'],'width': sourceblock['size']['width'], 'height': sourceblock['size']['height'], 'var_type': sourceblock['var_type'],'expression': sourceblock['name'],'executionOrder': sourceblock['executionOder'],'connectors': {'inputs': [], 'outputs': [{"pos":[int(sourceblock['portPosition']['outPorts'][0]['out']['x']),int(sourceblock['portPosition']['outPorts'][0]['out']['y'])]}]}}
                    else:
                        blockinfo = elements[str(sourceID)]
                        blockinfo['connectors']['outputs'].append({"pos":[int(sourceblock['portPosition']['outPorts'][0]['out']['x']),int(sourceblock['portPosition']['outPorts'][0]['out']['y'])]})
                    elements[str(sourceID)] = blockinfo

                if targetblock['type'] == 'Variable':
                    if targetID not in edited_targetblock:
                        edited_targetblock.append(sourceID)
                        blockinfo = {'_type':targetblock['type'], 'type':targetblock['type'],'class':targetblock['modifier'], 'id': targetID, 'x': targetblock['position']['x'], 'y': targetblock['position']['y'],'width': targetblock['size']['width'], 'height': targetblock['size']['height'], 'var_type': targetblock['var_type'],'expression': targetblock['name'],'executionOrder': targetblock['executionOder'],'connectors': {'inputs': [{'wire':[{"formalParameter":sourcePort,"points":[targetPoint,sourcePoint],"refLocalId":sourceID}],'pos':[int(targetblock['portPosition']['inPorts'][0]['in']['x']),int(targetblock['portPosition']['inPorts'][0]['in']['y'])]}], 'outputs': []}}
                        elements[str(targetID)] = blockinfo

                # ------ Standard FB ------
                if targetblock['type'] in STANDARD_FB:
                    if targetID not in edited_targetblock:
                        edited_targetblock.append(targetID)
                        inPorts = targetblock['portPosition']['inPorts']
                        outPorts = targetblock['portPosition']['outPorts']
                        outputs = []
                        for port in outPorts:
                            for key, value in port.items():
                                if key != 'modifier' and key != 'type':
                                    outputs.append({"modifier": port['modifier'], "type": port['type'], "name": key,
                                                    "pos": [int(port[key]['x']), int(port[key]['y'])]})

                        for port in inPorts:
                            if targetPort in port:
                                blockinfo = {'_type': targetblock['type'], 'type': targetblock['type'],
                                             'id': targetID, 'name': targetblock['name'],
                                             'x': targetblock['position']['x'], 'y': targetblock['position']['y'],
                                             'width': targetblock['size']['width'],
                                             'height': targetblock['size']['height'],
                                             'executionControl': targetblock['executionControl'],
                                             'executionOrder': targetblock['executionOder'], 'connectors': {
                                        'inputs': [
                                            {"modifier": port['modifier'], "type": port['type'], "name": targetPort,
                                             "wire": [{"formalParameter": sourcePort,
                                                       "points": [targetPoint, sourcePoint],
                                                       "refLocalId": sourceID}],
                                             "pos": [int(port[targetPort]['x']), int(port[targetPort]['y'])]}],
                                        'outputs': outputs}}
                            elements[str(targetID)] = blockinfo
                    else:
                        inPorts = targetblock['portPosition']['inPorts']
                        for port in inPorts:
                            if targetPort in port:
                                blockinfo = elements[str(targetID)]
                                blockinfo['connectors']['inputs'].append(
                                    {"modifier": port['modifier'], "type": port['type'], "name": targetPort,
                                     "wire": [{"formalParameter": sourcePort, "points": [targetPoint, sourcePoint],
                                               "refLocalId": sourceID}],
                                     "pos": [int(port[targetPort]['x']), int(port[targetPort]['y'])]})
                        elements[str(targetID)] = blockinfo

                # print(elements)
            with open(os.path.join(current_dir,'element.json'), 'w') as f:
                json.dump(elements, f, indent=4)

            for element in elements:
                if elements[element]['_type'] == 'LeftRail' or elements[element]['_type'] == 'RightRail':
                    body['powerrail'].append(elements[element])
                elif elements[element]['_type'] == 'Coil':
                    body['coil'].append(elements[element])
                elif elements[element]['_type'] == 'Contact':
                    body['contact'].append(elements[element])
                elif elements[element]['_type'] == 'Variable':
                    body['variable'].append(elements[element])
                elif elements[element]['_type'] in STANDARD_FB:
                    body['block'].append((elements[element]))

            tem_prog['body'] = body

            template_data['pou']['program'].append(tem_prog)
            with open(os.path.join(current_dir,'data.json'), 'w') as f:
                json.dump(template_data, f, indent=4)
        elif prog['language'] == 'FBD':
            tem_prog = {}
            tem_prog['name'] = prog['name']
            tem_prog['language'] = prog['language']
            tem_prog['type'] = prog['type']
            tem_prog['variable'] = prog['variable']
            body = {"variable":[], "block":[], "comment":[], "connection":[]}
            elements = {}
            code = prog['code']
            blocks = code['blocks']
            links = code['links']
            blockid = []
            for i in range(len(blocks)):
                blockid.append(blocks[i]['id'])
                blocks[i]['id'] = i + 1

            edited_block = []
            edited_sourceblock = []
            edited_targetblock = []

            for link in links:
                sourceID = blockid.index(link['SourceID']['id']) + 1
                targetID = blockid.index(link['TargetID']['id']) + 1

                link['SourceID']['id'] = sourceID
                link['TargetID']['id'] = targetID

                sourceblock = blocks[sourceID-1]
                targetblock = blocks[targetID-1]

                if sourceblock['type'] == 'Variable':
                    sourcePort = ''
                else:
                    sourcePort = link['SourceID']['port']

                targetPort = link['TargetID']['port']

                sourcePoint = getsourcePoint(sourceblock, sourcePort)
                targetPoint = gettargetPoint(targetblock, targetPort)

                if sourceblock['type'] == 'Variable':
                    if sourceID in edited_sourceblock:
                        pass
                    edited_sourceblock.append(sourceID)
                    if sourceID not in edited_targetblock:
                        edited_block.append(sourceID)
                        blockinfo = {'type':sourceblock['type'],'class':sourceblock['modifier'], 'id': sourceID, 'x': sourceblock['position']['x'], 'y': sourceblock['position']['y'],'width': sourceblock['size']['width'], 'height': sourceblock['size']['height'], 'var_type': sourceblock['var_type'],'expression': sourceblock['name'],'executionOrder': sourceblock['executionOder'],'connectors': {'inputs': [], 'outputs': [{"pos":[int(sourceblock['portPosition']['outPorts'][0]['out']['x']),int(sourceblock['portPosition']['outPorts'][0]['out']['y'])]}]}}
                    else:
                        blockinfo = elements[str(sourceID)]
                        blockinfo['connectors']['outputs'].append({"pos":[int(sourceblock['portPosition']['outPorts'][0]['out']['x']),int(sourceblock['portPosition']['outPorts'][0]['out']['y'])]})
                    elements[str(sourceID)] = blockinfo

                if targetblock['type'] == 'Variable':
                    if targetID not in edited_targetblock:
                        edited_targetblock.append(sourceID)
                        blockinfo = {'type':targetblock['type'],'class':targetblock['modifier'], 'id': targetID, 'x': targetblock['position']['x'], 'y': targetblock['position']['y'],'width': targetblock['size']['width'], 'height': targetblock['size']['height'], 'var_type': targetblock['var_type'],'expression': targetblock['name'],'executionOrder': targetblock['executionOder'],'connectors': {'inputs': [{'wire':[{"formalParameter":sourcePort,"points":[targetPoint,sourcePoint],"refLocalId":sourceID}],'pos':[int(targetblock['portPosition']['inPorts'][0]['in']['x']),int(targetblock['portPosition']['inPorts'][0]['in']['y'])]}], 'outputs': []}}
                        elements[str(targetID)] = blockinfo

                if targetblock['type'] == 'ADD':
                    pass

                if targetblock['type'] == 'UserBlock':
                    if targetID not in edited_targetblock:
                        edited_targetblock.append(targetID)
                        inPorts = targetblock['portPosition']['inPorts']
                        outPorts = targetblock['portPosition']['outPorts']
                        outputs = []
                        for port in outPorts:
                            for key, value in port.items():
                                if key != 'modifier' and key != 'type':
                                    outputs.append({"modifier":port['modifier'],"type":port['type'],"name":key,"pos":[int(port[key]['x']),int(port[key]['y'])]})

                        for port in inPorts:
                            if targetPort in port:
                                blockinfo = {'_type':targetblock['type'],'type':targetblock['blockType'], 'id': targetID,'name':targetblock['name'], 'x': targetblock['position']['x'], 'y': targetblock['position']['y'],'width': targetblock['size']['width'], 'height': targetblock['size']['height'], 'executionControl': targetblock['executionControl'],'executionOrder': targetblock['executionOder'],'connectors': {'inputs': [{"modifier":port['modifier'],"type":port['type'],"name":targetPort,"wire":[{"formalParameter":sourcePort,"points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[int(port[targetPort]['x']),int(port[targetPort]['y'])]}], 'outputs': outputs}}
                            elements[str(targetID)] = blockinfo  
                    else:
                        inPorts = targetblock['portPosition']['inPorts']
                        for port in inPorts:
                            if targetPort in port:
                                blockinfo = elements[str(targetID)]
                                blockinfo['connectors']['inputs'].append({"modifier":port['modifier'],"type":port['type'],"name":targetPort,"wire":[{"formalParameter":sourcePort,"points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[int(port[targetPort]['x']),int(port[targetPort]['y'])]})
                        elements[str(targetID)] = blockinfo
            for element in elements:
                if elements[element]['type'] == 'Variable':
                    body['variable'].append(elements[element])
                elif elements[element]['type'] == 'UserBlock' or ('_type' in elements[element] and  elements[element]['_type'] == 'UserBlock'):
                    body['block'].append(elements[element])  
            tem_prog['body'] = body
            template_data['pou']['program'].append(tem_prog)
        elif prog['language'] == 'SFC':
            tem_prog = {}
            tem_prog['name'] = prog['name']
            tem_prog['language'] = prog['language']
            tem_prog['type'] = prog['type']
            tem_prog['variable'] = prog['variable']
            body = {"powerrail":[], "contact":[], "transition":[], "divergence":[], "jump":[], "step":[], "variable":[], "block":[], "comment":[], "connection":[], "actionblock":[]}
            elements = {}
            code = prog['code']
            blocks = code['blocks']
            links = code['links']
            blockid = []
            for i in range(len(blocks)):
                blockid.append(blocks[i]['id'])
                blocks[i]['id'] = i + 1

            edited_block = []
            edited_sourceblock = []
            edited_targetblock = []

            for link in links:
                sourceID = blockid.index(link['SourceID']['id']) + 1
                targetID = blockid.index(link['TargetID']['id']) + 1

                link['SourceID']['id'] = sourceID
                link['TargetID']['id'] = targetID

                sourceblock = blocks[sourceID-1]
                targetblock = blocks[targetID-1]

                if sourceblock['type'] == 'Variable':
                    sourcePort = ''
                else:
                    sourcePort = link['SourceID']['port']

                targetPort = link['TargetID']['port']

                sourcePoint = getsourcePoint(sourceblock, sourcePort)
                targetPoint = gettargetPoint(targetblock, targetPort)

                if sourceblock['type'] == 'step':
                    if sourceID in edited_sourceblock:
                        pass
                    edited_sourceblock.append(sourceID)
                    if sourceblock['modifier'] == 1:
                        blockinfo = {'type':sourceblock['type'],'name':sourceblock['name'],'id':sourceID,'x': sourceblock['position']['x'], 'y': sourceblock['position']['y'],'width': sourceblock['size']['width'], 'height': sourceblock['size']['height'], 'modifier': sourceblock['modifier'],'initial': True,'connectors': {'action': [],'inputs': [], 'outputs': [{"pos":[int(sourceblock['portPosition']['outPorts'][0]['out']['x']),int(sourceblock['portPosition']['outPorts'][0]['out']['y'])]}]}}
                        elements[str(sourceID)] = blockinfo
                
                if targetblock['type'] == 'step':
                    if targetID not in edited_targetblock:
                        edited_targetblock.append(targetID)
                        inPort = targetblock['portPosition']['inPorts'][0]
                        outPorts = targetblock['portPosition']['outPorts']
                        outputs = []
                        action = []
                        for port in outPorts:
                            for key, value in port.items():
                                if key == 'action':
                                    action.append({"pos":[int(value['x']),int(value['y'])]})
                                else:
                                    outputs.append({"pos":[int(value['x']),int(value['y'])]})
                        blockinfo = {'type':targetblock['type'],'name':targetblock['name'],'id':targetID,'x': targetblock['position']['x'], 'y': targetblock['position']['y'],'width': targetblock['size']['width'], 'height': targetblock['size']['height'], 'initial': False,'connectors': {'action': action,'inputs': [{"wire":[{"formalParameter":'',"points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[int(inPort['in']['x']),int(inPort['in']['y'])]}], 'outputs': outputs}}   
                        elements[str(targetID)] = blockinfo

                if targetblock['type'] == 'transition':
                    if targetID not in edited_targetblock:
                        edited_targetblock.append(targetID)
                        inPort = targetblock['portPosition']['inPorts'][0]
                        outPorts = targetblock['portPosition']['outPorts']
                        outputs = []
                        for port in outPorts:
                            for key, value in port.items():
                                outputs.append({"pos":[int(value['x']),int(value['y'])]})
                        
                        if targetblock['modifier'] == 0:
                            trans_type = 'inline'
                        blockinfo = {'_type':targetblock['type'],'type':trans_type,'condition':targetblock['name'],'id':targetID,'x': targetblock['position']['x'], 'y': targetblock['position']['y'],'width': targetblock['size']['width'], 'height': targetblock['size']['height'], 'connection': None,'priority':targetblock['executionOder'],'connectors': {'inputs': [{"wire":[{"formalParameter":'',"points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[int(inPort['in1']['x']),int(inPort['in1']['y'])]}], 'outputs': outputs}}
                        elements[str(targetID)] = blockinfo

                if targetblock['type'] == 'Variable' and targetblock['var_type'] == 'action':
                    if targetID not in edited_targetblock:
                        edited_targetblock.append(targetID)
                        action = []
                        action_qualifier = targetblock['name'].split('|')[0].strip()
                        action_value = targetblock['name'].split('|')[1]
                        action.append({"duration":"","indicator":"","type":"inline","qualifier":action_qualifier,"value":action_value})
                        inPort = targetblock['portPosition']['inPorts'][0]
                        blockinfo = {'type':"actionblock",'id':targetID,'x': targetblock['position']['x'], 'y': targetblock['position']['y'],'width': targetblock['size']['width'], 'height': targetblock['size']['height'],'action':action,'connectors': {"wire":[{"formalParameter":sourcePort,"points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[int(inPort['in']['x']),int(inPort['in']['y'])]}}
                        elements[str(targetID)] = blockinfo

                if targetblock['type'] == 'Variable' and targetblock['var_type'] == 'jump':
                    inPort = targetblock['portPosition']['inPorts'][0]
                    blockinfo = {'type':"jump",'id':targetID,'target':targetblock['name'],'x': targetblock['position']['x'], 'y': targetblock['position']['y'],'width': targetblock['size']['width'], 'height': targetblock['size']['height'],'connectors':{"wire":{"formalParameter":'',"points":[targetPoint,sourcePoint],"refLocalId":sourceID},"pos":[int(inPort['in']['x']),int(inPort['in']['y'])]}}
                    elements[str(targetID)] = blockinfo

            for ele in elements:
                if elements[ele]['type'] == 'step':
                    body['step'].append(elements[ele])
                elif elements[ele]['type'] == 'actionblock':
                    body['actionblock'].append(elements[ele])
                elif '_type' in elements[ele] and elements[ele]['_type'] == 'transition':
                    body['transition'].append(elements[ele])
                elif elements[ele]['type'] == 'jump':
                    body['jump'].append(elements[ele])

            tem_prog['body'] = body
            template_data['pou']['program'].append(tem_prog)


    for prog in front_data['pou']['functionBlock']:
        
        for var in prog['variable']:
            for key in var:
                if var[key] == '...':
                    var[key] = ''
        if prog['language'] == 'ST':
            tem_prog = {}
            tem_prog['name'] = prog['name']
            tem_prog['language'] = prog['language']
            tem_prog['type'] = prog['type']
            tem_prog['variable'] = prog['variable']
            tem_prog['body'] = prog['code']
            template_data['pou']['functionBlock'].append(tem_prog)
        elif prog['language'] == 'LD':
            tem_prog = {}
            tem_prog['name'] = prog['name']
            tem_prog['language'] = prog['language']
            tem_prog['type'] = prog['type']
            tem_prog['variable'] = prog['variable']

            # LeftRail_id, RightRail_id
            LeftRail_id = -1
            RightRail_id = -2
            # LeftRail_point, RightRail_point
            LeftRail_point = []
            RightRail_point = []
            
            # body
            body = {"comment":[], "powerrail":[], "coil":[], "contact":[], "block":[], "connection":[], "variable":[]}
            elements = {}
            code = prog['code']
            blocks = code['blocks']
            links = code['links']
            blockid = []
            for i in range(len(blocks)):
                blockid.append(blocks[i]['id'])
                blocks[i]['id'] = i + 1

            edited_block = []
            edited_sourceblock = []
            edited_targetblock = []
            for link in links:
                sourceID = blockid.index(link['SourceID']['id']) + 1
                targetID = blockid.index(link['TargetID']['id']) + 1
                sourcePort = link['SourceID']['port']
                targetPort = link['TargetID']['port']
                
                link['SourceID']['id'] = sourceID
                link['TargetID']['id'] = targetID

                sourceblock = blocks[sourceID-1]
                targetblock = blocks[targetID-1]

                sourcePoint = []
                sourcePoint.append(sourceblock['position']['x']+sourceblock['portPosition']['outPorts'][0]['out']['x'])
                sourcePoint.append(sourceblock['position']['y']+sourceblock['portPosition']['outPorts'][0]['out']['y'])
                targetPoint = []
                targetPoint.append(targetblock['position']['x']+targetblock['portPosition']['inPorts'][0]['in']['x'])
                targetPoint.append(targetblock['position']['y']+targetblock['portPosition']['inPorts'][0]['in']['y'])

                edited_inPort = []

                if sourceblock['type'] == 'LeftRail':
                    if LeftRail_id == -1:
                        LeftRail_id = sourceID
                        LeftRail_point = [sourceblock['position']['x'],sourceblock['position']['y']]
                        edited_sourceblock.append(sourceID)
                        blockinfo = {'class':sourceblock['type'],'id': sourceID, 'x': sourceblock['position']['x'], 'y': sourceblock['position']['y'],
                                        'width': sourceblock['size']['width'], 'height': sourceblock['size']['height'], 'type': 0,
                                        'connectors': {'inputs': [], 'outputs': [{"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']]}]}}
                        # body['powerrail'].append(blockinfo)
                        elements[str(sourceID)] = blockinfo
                    else:
                        sourceID = LeftRail_id
                        blockinfo=elements[str(LeftRail_id)]
                        blockinfo['height'] =  blockinfo['height'] + sourceblock['size']['height']
                        blockinfo['connectors']['outputs'].append({"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']+blockinfo['height']]})
                        sourcePoint = [LeftRail_point[0],LeftRail_point[1]+sourceblock['portPosition']['outPorts'][0]['out']['y']+blockinfo['height']]
                        

                if targetblock['type'] == 'RightRail':
                    edited_targetblock.append(targetID)
                    blockinfo = {'class':targetblock['type'], 'id': targetID, 'x': targetblock['position']['x'], 'y': targetblock['position']['y'],
                                    'width': targetblock['size']['width'], 'height': targetblock['size']['height'], 'type': 1,
                                    'connectors': {'inputs': [{"wire":[{"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[targetblock['portPosition']['inPorts'][0]['in']['x'],targetblock['portPosition']['inPorts'][0]['in']['y']]}], 'outputs': []}}
                    # body['powerrail'].append(blockinfo)
                    elements[str(targetID)] = blockinfo

                    # print(body)

                if sourceblock['type'] == 'Contact':
                    if sourceID in edited_sourceblock:
                        pass
                    edited_sourceblock.append(sourceID)
                    if sourceID not in edited_block:
                        edited_block.append(sourceID)
                        blockinfo = {'class':sourceblock['type'], 'id': sourceID, 'x': sourceblock['position']['x'], 'y': sourceblock['position']['y'],
                                        'width': sourceblock['size']['width'], 'height': sourceblock['size']['height'], 'modifier': sourceblock['modifier'], 'variable': sourceblock['name'],
                                        'connectors': {'inputs': [], 'outputs': [{"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']]}]}}
                    else:
                        # output donot care more than one
                        blockinfo = elements[str(sourceID)]
                        blockinfo['connectors']['outputs'].append({"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']]})
                    elements[str(sourceID)] = blockinfo

                if targetblock['type'] == 'Contact': 
                    
                    if targetID not in edited_block:
                        edited_block.append(targetID)
                        edited_targetblock.append(targetID)
                        blockinfo = {'class':targetblock['type'], 'id': targetID, 'x': targetblock['position']['x'], 'y': targetblock['position']['y'],
                                        'width': targetblock['size']['width'], 'height': targetblock['size']['height'], 'modifier': targetblock['modifier'], 'variable': targetblock['name'],
                                        'connectors': {'inputs': [{"wire":[{"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[targetblock['portPosition']['inPorts'][0]['in']['x'],targetblock['portPosition']['inPorts'][0]['in']['y']]}], 'outputs': []}}
                    elif targetID in edited_sourceblock and targetID not in edited_targetblock:
                        edited_targetblock.append(targetID)
                        blockinfo = elements[str(targetID)]
                        blockinfo['connectors']['inputs'].append({"wire":[{"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[targetblock['portPosition']['inPorts'][0]['in']['x'],targetblock['portPosition']['inPorts'][0]['in']['y']]})
                    elif targetID in edited_targetblock:
                        blockinfo = elements[str(targetID)]
                        blockinfo['connectors']['inputs'][0]['wire'].append({"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID})
                    elements[str(targetID)] = blockinfo

                if sourceblock['type'] == 'Coil':
                    if sourceID in edited_sourceblock:
                        pass
                    edited_sourceblock.append(sourceID)
                    if sourceID not in edited_block:
                        edited_block.append(sourceID)
                        blockinfo = {'class':sourceblock['type'], 'id': sourceID, 'x': sourceblock['position']['x'], 'y': sourceblock['position']['y'],
                                        'width': sourceblock['size']['width'], 'height': sourceblock['size']['height'], 'modifier': sourceblock['modifier'], 'variable': sourceblock['name'],
                                        'connectors': {'inputs': [], 'outputs': [{"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']]}]}}
                    else:
                        blockinfo = elements[str(sourceID)]
                        blockinfo['connectors']['outputs'].append({"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']]})

                    elements[str(sourceID)] = blockinfo

                if targetblock['type'] == 'Coil':
                    
                    if targetID not in edited_block:
                        edited_block.append(targetID)
                        edited_targetblock.append(targetID)
                        blockinfo = {'class':targetblock['type'], 'id': targetID, 'x': targetblock['position']['x'], 'y': targetblock['position']['y'],
                                        'width': targetblock['size']['width'], 'height': targetblock['size']['height'], 'modifier': targetblock['modifier'], 'variable': targetblock['name'],
                                        'connectors': {'inputs': [{"wire":[{"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[targetblock['portPosition']['inPorts'][0]['in']['x'],targetblock['portPosition']['inPorts'][0]['in']['y']]}], 'outputs': []}}
                    elif targetID in edited_sourceblock and targetID not in edited_targetblock:
                        edited_targetblock.append(targetID)
                        blockinfo = elements[str(targetID)]

                        blockinfo['connectors']['inputs'].append({"wire":[{"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[targetblock['portPosition']['inPorts'][0]['in']['x'],targetblock['portPosition']['inPorts'][0]['in']['y']]})
                    elif targetID in edited_targetblock:
                        blockinfo = elements[str(targetID)]
                        blockinfo['connectors']['inputs'][0]['wire'].append({"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID})
                    elements[str(targetID)] = blockinfo

            for element in elements:
                if elements[element]['class'] == 'LeftRail' or elements[element]['class'] == 'RightRail':
                    body['powerrail'].append(elements[element])

                elif elements[element]['class'] == 'Coil':
                    body['coil'].append(elements[element])
                elif elements[element]['class'] == 'Contact':
                    body['contact'].append(elements[element])

            tem_prog['body'] = body

            template_data['pou']['functionBlock'].append(tem_prog)
    
    # for prog in front_data['pou']['libFB']:
    #     for var in prog['variable']:
    #         for key in var:
    #             if var[key] == '...':
    #                 var[key] = ''
    #     if prog['language'] == 'ST':
    #         tem_prog = {}
    #         tem_prog['name'] = prog['name']
    #         tem_prog['language'] = prog['language']
    #         tem_prog['type'] = prog['type']
    #         tem_prog['variable'] = prog['variable']
    #         tem_prog['body'] = prog['code']
    #         template_data['pou']['libFB'].append(tem_prog)

    OT_data = template_data
    return OT_data
