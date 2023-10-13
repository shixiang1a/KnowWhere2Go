#coding=utf- 8
import requests
from enum import Enum
import time
from bs4 import BeautifulSoup
import trafilatura
import os
from playwright.sync_api import sync_playwright

# ad93d025a4d04b4ea786d4722662411e d222deb3c1564c0483ae07ae1f19b03c
subscription_key = os.environ.get('BING_SEARCH_KEY', 'd222deb3c1564c0483ae07ae1f19b03c')
endpoint = "https://api.bing.microsoft.com/v7.0/search"
mkt = 'en-US'
headers = { 'Ocp-Apim-Subscription-Key': subscription_key }

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

    def search(self, key_words, filter=None) -> list:
        start_time = time.time()
        try:
            result =  remote_request(key_words)
            # result = requests.get(endpoint, headers=headers, params={'q': key_words, 'mkt': mkt }, timeout=10)
        except Exception:
            result =  remote_request(key_words)
            # result = requests.get(endpoint, headers=headers, params={'q': key_words, 'mkt': mkt }, timeout=10)
        if result.status_code == 200:
            result = result.json()

            result_list = []
            if "site:" in key_words and result is not None:
                for line in result:
                    if key_words.split('site:')[1] in line['url']:
                        result_list.append(line)
            elif result is not None:
                result_list = result.copy()


            self.content = []
            self.content.append(ContentItem(CONTENT_TYPE.SEARCH_RESULT, result_list))
        else:
            # result = requests.get(endpoint, headers=headers, params={'q': key_words, 'mkt': mkt }, timeout=10)
            result =  remote_request(key_words)
            if result.status_code == 200:
                result = result.json()

                result_list = []
                if "site:" in key_words and result is not None:
                    for line in result:
                        if key_words.split('site:')[1] in line['url']:
                            result_list.append(line)
                elif result is not None:
                    result_list = result.copy()

                self.content = []
                self.content.append(ContentItem(CONTENT_TYPE.SEARCH_RESULT, result_list))
            else:
                raise Exception('Platform search error. Do you register your Bing API key?')
        print(f'search time:{time.time() - start_time}s')
        
        try:
            # webpage = self.content[-1].data["webPages"]["value"]
            webpage = result_list
            return webpage
        except:
            return []

    def get_page_num(self) -> int:
        return len(self.content[-1].data)
        # return len(self.content[-1].data["webPages"]["value"])

    def load_page(self, idx:int) -> str:
        try:
            top = self.content[-1].data
            # top = self.content[-1].data["webPages"]["value"]
            # res = requests.get(top[idx]['url'], timeout=10)
            res =  remote_page(top[idx]['url'])
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
            # print(title, url)
            results.append({
                'title': title,
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

def remote_query(question):
    # 远程接口地址
    url = "http://bing-get-page.natapp1.cc/bing"

    # 准备要发送的数据（这里假设你想查询的问题是"example question"）
    data = {"question": question}

    try:
        # 发送GET请求到远程接口
        response = requests.get(url, params=data)

        # 检查响应状态码
        if response.status_code == 200:
            # 解析JSON响应
            result = response.json()
            print(result)  # 这里的result将是查询的结果
        else:
            print("请求失败，状态码:", response.status_code)

    except requests.exceptions.RequestException as e:
        print("请求发生异常:", e)


def remote_request(question):
    url = "http://bing-get-page.natapp1.cc/bing_search"
    data = {"question": question}
    # print(data)
    response = requests.get(url, params=data)
    return response

def remote_page(page_url):
    url = "http://bing-get-page.natapp1.cc/web_search"
    data = {"url": page_url}
    # print(data)
    response = requests.get(url, params=data)
    return response


