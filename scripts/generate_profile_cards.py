#!/usr/bin/env python3
"""Generate profile SVGs directly from GitHub's public REST API (stdlib only)."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def api(path):
    headers = {'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28',
               'User-Agent': 'repository-profile-cards'}
    if os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    print(f'Fetching {path}', flush=True)
    for attempt in range(3):
        try:
            with urlopen(Request('https://api.github.com' + path, headers=headers), timeout=40) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** (attempt + 1))


def collect(username):
    repos = []
    page = 1
    while True:
        batch = api(f'/users/{username}/repos?type=owner&per_page=100&page={page}')
        repos.extend(repo for repo in batch if not repo['private'])
        if len(batch) < 100:
            break
        page += 1
    original = [repo for repo in repos if not repo['fork']]
    languages = Counter()
    for repo in original:
        languages.update(api(f"/repos/{repo['full_name']}/languages"))
    counts = {}
    for kind in ('pr', 'issue'):
        result = api('/search/issues?' + urlencode({'q': f'author:{username} type:{kind} is:public', 'per_page': 1}))
        if result.get('incomplete_results'):
            raise RuntimeError('GitHub returned incomplete search results; keeping existing cards')
        counts[kind] = result['total_count']
    return {'username': username,
            'updated': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            'repos': len(original),
            'stars': sum(repo['stargazers_count'] for repo in original),
            'forks': sum(repo['forks_count'] for repo in original),
            'prs': counts['pr'], 'issues': counts['issue'],
            'languages': dict(languages.most_common(6))}


def text(x, y, value, color='#c9d1d9', size=12, weight=400):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}">{escape(str(value))}</text>'


def card(width, title, body, description, accent):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="165" viewBox="0 0 {width} 165" role="img" aria-labelledby="title desc">'
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>'
            '<rect width="100%" height="100%" rx="8" fill="#05060A"/>'
            '<g font-family="Segoe UI, Ubuntu, sans-serif">' +
            text(18, 27, title, accent, 16, 600) + body + '</g></svg>\n')


def render(data):
    rows = [('Stars earned', data['stars']), ('Public repositories', data['repos']),
            ('Forks received', data['forks']), ('Public pull requests', data['prs']),
            ('Public issues opened', data['issues'])]
    body = ''
    for index, (label, value) in enumerate(rows):
        y = 51 + index * 20
        body += f'<circle cx="23" cy="{y - 4}" r="3" fill="#00E5FF"/>'
        body += text(35, y, label) + text(287, y, f'{value:,}', size=12, weight=600)
    body += text(18, 156, f"Public data · {data['updated']} UTC", '#9198a1', 9)
    stats = card(370, f"{data['username']}'s GitHub stats", body,
                 '; '.join(f'{label}: {value}' for label, value in rows), '#FF7A00')

    colors = ['#FF7A00', '#00E5FF', '#2E7BFF', '#FFB000', '#FF2E97', '#8B5CF6']
    languages = list(data['languages'].items())
    total = sum(value for _, value in languages)
    body = '<defs><clipPath id="bar"><rect x="18" y="43" width="284" height="9" rx="4"/></clipPath></defs><g clip-path="url(#bar)">'
    x = 18
    for index, (_, value) in enumerate(languages):
        width = value / total * 284 if total else 0
        body += f'<rect x="{x:.3f}" y="43" width="{width:.3f}" height="9" fill="{colors[index]}"/>'
        x += width
    body += '</g>'
    for index, (name, value) in enumerate(languages):
        x, y = 23 + (index % 2) * 144, 78 + (index // 2) * 25
        body += f'<circle cx="{x}" cy="{y - 4}" r="4" fill="{colors[index]}"/>'
        body += text(x + 10, y, f'{name} {value / total:.1%}', size=10)
    if not total:
        body += text(18, 82, 'No public language data yet')
    body += text(18, 156, 'Top 6 by code bytes · public repos · no forks', '#9198a1', 9)
    langs = card(320, 'Most used languages', body,
                 'Share of the six largest languages by code bytes across public, non-fork owned repositories. ' +
                 '; '.join(f'{name}: {value / total:.1%}' for name, value in languages), '#00E5FF')
    return {'github-stats.svg': stats, 'top-languages.svg': langs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username', default='GoblinRules')
    parser.add_argument('--output', type=Path, default=Path('assets/stats'))
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9-]+', args.username):
        parser.error('Invalid GitHub username')
    # Collect and render everything before replacing any last-known-good files.
    cards = render(collect(args.username))
    args.output.mkdir(parents=True, exist_ok=True)
    for name, svg in cards.items():
        temp = args.output / (name + '.tmp')
        temp.write_text(svg, encoding='utf-8')
        temp.replace(args.output / name)
    print('Generated ' + ', '.join(cards))


if __name__ == '__main__':
    main()
