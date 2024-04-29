import requests
from html.parser import HTMLParser
import os


class HNHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_score_span = False
        self.in_titleline_span = False
        self.current_link = None
        self.found_first_link = False
        self.articles = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "span":
            if 'class' in attrs_dict and attrs_dict['class'] == 'score':
                self.in_score_span = True
            if 'class' in attrs_dict and attrs_dict['class'] == 'titleline':
                self.in_titleline_span = True
        elif tag == "a" and self.in_titleline_span and not self.found_first_link:
            self.current_link = attrs_dict.get('href')
            self.found_first_link = True

    def handle_endtag(self, tag):
        if tag == "span":
            if self.in_titleline_span:
                self.found_first_link = False
                self.in_titleline_span = False
            if self.in_score_span:
                self.in_score_span = False

    def handle_data(self, data):
        if self.in_score_span:
            score = int(data.split()[0])
            if self.current_link:
                self.articles.append((score, self.current_link))


def lambda_handler(event, context):
    response = requests.get("https://news.ycombinator.com/", timeout=10)
    html = response.text

    if not html:
        raise ValueError("could not request hacker news")

    parser = HNHTMLParser()

    parser.feed(html)

    articles_sorted = sorted(parser.articles, key=lambda x: x[0], reverse=True)
    top_article = articles_sorted[0] if articles_sorted else None

    if top_article:
        data = {
            'content': f'Top HackerNews article ({top_article[0]} points) -> {top_article[1]}',
        }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bot {os.getenv('TOKEN')}'
        }

        url = f"https://discord.com/api/v9/channels/{os.getenv('CSI_CSC_CHANNEL')}/messages"

        result = requests.post(url, json=data, headers=headers, timeout=10)
        result.raise_for_status()

    return 'success'
