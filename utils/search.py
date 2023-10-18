#coding=utf- 8
import requests
from enum import Enum
import time
from bs4 import BeautifulSoup
import trafilatura
from playwright.sync_api import sync_playwright


class CONTENT_TYPE(Enum):
    SEARCH_RESULT = 0
    RESULT_TARGET_PAGE = 1

class ContentItem:
    def __init__(self, type: CONTENT_TYPE, data):
        self.type = type
        self.data = data

class Operator():
    def __init__(self):
        self.content = []

    def search(self, key_words) -> list:
        start_time = time.time()
        try:
            result =  query_bing(key_words)
        except Exception:
            result =  query_bing(key_words)
        

        result_list = []
        if "site:" in key_words and result is not None:
            for line in result:
                if key_words.split('site:')[1] in line['url']:
                    result_list.append(line)
        elif result is not None:
            result_list = result.copy()

        self.content = []
        self.content.append(ContentItem(CONTENT_TYPE.SEARCH_RESULT, result_list))
        print(f'search time:{time.time() - start_time}s')
        
        try:
            webpage = result_list
            return webpage
        except:
            return []

    def get_page_num(self) -> int:
        return len(self.content[-1].data)
    
    def get_page(self, url: str):
        res= requests.get(url, timeout=10)
        res.raise_for_status()
        res.encoding = res.apparent_encoding
        return res


    def load_page(self, idx:int) -> str:
        try:
            top = self.content[-1].data
            res =  self.get_page(top[idx]['url'])
            res.raise_for_status()
            res.encoding = res.apparent_encoding
            content = res.text
            soup = BeautifulSoup(content, 'html.parser')
            text = trafilatura.extract(soup.prettify())
                
            return top[idx]['url'], text
        except:
            return None, None


# bing search without api

def get_bing_search_raw_page(question: str):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(f"https://www.bing.com/search?q={question}" + "&ensearch=1")
        except:
            page.goto(f"https://www.bing.com")
            page.fill('input[name="q"]', question)
            page.press('input[name="q"]', 'Enter')
        try:
            page.wait_for_load_state('networkidle', timeout=3000)
        except:
            pass
        # page.wait_for_load_state('networkidle')
        search_results = page.query_selector_all('.b_algo h2')
        for result in search_results:
            title = result.inner_text()
            a_tag = result.query_selector('a')
            if not a_tag: continue
            url = a_tag.get_attribute('href')
            if not url: continue
            results.append({
                'name': title,
                'url': url
            })
        browser.close()
    return results

def query_bing(question, max_tries=3):
    cnt = 0
    while cnt < max_tries:
        cnt += 1
        results = get_bing_search_raw_page(question)
        if results:
            return results
    print('No Bing Result')
    return None

# if __name__ == '__main__':
#     # query_bing("Why do undocumented immigrants returning to Mexico drive down wages there, but proponents of relaxed immigration say they don't do the same here? site:https://www.economist.com/")



