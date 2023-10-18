import json
from pymongo import MongoClient

####################### SourcePool #######################
# load data from json file or database

# init database
def init_db(client_name):
    client = MongoClient('localhost', 27017)
    db = client[client_name]
    source_collection = db['source']
    return source_collection


# load data from json file
def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = [json.loads(line) for line in f.readlines()]
    return data


# Read data from json file or database
class SourcePool:
    def __init__(self, source_file_path=None, db_collection=None):
        self.source_file_path = source_file_path
        self.db_collection = db_collection
        self.source_data = []
        self.source_collection = None
        self.load_data()


    def load_data(self):
        if self.source_file_path:
            self.source_data = read_json_file(self.source_file_path)
        elif self.db_collection:
            self.source_collection = init_db(self.db_collection)
            self.source_data = self.source_collection.find()
        else:
            raise Exception('No data source')
    

    # get all source_data
    def get_source_data(self):
        return self.source_data
    
    # get source collection
    def get_source_collection(self):
        return self.source_collection
    
    # write source_data to json file
    def write_source_file(self, data, pre_load=False):
        with open(self.source_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
        if not pre_load:
            self.load_data()
    
    # write source_data to database
    def write_query_web_db(self, data):
        self.get_source_collection.insert_one(data)
        self.load_data()



# if __name__ == '__main__':
#     # test
#     source_pool = SourcePool(db_collection='KW2G')
#     collection = source_pool.get_source_collection()
#     for item in collection.find({'$text': {'$search': 'exercise'}}).sort([('query', 1)]).limit(2):
#         print(item)