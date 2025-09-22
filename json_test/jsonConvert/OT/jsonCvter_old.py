import json
TEMPLATE_DATA = {"pou": {"program": [],"function":[],"functionBlock":[]}, "config": {},"contentHeader": "LD_Language"}

def OTdataCvter(front_data, template_data):
    template_data['config'] = front_data['config']
    template_data['contentHeader'] = front_data['contentHeader']

    for prog in front_data['pou']['program']:
        if prog['language'] == 'ST':
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
                    edited_sourceblock.append(sourceID)
                    blockinfo = {'class':sourceblock['type'],'id': sourceID, 'x': sourceblock['position']['x'], 'y': sourceblock['position']['y'],
                                    'width': sourceblock['size']['width'], 'height': sourceblock['size']['height'], 'type': 0,
                                    'connectors': {'inputs': [], 'outputs': [{"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']]}]}}
                    # body['powerrail'].append(blockinfo)
                    elements[str(sourceID)] = blockinfo

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
                    if sourceID not in edited_targetblock:
                        blockinfo = {'class':sourceblock['type'], 'id': sourceID, 'x': sourceblock['position']['x'], 'y': sourceblock['position']['y'],
                                        'width': sourceblock['size']['width'], 'height': sourceblock['size']['height'], 'modifier': 0, 'variable': sourceblock['name'],
                                        'connectors': {'inputs': [], 'outputs': [{"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']]}]}}
                    else:
                        blockinfo = elements[str(sourceID)]
                        blockinfo['connectors']['outputs'].append({"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']]})
                    elements[str(sourceID)] = blockinfo

                if targetblock['type'] == 'Contact':  
                    if targetID not in edited_sourceblock and targetID not in edited_targetblock:
                        edited_targetblock.append(targetID)
                        blockinfo = {'class':targetblock['type'], 'id': targetID, 'x': targetblock['position']['x'], 'y': targetblock['position']['y'],
                                        'width': targetblock['size']['width'], 'height': targetblock['size']['height'], 'modifier': 0, 'variable': targetblock['name'],
                                        'connectors': {'inputs': [{"wire":[{"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[targetblock['portPosition']['inPorts'][0]['in']['x'],targetblock['portPosition']['inPorts'][0]['in']['y']]}], 'outputs': []}}
                    else:
                        blockinfo = elements[str(targetID)]
                        blockinfo['connectors']['inputs'].append({"wire":[{"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[targetblock['portPosition']['inPorts'][0]['in']['x'],targetblock['portPosition']['inPorts'][0]['in']['y']]})
                    elements[str(targetID)] = blockinfo

                if sourceblock['type'] == 'Coil':
                    if sourceID in edited_sourceblock:
                        pass
                    edited_sourceblock.append(sourceID)
                    if sourceID not in edited_targetblock:
                        blockinfo = {'class':sourceblock['type'], 'id': sourceID, 'x': sourceblock['position']['x'], 'y': sourceblock['position']['y'],
                                        'width': sourceblock['size']['width'], 'height': sourceblock['size']['height'], 'modifier': 0, 'variable': sourceblock['name'],
                                        'connectors': {'inputs': [], 'outputs': [{"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']]}]}}
                    else:
                        blockinfo = elements[str(sourceID)]
                        blockinfo['connectors']['outputs'].append({"pos":[sourceblock['portPosition']['outPorts'][0]['out']['x'],sourceblock['portPosition']['outPorts'][0]['out']['y']]})

                    elements[str(sourceID)] = blockinfo

                if targetblock['type'] == 'Coil':
                    edited_targetblock.append(targetID)
                    if targetID not in edited_sourceblock:
                        blockinfo = {'class':targetblock['type'], 'id': targetID, 'x': targetblock['position']['x'], 'y': targetblock['position']['y'],
                                        'width': targetblock['size']['width'], 'height': targetblock['size']['height'], 'modifier': 0, 'variable': targetblock['name'],
                                        'connectors': {'inputs': [{"wire":[{"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[targetblock['portPosition']['inPorts'][0]['in']['x'],targetblock['portPosition']['inPorts'][0]['in']['y']]}], 'outputs': []}}
                    else:
                        blockinfo = elements[str(targetID)]
                        blockinfo['connectors']['inputs'].append({"wire":[{"formalParameter":"","points":[targetPoint,sourcePoint],"refLocalId":sourceID}],"pos":[targetblock['portPosition']['inPorts'][0]['in']['x'],targetblock['portPosition']['inPorts'][0]['in']['y']]})
                    elements[str(targetID)] = blockinfo

                print(elements)

            for element in elements:
                if elements[element]['class'] == 'LeftRail' or elements[element]['class'] == 'RightRail':
                    body['powerrail'].append(elements[element])

                elif elements[element]['class'] == 'Coil':
                    body['coil'].append(elements[element])
                elif elements[element]['class'] == 'Contact':
                    body['contact'].append(elements[element])

            tem_prog['body'] = body

            template_data['pou']['program'].append(tem_prog)

    OT_data = template_data

    return OT_data