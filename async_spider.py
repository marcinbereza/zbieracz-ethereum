from bs4 import BeautifulSoup
from time import perf_counter
import requests
import json
import sys

import asyncio
import aiohttp
from aiohttp import ClientSession

base_url = "http://127.0.0.1:5000"
semaphore = asyncio.Semaphore(100)

visited = set()
results = []
ethereum = 0
start = 0

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


async def get_node(
        session: ClientSession,
        node_href: str
    ) -> tuple[int, int, list[str]]:
    """
    Parses the page at the given `node_href` and extracts:

    Returns:
        Tuple:
        - node number (int)
        - ethereum value (int)
        - list of hrefs to next nodes (list[str])
    """
    async with semaphore:
        try:
            async with session.get(f'{base_url}{node_href}') as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'lxml')

                if soup.find('h1') and 'Brak dostępu' in soup.h1.text:
                    x_password = resp.headers.get('x-password')
                    if x_password:
                        async with session.post(
                            f'{base_url}/validate_password/{node_href}',
                            data={'password': x_password},
                            allow_redirects=True
                        ): pass
                        async with session.get(f'{base_url}{node_href}') as resp2:
                            html = await resp.text()
                            soup = BeautifulSoup(html, 'lxml')
                    else:
                        node_number = int(soup.p.text.split()[3].strip())
                        node_value = 0
                        node_hrefs = []
                else:
                    node_number = int(soup.h2.text.split(':')[-1].strip())
                    node_value = int(soup.p.text.split()[1].strip())
                    node_hrefs = [a['href'] for a in soup.find_all('a')]

                return node_number, node_value, node_hrefs
            
        except Exception as e:
            print(f"\nBłąd przy {node_href}: {e}")
            return -1, 0, []


async def spider_bfs_async(
        start_href: str,
        max_depth: int=None
    ) -> list[dict[int, int]]:
    """
    Asynchronously traverses the Ethereum app graph using BFS algorithm.

    Starting from the given href, it visits all accessible nodes,
    collects ethereum values, and tracks visited pages.

    Args:
        start_href: Href to the first node in the graph.
        max_depth:  Max lenth of branches where spider could come.

    Returns:
        List:
        - 'node': node ID (int)
        - 'ethereum': collected value (int)
    """
    print("Rozpoczęto asynchroniczne kopanie...")
    global visited, results, ethereum
    queue = [(start_href, 0)]  # (link, depth)
    visited = set()
    results = []

    async with aiohttp.ClientSession() as session:
        while queue:
            current_batch = []
            next_queue = []

            for href, depth in queue:
                if max_depth is not None and depth > max_depth: continue
                if href in visited: continue
                current_batch.append(get_node(session, href))
                visited.add(href)

            nodes = await asyncio.gather(*current_batch)

            for node, eth, links in nodes:
                ethereum+=eth
                results.append({'node': node, 'ethereum': eth})

                for link in links:
                    next_queue.append((link, depth + 1))

            queue = next_queue
        return results


async def progress_report() -> None:
    """
    Prints progress report every 0.1 seconds, showing:
    - Number of visited nodes
    - Collected ethereum
    - Elapsed time since start
    """
    global visited, ethereum, start
    while True:
        try:
            print(f'\rOdwiedzono: {len(visited):>4} | Ethereum: {ethereum:>5} | Czas: {(perf_counter() - start):.2f}s', end='')
            await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            break
        finally:
            print(f'\rOdwiedzono: {len(visited):>4} | Ethereum: {ethereum:>5} | Czas: {(perf_counter() - start):.2f}s', end='')


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


async def main():
    start_href = get_first_node()
    
    progress = asyncio.create_task(progress_report())
    nodes = await spider_bfs_async(start_href)
    progress.cancel()
    await progress

    save_json(nodes, 'ethereum_async.json')
    input('\nKliknij, aby zamknąć...')


if __name__ == '__main__':
    start = perf_counter()
    asyncio.run(main())
