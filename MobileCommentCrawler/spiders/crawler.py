from scrapy import Selector, Request
from scrapy.spiders import CrawlSpider
import re
from scrapy_splash import SplashRequest

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
  assert(splash:wait(0.5))
  return {
    html = splash:html(),
    cookies = splash:get_cookies()
  }
end
"""

get_comment_script = """
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


class vatgia(CrawlSpider):
    name = 'vatgia'
    # urls = []
    domain = 'https://vatgia.com'
    index = 1
    # for i in range(389):
        # urls.append("https://vatgia.com/home/listudv.php?iCat=438&p10=4&page={}".format(i+1))
    start_urls = ["https://vatgia.com/home/listudv.php?iCat=438&p10=4"]

    def start_requests(self):
        for url in self.start_urls:
            yield SplashRequest(args={'lua_source' : wait_script}, url=url, callback=self.parse_first, endpoint='execute')

    def parse_first(self, response):
        # print(response.css("#type_product_list_udv div.wrapper"))
        for item in response.css("#type_product_list_udv div.wrapper"):
            if (len(item.css("div.group_rating_order")) != 0):
                next_link = item.css("a.picture_link::attr(href)").extract_first()
                next_link_split = next_link.split('/')
                url = self.domain + '/' + next_link_split[1] + '/' + next_link_split[2] + '/' + 'binh_chon_new' + '/' + next_link_split[3]
                print(url)
                yield SplashRequest(args={'lua_source' : get_comment_script}, url=url, callback=self.parse_item, endpoint='execute')

        if (self.index < 50):
            self.index += 1
            yield SplashRequest(args={'lua_source': wait_script_2}, url="https://vatgia.com/home/listudv.php?iCat=438&p10=4&page={}".format(self.index), callback=self.parse_first, endpoint='execute')


    def parse_item(self, response):
        data = {}
        data['url'] = response.url
        data['name'] = response.css('div#header_navigate_breadcrumb b::text').extract_first()
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

class TestVatGia(CrawlSpider):
    name = 'vatgiatest'
    start_urls = ["https://vatgia.com/438/1635193/binh_chon_new/apple-iphone-4s-16gb-black-b%E1%BA%A3n-qu%E1%BB%91c-t%E1%BA%BF.html"]

    def start_requests(self):
        for url in self.start_urls:
            yield SplashRequest(args={'lua_source' : get_comment_script}, url=url, callback=self.parse, endpoint='execute')

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
