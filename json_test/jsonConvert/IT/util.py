import os
import json

def ITdataCvter(front_data):
    blocks = front_data['blocks']
    links = front_data['links']
    elements = {}
    blockid = []
    for i in range(len(blocks)):
        blockid.append(blocks[i]['id'])
        blocks[i]['id'] = i

    for block in blocks:
        if block['type'] == 'Camera':
            elements[block['id']] = {'name':block['name'],'type': block['type'], 'id': block['id'], 'modifier': block['modifier'], 'camera': block['camera']}
        elif block['type'] == 'Program':
            elements[block['id']] = {'name':block['name'],'type': block['type'], 'id': block['id'], 'modifier': block['modifier'], 'proData': block['proData']}
        elif block['type'] == 'Data':
            elements[block['id']] = {'name':block['name'],'type': block['type'], 'id': block['id'], 'modifier': block['modifier'], 'DataFlag': block['DataFlag']}
        else:
            elements[block['id']] = {'name':block['name'],'type': block['type'], 'id': block['id'], 'modifier': block['modifier']}
        inputID = []
        outputID = []
        for link in links:
            sourceID = blockid.index(link['SourceID']['id'])
            targetID = blockid.index(link['TargetID']['id'])
            if sourceID == block['id']:
                # 
                outputID.append({'id': targetID, 'port': link['SourceID']['port']})
            if targetID == block['id']:
                # 
                inputID.append({'id': sourceID, 'port': link['SourceID']['port']})

        elements[block['id']]['input'] = inputID
        elements[block['id']]['output'] = outputID
    return elements


# current_path = os.path.dirname(__file__)
# filename = 'ydsitdata_project.json'
# output_path = os.path.join(current_path, "ydsitdata_output.json")
# json_path = "E:\Graduation_project\Code\json2xml\ITdata\\" + filename
# with open(json_path, 'r') as f:
#     front_data = json.load(f)
#     front_data = front_data['IT']
#     elements = ITdataCvter(front_data[0]['IT_code'])
#     with open(output_path, 'w') as f:
#         json.dump(elements, f, indent=4)
#     print(elements)