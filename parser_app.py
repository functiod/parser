import requests
from bs4 import BeautifulSoup
import validators
import re

video_url: str = 'https://animego.org/anime//player?_allow=true'
change_series_url: str = 'https://animego.org/anime/series?dubbing=1&provider=19&episode=3&id=5497'

def download_html_page(url: str) -> str | None:
    try:
        return requests.get(url).content.decode('utf-8')
    except KeyboardInterrupt:
        raise
    except:
        return None

def download_html_video_page(url: str) -> str | None:
    try:
        return requests.get(url, headers={"x-requested-with": "XMLHttpRequest"}).json()
    except KeyboardInterrupt:
        raise
    except:
        return None

def check_if_link(url: str) -> bool:
    try:
        response: requests.Response = requests.head(url)
        if response.status_code == 200:
            return True
        else:
            return False
    except requests.exceptions.RequestException:
        return False

def extract_links_from_html(html: str) -> list:
    parser = BeautifulSoup(html, features="html.parser")
    return parser.find_all('a', href=True)

def parse_links_to_movies(html: str) -> list:
    false_name_list: list = ['manga', 'characters', 'random', 'connect', 'vkontakte', 'genre', 'type', 'season']
    # link_list: list = list(set([str(elem['href']) for elem in extract_links_from_html(html)]))
    link_list: list = list(set([elem['href'] for elem in extract_links_from_html(html)]))
    valid_links: list = []
    for link in link_list:
        if validators.url(link):
            valid_links.append(link)
    filtered_links: list = [link for link in valid_links if not any(elem in link for elem in false_name_list)
                             and link.split('/')[-1] != 'anime' and check_if_link(link)]
    return filtered_links

def extract_info_from_html(html: str) -> dict:
    parser = BeautifulSoup(html, features="html.parser")
    title: str = parser.find('div', class_ ='anime-title').find('h1').get_text()
    dl_element: list = parser.find('dl', class_='row')
    dt_elements: list = dl_element.find_all('dt')
    dd_elements: list = dl_element.find_all('dd')
    param_dict: dict = {}
    parameter: str = ''
    value: str = ''
    param_dict['Название'] = title
    for dt, dd in zip(dt_elements, dd_elements):
        parameter = dt.text.strip()
        value = dd.text.strip()
        correct_value: str = re.sub(r'\s+', ' ', value)
        param_dict[parameter] = correct_value
    return param_dict

def get_url_last_numbers(html: str) -> int:
    last_place: int = html.rfind('-')
    return html[last_place+1:]

def make_video_url_requests(html: str) -> tuple:
    links_list: list = parse_links_to_movies(html)
    last_number_list: list = list(map(get_url_last_numbers, links_list))
    input_before: int = video_url.rfind('/')
    requests_list: list = [video_url[:input_before]+last_number_list[i]+video_url[input_before:] for i in range(len(last_number_list))]
    return links_list, requests_list

def extract_series_from_video_html(html: str) -> list[list]:
    links_iter: int = 0
    requests_iter: int = 1
    requests_list: tuple = make_video_url_requests(html)
    page_content: list = [download_html_video_page(requests_list[requests_iter][i]) for i in range(len(requests_list[requests_iter]))]
    page_slice: list = [[requests_list[links_iter][i]] + page_content[i][page_content[i].find("data-episode"):page_content[i].find('data-episode-description=')].split('\n') for i in range(len(page_content))]
    return page_slice

def devide_films_by_series(html: str) -> tuple:
    page_slice: list[list] = extract_series_from_video_html(html)
    one_series: list = []
    several_series: list = []
    for i in range(len(page_slice)):
        if any('data-id' in elem for elem in page_slice[i]):
            several_series.append(page_slice[i])
        else:
            one_series.append(page_slice[i])
    one_series_final: list = delete_extra(one_series)
    several_series_final: list = delete_extra(delete_extra(several_series))
    return one_series_final, several_series_final

def delete_extra(buff: list) -> list:
    my_buff: list = buff
    for i, elem in enumerate(buff):
        my_buff[i] = list(filter(None, elem))
        for j, N in enumerate(my_buff[i]):
            my_buff[i][j] = N.strip()
    return my_buff
# Я ТУТА!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
def extract_voice_from_video_html(html: str) -> list[list]:
    links_iter: int = 0
    requests_iter: int = 1
    requests_list: tuple = make_video_url_requests(html)
    page_content: list = [download_html_video_page(requests_list[requests_iter][i]) for i in range(len(requests_list[requests_iter]))]
    # page_slice: list = [[requests_list[links_iter][i]] + page_content[i][page_content[i].find("data-episode"):page_content[i].find('data-episode-description=')].split('\n') for i in range(len(page_content))]
    return page_content

def all_pages_url() -> list:
    initial_url: str = 'https://animego.org/anime?sort=a.startDate&direction=asc'
    url_template: str = 'https://animego.org/anime?sort=a.startDate&direction=asc&type=animes&page='
    url_list: list = [initial_url]
    page_number: int = 2
    while True:
        url: str = url_template + str(page_number)
        response: requests.Response = requests.get(url)
        if response.status_code != 200:
            break
        url_list.append(url)
        page_number += 1
    return url_list

def download_all_pages() -> dict:
    url_list: list = all_pages_url()
    movies_links: list = []
    movie_params: list = []
    final_list: list = []
    for url in url_list:
        movies_links = parse_links_to_movies(download_html_page(url))
        for link in movies_links:
            print(link)
            movie_params = extract_info_from_html(download_html_page(link))
            final_list.append(movie_params)
    return len(url_list), final_list

if __name__ == '__main__':
    # info_list: list = devide_films_by_series(download_html_page('https://animego.org/anime?sort=a.startDate&direction=asc'))
    # print(info_list[0])
    # print(info_list[1])
    # print(get_voice_acting_list(download_html_video_page('https://animego.org/anime/1891/player?_allow=true')))
    print(extract_voice_from_video_html(download_html_page('https://animego.org/anime/vosemdesyat-shest-2-1891')))
