from sqlite import Database
import json

START_ID = 1248
END_ID = 1576
database = Database()

def output_memory():
    data = database.get_history()
    memory = []
    for i in range(START_ID, len(data)):
        memory.append({'Prompt':data[i][4], 'Respond':data[i][5].strip(' '), 'History':[]})
    with open(f'temp/memory_{START_ID}-{END_ID}.json', 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=4)
    print('Memory output successfully!')

def input_dataset():
    count = 0
    with open(f'temp/memory_{START_ID}-{END_ID}.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    with open('D:/Muice-Development/dataset/train.jsonl','a',encoding='utf-8') as f:
        for i in data:
            if i['Respond'] == "":
                continue
            count += 1
            if 'History' in i.keys():
                json.dump({'Prompt':i["Prompt"],'Response':i['Respond'], 'History':i['History']},f,ensure_ascii=False)
            else:
                json.dump({'Prompt':i["Prompt"],'Response':i['Respond'], 'History':[]},f,ensure_ascii=False)
            f.write('\n')
    print(f'Input {count} memory from living data.')

if __name__ == '__main__':
    input_dataset()
