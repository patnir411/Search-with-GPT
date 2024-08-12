import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from storage import storage

class ArxivSpider(CrawlSpider):
    print("arxiv spider initialized!")
    name = 'arxiv_spider'
    allowed_domains = ['arxiv.org']
    start_urls = ['https://arxiv.org/list/cs.AI/recent']

    rules = (
        # Follow pagination links
        Rule(LinkExtractor(restrict_xpaths='//a[contains(@class, "pagination")]'), follow=True),
        # Follow paper links
        Rule(LinkExtractor(restrict_xpaths='//li[contains(@class, "arxiv-result")]//a[contains(@href, "abs")]'), callback='parse_paper', follow=False),
    )

    def parse_paper(self, response):
        print(f"parsing paper with response: {response}")
        title = response.css('h1.title::text').get().strip()
        authors = response.css('div.authors a::text').getall()
        abstract = response.css('blockquote.abstract::text').get().strip()
        url = response.url
        pdf_url = response.css('a.download-pdf::attr(href)').get()

        # Store the extracted data
        content = f'Title: {title}\nAuthors: {", ".join(authors)}\nAbstract: {abstract}\nURL: {url}\nPDF URL: {pdf_url}'
        storage.add(url, content)
        print(f"\nURL: {url}\nContent: {content}\n")

        yield {
            'title': title,
            'authors': authors,
            'abstract': abstract,
            'url': url,
            'pdf_url': pdf_url
        }

# To run the spider
from scrapy.crawler import CrawlerProcess

def run_spider():
    process = CrawlerProcess({
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'ROBOTSTXT_OBEY': True,
        'CONCURRENT_REQUESTS': 16,
        'DOWNLOAD_DELAY': 1,  # Be polite!
        'COOKIES_ENABLED': False,
    })

    process.crawl(ArxivSpider)
    process.start()