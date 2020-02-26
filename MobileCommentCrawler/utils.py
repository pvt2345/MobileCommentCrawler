def InsertToMongoComment(document, database, collection):
    MyClient = MongoClient('mongodb://localhost:27017/')
    MyDb = MyClient[database]
    MyCol = MyDb[collection]
