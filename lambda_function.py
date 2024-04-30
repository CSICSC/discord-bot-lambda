import requests
from html.parser import HTMLParser
import os
import json
import boto3

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


s3_client = boto3.client('s3')

def lambda_handler(event, context):
    file_key = 'article-cache.json'
    bucket_name = 'discord-lambda-cache'
    resp = requests.get("https://news.ycombinator.com/", timeout=10)
    html = resp.text

    if not html:
        raise ValueError("could not request hacker news")

    parser = HNHTMLParser()

    parser.feed(html)

    articles_sorted = sorted(parser.articles, key=lambda x: x[0], reverse=True)

    used_articles = []
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        used_articles = json.load(response['Body'])
    except Exception as e:
        print(e)

    top_article = None

    for article in articles_sorted:
        if article[1] not in used_articles:
            top_article = article
            break

    used_articles.append(top_article[1])

    if len(used_articles) > 8:
        used_articles.pop(0)

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

    
    s3_client.put_object(Body=json.dumps(used_articles), Bucket=bucket_name, Key=file_key)

    return 'success'
