from scrapy import Selector, Request
from scrapy.spiders import CrawlSpider
import re
from scrapy_splash import SplashRequest
import time
import requests
import json
import pymongo
import selenium


def InsertToMongo(document, database, collection):
    MyClient = pymongo.MongoClient('mongodb://localhost:27017/')
    MyDb = MyClient[database]
    MyCol = MyDb[collection]

    if MyCol.find_one({'comment_id' : document['comment_id']}) is None:
        MyCol.insert_one(document)

wait_script = """
function main(splash, args)
  assert(splash:go(args.url))
  assert(splash:wait(5))
  return {
    html = splash:html(),
    cookies = splash:get_cookies()
  }
end
"""

wait_script_2 = """
function main(splash, args)
  assert(splash:go(args.url))
  assert(splash:wait(2))
  return {
    html = splash:html(),
    cookies = splash:get_cookies()
  }
end
"""

get_comment_script_tiki = """
function main(splash, args)
  assert(splash:go(args.url))
  assert(splash:wait(0.5))
  comment_element = splash:select('ul#dpr_listing')
  next_page_element = splash:select('a.nav.next')
  return_html = splash:select('div#header_navigate_breadcrumb').node.innerHTML .. comment_element.innerHTML
  while (next_page_element ~= nil)
  do
    next_page_element:click()
    assert(splash:wait(0.5))
    return_html = return_html .. splash:select('ul#dpr_listing').node.innerHTML
    next_page_element = splash:select('a.nav.next')
  end
  return {
    html = return_html,
    cookies = splash:get_cookies()
  }
end
"""

get_comment_script_lazada = """
function main(splash, args)
  assert(splash:go(args.url))
  assert(splash:wait(2))
  comment_element = splash:select('div.mod-reviews')
  btn_list = splash:select_all('div.pdp-mod-review button.next-btn')
  next_page_element = btn_list[#btn_list]
  return_html = splash:select('div.pdp-mod-product-badge-wrapper').node.innerHTML .. comment_element.innerHTML
  while (not next_page_element:hasAttribute('disabled'))
  do
    next_page_element:click()
    assert(splash:wait(0.5))
    return_html = return_html .. splash:select('div.mod-reviews').node.innerHTML
    btn_list = splash:select_all('div.pdp-mod-review button.next-btn')
	next_page_element = btn_list[#btn_list]
  end
  return {
    html = return_html,
    cookies = splash:get_cookies()
  }
end
"""

wait_script_shopee = """
    function main(splash, args)
      local scroll_to = splash:jsfunc("window.scrollTo")
      local get_third_body_height = splash:jsfunc(
        "function() {return document.body.scrollHeight/4;}"
      )
      assert(splash:go(args.url))
      assert(splash:wait(2))
      for _ = 1, 4 do
        scroll_to(0, get_third_body_height()*_)
        assert(splash:wait(0.5))
      end
      return {
        html = splash:html(),
        cookies = splash:get_cookies(),
        png = splash:png()
      }
    end
    """

wait_script_2_shopee = """
    function main(splash, args)
      local scroll_to = splash:jsfunc("window.scrollTo")
      local get_third_body_height = splash:jsfunc(
        "function() {return document.body.scrollHeight/4;}"
      )
      assert(splash:go(args.url))
      assert(splash:wait(0.5))
      for _ = 1, 4 do
        scroll_to(0, get_third_body_height()*_)
        assert(splash:wait(0.5))
      end
      return {
        html = splash:html(),
        cookies = splash:get_cookies(),
        png = splash:png()
      }
    end
    """

get_comment_script_shopee = """
    function main(splash, args)
      assert(splash:go(args.url))
      assert(splash:wait(5))
      danh_gia_button = splash:select_all('div.flex.M3KjhJ')[2]
      danh_gia_button:mouse_click()
      assert(splash:wait(3))
      co_binh_luan_button = splash:select('div.product-rating-overview__filter--with-comment')
      co_binh_luan_button:mouse_click()
      assert(splash:wait(2))
        return_html = splash:select('div.qaNIZv').node.outerHTML .. splash:select('div.shopee-product-comment-list').node.innerHTML
      co_binh_luan_text = co_binh_luan_button:text()
        so_binh_luan = tonumber(co_binh_luan_text:sub(-4, -2))
      if so_binh_luan == nil then
        so_binh_luan = tonumber(co_binh_luan_text:sub(-3, -2))
      end
      if so_binh_luan == nil then
        so_binh_luan = tonumber(co_binh_luan_text:sub(-2, -2))
      end
      num_page = math.floor(so_binh_luan/6)
      if num_page > 0 then
        for i = 1, num_page do
          next_page_button = splash:select('button.shopee-icon-button--right')
          next_page_button:mouse_click()
          assert(splash:wait(2))
          return_html = return_html .. splash:select('div.shopee-product-comment-list').node.innerHTML
        end
      end

      return {
        html = return_html,
        cookies = splash:get_cookies()
      }
    end
    """

class tiki(CrawlSpider):
    name = 'tiki'

    custom_settings = {

        "DOWNLOAD_DELAY" : 2

    }
    get_link_scripts = """
    function main(splash, args)
      assert(splash:go(args.url))
      assert(splash:wait(1.5))
      return {
        html = splash:html(),
        cookies = splash:get_cookies()
      }
    end
    """

    def __init__(self, url='', start_page='1', end_page='1', *args, **kwargs):
        super(tiki, self).__init__(*args, **kwargs)
        for i in range(int(start_page), int(end_page)  + 1):
            self.start_urls.append(url + '&page={}'.format(i))

        print(type(start_page))
        print(type(end_page))


    def start_requests(self):
        for url in self.start_urls:
            yield SplashRequest(url = url, callback=self.parse_first, endpoint='execute', args={'lua_source' : self.get_link_scripts})

    def parse_first(self, response):
        data_ids = response.css('a::attr(data-id)').extract()
        for item in data_ids:
            yield SplashRequest(url='https://tiki.vn/api/v2/reviews?product_id={}&limit=1000'.format(item), callback=self.parse_item, endpoint='execute', args={'lua_source' : self.get_link_scripts})

    def parse_item(self, response):
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


class shopee(CrawlSpider):
    name = 'shopee'

    get_link_scripts = """
    function main(splash, args)
      splash:set_viewport_full()
      local scroll_to = splash:jsfunc("window.scrollTo")
      local get_third_body_height = splash:jsfunc(
        "function() {return document.body.scrollHeight/4;}"
      )
      assert(splash:go(args.url))
      assert(splash:wait(2))
      for _ = 1, 4 do
        scroll_to(0, get_third_body_height()*_)
        assert(splash:wait(1))
      end
      return {
        html = splash:html(),
        cookies = splash:get_cookies(),
        png = splash:png()
      }
    end
    """

    custom_settings = {
        'DOWNLOAD_DELAY' : 3
    }

    wait_script = """
    function main(splash, args)
      assert(splash:go(args.url))
      assert(splash:wait(1.5))
      return {
        html = splash:html(),
        cookies = splash:get_cookies()
      }
    end
    """

    def __init__(self, url='', start_page='1', end_page='1', *args, **kwargs):
        super(shopee, self).__init__(*args, **kwargs)
        for i in range(int(start_page) - 1, int(end_page)):
            self.start_urls.append(url + '&page={}'.format(int(i)))


    def start_requests(self):
        for url in self.start_urls:
            yield SplashRequest(url=url, callback=self.parse_first, endpoint='execute',
                                args={'lua_source': self.get_link_scripts})

    def parse_first(self, response):
        print(response.body)
        urls = response.css('a[data-sqe="link"]::attr(href)').extract()
        crawl_urls = []
        print(urls)
        for item in urls:
            # print(item)
            id_string = re.findall('i.\d+.\d+', item)[-1].split('.')
            # print(id_string)
            item_id = id_string[2]
            shop_id = id_string[1]
            crawl_urls.append('https://shopee.vn/api/v2/item/get_ratings?&itemid={}&limit=59&offset=0&shopid={}'.format(item_id, shop_id))
        # print(crawl_urls)
        for item in crawl_urls:
            request = SplashRequest(url=item, callback=self.parse_item, endpoint='execute',
                          args={'lua_source': self.get_link_scripts})
            request.meta['offset'] = 0
            yield request

    def parse_item(self, response):
        data_get = json.loads(response.css('pre::text').extract_first())
        ratings = data_get['data']['ratings']
        print('len ratings: ', len(ratings))
        offset = response.meta['offset']
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

            # if len(ratings) == 59:
            offset += 59
            request = SplashRequest(url=re.sub('offset=\d+', 'offset={}'.format(offset), response.url),
                                callback=self.parse_item, endpoint='execute', args={'lua_source': self.wait_script})
            request.meta['offset'] = offset
            yield request

class lazada(CrawlSpider):

    name = 'lazada'

    wait_script = """
    function main(splash, args)
      assert(splash:go(args.url))
      assert(splash:wait(1))
      return {
        html = splash:html(),
        cookies = splash:get_cookies()
      }
    end
    """

    custom_settings = {
        'DOWNLOAD_DELAY': 5,
        'COOKIES_ENABLED' : False
    }

    def __init__(self, url='', start_page=1, end_page=1, *args, **kwargs):
        super(lazada, self).__init__(*args, **kwargs)

        parts = url.split('/')
        if parts[-1] != '':
            for i in range(start_page, end_page + 1):
                self.start_urls.append(url + '&ajax=true&page={}'.format(i))
        else:
            for i in range(start_page, end_page + 1):
                self.start_urls.append(url + '?ajax=true&page={}'.format(i))

    def start_requests(self):
        for url in self.start_urls:
            # print(url)
            yield SplashRequest(url=url, callback=self.parse_first, endpoint='execute', args={'lua_source' : self.wait_script})

    def parse_first(self, response):
        # for item in response.css('div.c2prKC'):
        #     if item.css('div.c2JB4x.c6Ntq9') is not None:
        #         url = item.css('div.c16H9d a[age="0"]::attr(href)').extract_first()
        #         item_id = re.findall('i\d+', url)[0][1:]
        
        # print(response.body)
        # urls = response.css('div.c16H9d a[age="0"]::attr(href)').extract()
        # print(urls)
        # print(len(urls))
        data_get = json.loads(response.css('pre::text').extract_first())
        urls = []
        for item in data_get['mods']['listItems']:
            urls.append('https://my.lazada.vn/pdp/review/getReviewList?itemId={}&pageSize=1000&filter=0&sort=0&pageNo=1'.format(item['itemId']))

        print(urls)
        for url in urls:
            yield SplashRequest(url=url, args={'lua_source' : self.wait_script}, endpoint='execute', callback=self.parse_item)
    
    def parse_item(self, response):
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
                    # InsertToMongo(_data, 'reviews', 'lazada')
                    yield _data    

        

    def parse_item(self, response):
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

            # self.page_num += 1
            # yield SplashRequest(url= re.sub('pageNo=\d+', 'pageNo={}'.format(self.page_num), response.url), args={'lua_source' : self.wait_script}, callback=self.parse_first, endpoint='execute')



class vatgia(CrawlSpider):
    name = 'vatgia'
    # urls = []
    domain = 'https://vatgia.com'
    index = 1
    start_urls = ["https://vatgia.com/home/listudv.php?iCat=438&p10=4"]

    def start_requests(self):
        for url in self.start_urls:
            yield SplashRequest(args={'lua_source' : wait_script}, url=url, callback=self.parse_first, endpoint='execute')

    def parse_first(self, response):
        for item in response.css("#type_product_list_udv div.wrapper"):
            if (len(item.css("div.group_rating_order")) != 0):
                next_link = item.css("a.picture_link::attr(href)").extract_first()
                next_link_split = next_link.split('/')
                url = self.domain + '/' + next_link_split[1] + '/' + next_link_split[2] + '/' + 'binh_chon_new' + '/' + next_link_split[3]
                yield SplashRequest(args={'lua_source' : get_comment_script_tiki}, url=url, callback=self.parse_item, endpoint='execute')


        if (self.index < 50):
            self.index += 1
            yield SplashRequest(args={'lua_source': wait_script_2}, url="https://vatgia.com/home/listudv.php?iCat=438&p10=4&page={}".format(self.index), callback=self.parse_first, endpoint='execute')


    def parse_item(self, response):
        data = {}
        data['url'] = response.url
        data['name'] = response.css('div.container_width b::text').extract_first()
        data['comments'] = []
        # cmt_list = response.css('ul#dpr_listing li')
        cmt_list = response.css('li')
        for item in cmt_list:
            star_and_comment = item.css('div.dpr_content span')
            if len(star_and_comment) == 2:
                stars = len(star_and_comment[0].css('i.icm.icm_star-full2.active'))
                comment = star_and_comment[1].css('::text').extract_first()
                data['comments'].append({'stars': stars, 'comment': comment})

        yield data




# class lazada(CrawlSpider):
#     name = 'lazada'
#     index = 1
#     start_urls = ['https://www.lazada.vn/dien-thoai-di-dong/?page=1&spm=a2o4n.home.cate_1.1.51a26afeb9omAJ']

#     wait_script = """
#     function main(splash, args)
#     assert(splash:go(args.url))
#     assert(splash:wait(0.5))
#     return {
#       html = splash:html(),
#       png = splash:png(),
#       har = splash:har(),
#       cookies = splash:get_cookies(),
#     }
#     end
#     """

#     def start_requests(self):
#         for url in self.start_urls:
#             yield SplashRequest(url = url, callback=self.parse_first, endpoint='execute', args={'lua_source' : wait_script})

#     def parse_first(self, response):
#         for item in response.css('div.c2prKC'):
#             if item.css('div.c2JB4x.c6Ntq9') is not None:
#                 url = item.css('div.c16H9d a[age="0"]::attr(href)').extract_first()
#                 item_id = re.findall('i\d+', url)[0][1:]
#                 self.page_num = 1
#                 yield SplashRequest(url = 'https://my.lazada.vn/pdp/review/getReviewList?itemId={}&pageSize=5&filter=0&sort=0&pageNo=1'.format(item_id), callback=self.parse_item, endpoint='execute', args={'lua_source' : self.wait_script})

#             # time.sleep(5)

#         if self.index < 102:    
#             self.index += 1
#             time.sleep(200)
#             yield SplashRequest(url = 'https://www.lazada.vn/dien-thoai-di-dong/?page={}&spm=a2o4n.home.cate_1.1.51a26afeb9omAJ'.format(self.index),
#                                 callback=self.parse_first, endpoint='execute', args={'lua_source' : wait_script_2})

#     def parse_item(self, response):
#         data = {}
#         data['name'] = response.css('span.pdp-mod-product-badge-title::text').extract_first()
#         comments = []
#         for item in response.css('div.item'):
#             comment = item.css('div.content::text').extract_first()
#             if comment is not None:
#                 stars = len(item.css('img[src="//laz-img-cdn.alicdn.com/tfs/TB19ZvEgfDH8KJjy1XcXXcpdXXa-64-64.png"]'))
#                 comments.append({'stars': stars, 'comments': comment})

#         data['comments'] = comments
#         data['url'] = response.url
#         yield data


class sendo(CrawlSpider):
    name = 'sendo'

    def __init__(self, url='', start_page=1, end_page=1, *args, **kwargs):
        super(sendo, self).__init__(*args, **kwargs)
        for i in range(start_page, end_page + 1):
            self.start_urls.append(url + '&page={}'.format(i))

    start_urls = ["https://www.sendo.vn/may-da-qua-su-dung"]
    index = 1
    domain = 'https://www.sendo.vn'

    def start_requests(self):
        for url in self.start_urls:
            yield SplashRequest(args={'lua_source' : wait_script}, url=url, callback=self.parse_first, endpoint='execute')

    def parse_first(self, response):
        for item in response.css('a[aria-label="item_3KnU"]'):
            if len(item.css('div.stars_2og7').extract()) != 0:
                item_link = item.css('::attr(href)').extract_first()
                yield SplashRequest(args={'lua_source' : wait_script}, url = self.domain + item_link , callback=self.parse_item, endpoint='execute')

        if(self.index < 243):
            self.index += 1
            yield SplashRequest(args={'lua_source' : wait_script_2}, url="https://www.sendo.vn/may-da-qua-su-dung?p={}".format(self.index), callback=self.parse_first, endpoint='execute')

    def parse_item(self, response):
        pass

# class shopee(CrawlSpider):
#     name = 'shopee'
#     start_urls = ['https://shopee.vn/%C4%90i%E1%BB%87n-tho%E1%BA%A1i-cat.84.1979?page=0&sortBy=pop']
#     index = 0


#     def start_requests(self):
#         for url in self.start_urls:
#             yield SplashRequest(url=url, callback=self.parse_first, args={'lua_source' : wait_script_shopee}, endpoint='execute')

#     def parse_first(self, response):
#         urls = []
#         for item in response.css('div.shopee-search-item-result__item'):
#             if (item.css('div.shopee-rating-stars').extract_first() is not None):
#                 urls.append(item.css('a[data-sqe="link"]::attr(href)').extract_first())

#         for url in urls:
#             yield SplashRequest(url=response.urljoin(url), callback=self.parse_item, args={'lua_source' : get_comment_script_shopee}, endpoint='execute')

#         if self.index < 99:
#             self.index += 1
#             yield SplashRequest(url='https://shopee.vn/%C4%90i%E1%BB%87n-tho%E1%BA%A1i-cat.84.1979?page={}&sortBy=pop'.format(self.index), args={'lua_source' : wait_script_shopee}, endpoint='execute', callback=self.parse_first)


#     def parse_item(self, response):
#         data = {}
#         url = response.url
#         name = response.css('div.qaNIZv::text').extract_first()
#         comments = []
#         for item in response.css('div.shopee-product-rating__main'):
#             stars = len(item.css('svg.shopee-svg-icon.icon-rating-solid--active.icon-rating-solid').extract())
#             comment = item.css('div.shopee-product-rating__content::text').extract_first()
#             comments.append({'stars': stars, 'comment': comment})

#         data['url'] = url
#         data['name'] = name
#         data['comments'] = comments

#         yield data

class TestVatGia(CrawlSpider):
    name = 'vatgiatest'
    start_urls = ["https://vatgia.com/438/1635193/binh_chon_new/apple-iphone-4s-16gb-black-b%E1%BA%A3n-qu%E1%BB%91c-t%E1%BA%BF.html"]

    def start_requests(self):
        for url in self.start_urls:
            yield SplashRequest(args={'lua_source' : get_comment_script_tiki}, url=url, callback=self.parse, endpoint='execute')

    def parse(self, response):
        comments = []
        cmt_list = response.css('li')
        for item in cmt_list:
            star_and_comment = item.css('div.dpr_content span')
            if len(star_and_comment) == 2:
                stars = len(star_and_comment[0].css('i.icm.icm_star-full2.active'))
                comment = star_and_comment[1].css('::text').extract_first()
                comments.append({'stars': stars, 'comment': comment})

        data = {}
        data['comments'] = comments
        yield data

class thegioididong(CrawlSpider):
    name = 'thegioididong'
    wait_script = """
    function main(splash, args)
      assert(splash:go(args.url))
      assert(splash:wait(5))
      return {
        html = splash:html(),
        cookies = splash:get_cookies()
      }
    end
    """
    get_comment_script = """
    function main(splash, args)
      assert(splash:go(args.url))
      assert(splash:wait(0.75))
      return_html = splash:select('ul.breadcrumb').node.outerHTML
      return_html = return_html .. splash:select('ul.ratingLst').node.outerHTML
      btn_elements = splash:select_all('div.pagcomment a')
        if #btn_elements > 0 then
        last_element = btn_elements[#btn_elements]
        while (last_element:text() == "»")
        do
            last_element.click()
            assert(splash:wait(1.25))
            return_html = return_html .. splash:select('ul.ratingLst').node.outerHTML
            btn_elements = splash:select_all('div.pagcomment a')
            last_element = btn_elements[#btn_elements]
        end
      end
      
      return {
        html = return_html,
        cookies = splash:get_cookies()
      }
    end
    """
    start_urls = ["https://www.thegioididong.com/dtdd#i:5"]

    def start_requests(self):
        for url in self.start_urls:
            yield SplashRequest(args={'lua_source' : self.wait_script}, url=url, callback=self.parse_first, endpoint='execute')

    def parse_first(self, response):
        urls = []   
        for item in response.css('ul.homeproduct li'):
            if len(item.css('div.ratingresult i')) > 0:
                urls.append(item.css('a::attr(href)').extract_first())

        for url in urls:
            yield SplashRequest(args={'lua_source' : self.get_comment_script}, url=response.urljoin(url) + '/danh-gia', callback=self.parse_item, endpoint='execute')


    def parse_item(self, response):
        url = response.url
        name = response.css('ul.breadcrumb li')[3].css('a::text').extract_first()
        comments = []
        for item in response.css('li.par'):
            stars = len(item.css('i.iconcom-txtstar'))
            comment = item.css('div.rc i')[-1].css('::text').extract_first()
            comments.append({'stars' : stars, 'comment' : comment})

        data = {}
        data['url'] = url
        data['comments'] = comments
        data['name'] = name

        yield data







