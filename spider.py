from bs4 import BeautifulSoup
from time import perf_counter
import requests
import json
import sys

from collections import deque
from requests import Session

base_url = "http://127.0.0.1:5000/"

def get_first_node() -> str:
    """
    Get the link to the first node from the main page of the Ethereum app.

    Returns:
        String: The link to next page.
    
    Raises:
        ConnectionError: If the local server is not running.
        HTTPError: If the local server return error.
    """
    try:
        resp = requests.get(base_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'lxml')
        return soup.a['href']
    except requests.ConnectionError:
        print('Nie udało się połączyć z lokalnym serwerem Flask.')
        print('Upewnij się, że uruchomiłeś aplikacje Ethereum.')
        sys.exit(1)
    except requests.HTTPError as e:
        print(f'Serwer zwrócił błąd HTTP: {e}')
        sys.exit(1)


def get_node(session: Session, node_href: str) -> tuple[int, int, list[str]]:
    """
    Parses the page at the given `node_href` and extracts:

    Returns:
        Tuple:
        - node number (int)
        - ethereum value (int)
        - list of hrefs to next nodes (list[str])

    Raises:
        ConnectionError: If the local server is not running.
        HTTPError: If the local server return error.
    """
    try:
        resp = session.get(f'{base_url}{node_href}')
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'lxml')

        if soup.find('h1') and 'Brak dostępu' in soup.h1.text:
            x_password = resp.headers.get('x-password')
            if x_password:
                post_resp = session.post(
                    f'{base_url}/validate_password/{node_href}',
                    data={'password': x_password},
                    allow_redirects=True
                    )
                resp = session.get(f'{base_url}{node_href}')
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, 'lxml')
            else:
                node_number = int(soup.p.text.split()[3].strip())
                node_value  = 0
                node_hrefs  = []
        else:
            node_number = int(soup.h2.text.split(':')[-1].strip())
            node_value  = int(soup.p.text.split()[1].strip())
            node_hrefs  = [a['href'] for a in soup.find_all('a')]

        return node_number, node_value, node_hrefs
    
    except requests.ConnectionError:
        print('Nie udało się połączyć z lokalnym serwerem Flask.')
        print('Upewnij się, że uruchomiłeś aplikacje Ethereum.')
        sys.exit(1)
    except requests.HTTPError as e:
        print(f'Serwer zwrócił błąd HTTP: {e}')
        sys.exit(1)


def spider_bfs(start_node: str) -> list[dict[int, int]]:
    """
    Synchronously traverses the Ethereum app graph using BFS algorithm.

    Starting from the given href, it visits all accessible nodes,
    collects ethereum values, and tracks visited pages.

    Args:
        start_href: Href to the first node in the graph.

    Returns:
        List:
        - 'node': node ID (int)
        - 'ethereum': collected value (int)
    """
    print('Rozpoczęto kopanie...')
    start = perf_counter()
    queue = deque([start_node])
    visited = set()
    results = []
    ethereum = 0

    with Session() as session:
        while queue:
            href = queue.popleft()
            if href in visited: continue
            node, eth, links = get_node(session, href)
            visited.add(href)
            ethereum+=eth
            results.append({'node':node, 'ethereum':eth})
            
            for link in links:
                queue.append(link)

            print(f'\rOdwiedzono: {len(visited):>4} | Ethereum: {ethereum:>5} | Czas: {(perf_counter() - start):.2f}s', end='')
        return results


def save_json(data: list[dict[int, int]], output_name: str='ethereum.json') -> None:
    """
    Calculates the total amount of collected Ethereum and saves the data to a JSON file.

    The output JSON file contains:
    - "suma": the total Ethereum collected,
    - "wierzchołki": a list of dictionaries with node number and its Ethereum value.
    """
    total_ethereum = sum(d['ethereum'] for d in data)

    with open(output_name, 'w', encoding='utf-8') as o:
        json.dump({
            'suma': total_ethereum,
            'wierzchołki': data
        }, o, indent=2)
    
    print(f'\nZapisano do {output_name}')


def main():
    start_node = get_first_node()
    nodes = spider_bfs(start_node)
    save_json(nodes)
    input('\nKliknij, aby zamknąć...')

if __name__ == '__main__':
    main()
