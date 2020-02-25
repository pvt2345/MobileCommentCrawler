from scrapy.spiders import CrawlSpider
from scrapy_splash import SplashRequest
import time
from MobileCommentCrawler.items import MobilecommentcrawlerItem

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


class testLazada(CrawlSpider):
    name = 'testlazadaPage'
    index = 1
    start_urls = ['https://www.lazada.vn/dien-thoai-di-dong/?page=1']

    def start_requests(self):
        for url in self.start_urls:
            yield SplashRequest(url=url, callback=self.parse_first, endpoint='execute',
                                args={'lua_source': wait_script})

    def parse_first(self, response):
        urls = []
        for item in response.css('div.c2prKC'):
            if item.css('div.c2JB4x.c6Ntq9') is not None:
                url = item.css('div.c16H9d a[age="0"]::attr(href)').extract_first()
                urls.append(url)

        print(len(urls))
        print(urls)


class testLazadaComment(CrawlSpider):
    name = 'testLazadaComment'
    start_urls = ['https://www.lazada.vn/products/lg-g6-moi-nguyen-zin-nhap-khau-i265230183-s466186434.html']

    def start_requests(self):
        for url in self.start_urls:
            yield SplashRequest(url=url, callback=self.parse_item, endpoint='execute',
                            args={'lua_source': get_comment_script_lazada})

    def parse_item(self, response):
        data = {}
        data['name'] = response.css('span.pdp-mod-product-badge-title::text').extract_first()
        comments = []
        for item in response.css('div.item'):
            comment = item.css('div.content::text').extract_first()
            if comment is not None:
                stars = len(item.css('img[src="//laz-img-cdn.alicdn.com/tfs/TB19ZvEgfDH8KJjy1XcXXcpdXXa-64-64.png"]'))
                comments.append({'stars': stars, 'comments': comment})

        data['comments'] = comments
        data['url'] = response.url
        yield data



