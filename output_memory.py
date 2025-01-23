from sqlite import Database
import json

START_ID = 22
END_ID = 519
database = Database()

def output_memory():
    data = database.get_history()
    memory = []
    for i in range(START_ID, len(data)):
        memory.append({'Prompt':data[i][4], 'Respond':data[i][5], 'History':[]})
    end_id = len(data) - 1
    with open(f'logs/memory_{START_ID}-{end_id}.json', 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=4)

def input_dataset():
    with open(f'logs/memory_{START_ID}-{END_ID}.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    with open('D:/Muice-Development/dataset/train.jsonl','a',encoding='utf-8') as f:
        for i in data:
            if 'History' in i.keys():
                json.dump({'Prompt':i["Prompt"],'Response':i['Respond'], 'History':i['History']},f,ensure_ascii=False)
            else:
                json.dump({'Prompt':i["Prompt"],'Response':i['Respond'], 'History':[]},f,ensure_ascii=False)
            f.write('\n')

if __name__ == '__main__':
    input_dataset()
    print('Memory output successfully!')