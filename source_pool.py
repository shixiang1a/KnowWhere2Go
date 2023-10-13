import json
from pymongo import MongoClient

####################### 资源池 #######################

# 资源池类，能够从json文件中读取资源，也能够从数据库中读取资源

## 数据存储格式 ##
# query_web [dict]: {'query': 'xxx', 'web-urls': [{'web': 'xxx', 'url': 'xxx', 'evidence': 'xxx'}, ...], , 'auto_check': 'xxx', 'manual_check': 'xxx'}
# web_url [dict]: {'web': 'xxx', 'url': 'xxx', 'auto_check': 'xxx', 'manual_check': 'xxx'}


# 初始化数据库
# Collection: query_web, web_url
def init_db(client_name):
    client = MongoClient('localhost', 27017)
    db = client[client_name]
    query_web_collection = db['query_web']
    web_url_collection = db['web_url']
    return query_web_collection, web_url_collection


# 读取json文件
def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = [json.loads(line) for line in f.readlines()]
    return data


# 资源池类，能够从json文件中读取资源，也能够从数据库中读取资源
class ResourcePool:
    def __init__(self, query_web_file_path=None, web_url_file_path=None, db_collection=None):
        self.query_web_file_path = query_web_file_path
        self.web_url_file_path = web_url_file_path
        self.db_collection = db_collection
        self.query_web_data = []
        self.web_url_data = []
        self.query_web_collection = None
        self.web_url_collection = None
        self.load_data()


    def load_data(self):
        if self.query_web_file_path and self.web_url_file_path:
            self.query_web_data = read_json_file(self.query_web_file_path)
            self.web_url_data = read_json_file(self.web_url_file_path)
        elif self.query_web_file_path:
            self.query_web_data = read_json_file(self.query_web_file_path)
        elif self.db_collection:
            query_web_collection, web_url_collection = init_db(self.db_collection)
            self.query_web_collection = query_web_collection
            self.web_url_collection = web_url_collection
            self.query_web_data = self.query_web_collection.find()
            self.web_url_data = self.web_url_collection.find()
        else:
            raise Exception('No data source')
    

    # 获取所有的query_web数据
    def get_query_web_data(self):
        return self.query_web_data
    
    # 获取query_web collection
    def get_query_web_collection(self):
        return self.query_web_collection
        

    # 获取所有的web_url数据
    def get_web_url_data(self):
        return self.web_url_data
    
    # 向query_web_file Json文件中补充写入数据，并更新资源池
    def write_query_web_file(self, data):
        with open(self.query_web_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
        # self.load_data()
    
    # 向web_url_file Json文件中补充写入数据，并更新资源池
    def write_web_url_file(self, data):
        with open(self.web_url_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
        self.load_data()
    
    # 向数据库中补充写入query_web数据，并更新资源池
    def write_query_web_db(self, data):
        self.query_web_collection.insert_one(data)
        self.load_data()
    
    # 向数据库中补充写入web_url数据，并更新资源池
    def write_web_url_db(self, data):
        self.web_url_collection.insert_one(data)
        self.load_data()



if __name__ == '__main__':
    # 测试

    # 测试读取json文件
    # query_web_file_path = os.path.join(os.path.dirname(__file__), 'data/query_web.json')
    # web_url_file_path = os.path.join(os.path.dirname(__file__), 'data/web_url.json')
    # source_pool = ResourcePool(query_web_file_path, web_url_file_path)
    # source_pool.load_data()
    # print(source_pool.get_query_web_data())

    # 测试读取数据库
    source_pool = ResourcePool(db_collection='KW2G')
    # 插入数据
    # source_pool.write_query_web_db({'query': 'the capital of China', 'web-urls': [{'web': 'xxx', 'url': 'xxx', 'evidence': 'xxx'}]})
    # 删除数据
    # source_pool.query_web_collection.delete_one({'query': 'China ia a great country', 'web-urls': [{'web': 'xxx', 'url': 'xxx', 'evidence': 'xxx'}]})
    # print(len(list(source_pool.get_query_web_data())))
    # 使用query字段建立索引
    # source_pool.query_web_collection.create_index([('query', 'text')])
    collection = source_pool.get_query_web_collection()
    # 使用索引模糊查询“中国”
    for item in collection.find({'$text': {'$search': 'exercise'}}).sort([('query', 1)]).limit(2):
        print(item)