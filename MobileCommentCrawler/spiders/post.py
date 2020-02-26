from scrapy import Selector, Request
from scrapy.spiders import CrawlSpider
import re
from scrapy_splash import SplashRequest
import time
import requests
import json
import pymongo

def InsertToMongo(document, database, collection):
    MyClient = pymongo.MongoClient('mongodb://localhost:27017/')
    MyDb = MyClient[database]
    MyCol = MyDb[collection]

    if MyCol.find_one({'comment_id' : document['comment_id']}) is None:
        MyCol.insert_one(document)



class tikipost(CrawlSpider):
    name= 'tikipost'

    wait_script = """
    function main(splash, args)
    assert(splash:go(args.url))
    assert(splash:wait(0.5))
    return {
      html = splash:html(),
      png = splash:png(),
      har = splash:har(),
      cookies = splash:get_cookies(),
    }
  end
    """

    def __init__(self, id=None, url=None, *args, **kwargs):
        super(tikipost, self).__init__(*args, **kwargs)
        if id is not None:
            self.start_urls = ['https://tiki.vn/api/v2/reviews?product_id={}&limit=1000'.format(id)]
        elif url is not None:
            product_id = re.findall('p\d+', url)[0]
            self.start_urls = ['https://tiki.vn/api/v2/reviews?product_id={}&limit=1000'.format(product_id[1:])]

    def start_requests(self):
        for url in self.start_urls:
            yield SplashRequest(url=url, args={'lua_source' : self.wait_script}, callback=self.parse_first, endpoint='execute')

    def parse_first(self, response):
        data_get = json.loads(response.css('pre::text').extract_first())

        for item in data_get['data']:
            _data = {}
            _data['content'] = item['content']
            _data['customer_id'] = item['customer_id']
            _data['user_name'] = item['created_by']['name']
            _data['stars'] = item['rating']
            _data['comment_id'] = item['id']
            InsertToMongo(_data, 'reviews', 'tiki')
            yield _data


class shopeepost(CrawlSpider):
    
    name = 'shopeepost'

    wait_script = """
    function main(splash, args)
    assert(splash:go(args.url))
    assert(splash:wait(0.5))
    return {
      html = splash:html(),
      png = splash:png(),
      har = splash:har(),
      cookies = splash:get_cookies(),
    }
  end
    """

    offset = 0

    def __init__(self, shop_id=None, url=None, item_id=None, *args, **kwargs):
        super(shopeepost, self).__init__(*args, **kwargs)
        if url is not None:
            id_string = re.findall('i.\d+.\d+', url)[0].split('.')
            item_id = id_string[2]
            shop_id = id_string[1]
            self.start_urls = ['https://shopee.vn/api/v2/item/get_ratings?&itemid={}&limit=6&offset=0&shopid={}'.format(item_id, shop_id)]

        elif shop_id is not None and item_id is not None:
            self.start_urls = ['https://shopee.vn/api/v2/item/get_ratings?&itemid={}&limit=6&offset=0&shopid={}'.format(item_id, shop_id)]

    def start_requests(self):
        for url in self.start_urls:
            request = SplashRequest(url=url, args={'lua_source' : self.wait_script}, callback=self.parse_first, endpoint='execute')
            yield request

    def parse_first(self, response):
        data_get = json.loads(response.css('pre::text').extract_first())
        ratings = data_get['data']['ratings']


        if len(ratings) > 0:
            for item in ratings:
                if item['comment'] != '' and item['comment'] is not None: 
                    _data = {}
                    _data['comment_id'] = item['cmtid']
                    _data['content'] = item['comment']
                    _data['user_id'] = item['userid']
                    _data['user_name'] = item['author_username']
                    _data['stars'] = item['rating_star']
                    _data['item_id'] = item['itemid']
                    _data['shop_id'] = item['shopid']
                    InsertToMongo(_data, 'reviews', 'shopee')
                    yield _data

            self.offset += 6
            yield SplashRequest(url= re.sub('offset=\d+', 'offset={}'.format(self.offset), response.url), callback=self.parse_first, endpoint='execute', args={'lua_source' : self.wait_script})

class lazadapost(CrawlSpider):

    name = 'lazadapost'

    wait_script = """
    function main(splash, args)
    assert(splash:go(args.url))
    assert(splash:wait(0.5))
    return {
      html = splash:html(),
      png = splash:png(),
      har = splash:har(),
      cookies = splash:get_cookies(),
    }
    end
    """

    page_num = 1

    def __init__(self, url=None, item_id=None, *args, **kwargs):
        super(lazadapost, self).__init__(*args, **kwargs)
        if url is not None:
            item_id = re.findall('i\d+', url)[0][1:]
            self.start_urls = ['https://my.lazada.vn/pdp/review/getReviewList?itemId={}&pageSize=5&filter=0&sort=0&pageNo=1'.format(item_id)]

        elif item_id is not None:
            self.start_urls = ['https://my.lazada.vn/pdp/review/getReviewList?itemId={}&pageSize=5&filter=0&sort=0&pageNo=1'.format(item_id)]            

    def start_requests(self):
        for url in self.start_urls:
            request = SplashRequest(url=url, args={'lua_source' : self.wait_script}, callback=self.parse_first, endpoint='execute')
            yield request

    def parse_first(self, response):
        data_get = json.loads(response.css('pre::text').extract_first())
        
        items = data_get['model']['items']
        if items is not None:
            for item in items:
                # try:
                if item['reviewContent'] is not None:
                    _data = {}
                    _data['content'] = item['reviewContent']
                    _data['stars'] = item['rating']
                    _data['user_name'] = item['buyerName']
                    _data['user_id'] = item['buyerId']
                    _data['comment_id'] = item['reviewRateId']
                    InsertToMongo(_data, 'reviews', 'lazada')
                    yield _data

            self.page_num += 1
            yield SplashRequest(url= re.sub('pageNo=\d+', 'pageNo={}'.format(self.page_num), response.url), args={'lua_source' : self.wait_script}, callback=self.parse_first, endpoint='execute')
