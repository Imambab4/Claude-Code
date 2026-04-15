"""
GitHub Sponsors API client.

Uses the GitHub GraphQL API to fetch sponsorship data for the authenticated user.
Requires a GitHub Personal Access Token with the following scopes:
  - read:user
  - read:org (if checking org sponsorships)

Set the token via the GITHUB_TOKEN environment variable or a .env file.
"""

import os
import sys
import json
import urllib.request
import urllib.error

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

SPONSORS_QUERY = """
query GetSponsors($cursor: String) {
  viewer {
    login
    name
    sponsorshipsAsMaintainer(first: 100, after: $cursor, includePrivate: true) {
      totalCount
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        createdAt
        isActive
        privacyLevel
        tier {
          name
          monthlyPriceInDollars
          isCustomAmount
        }
        sponsorEntity {
          ... on User {
            login
            name
            url
          }
          ... on Organization {
            login
            name
            url
          }
        }
      }
    }
  }
}
"""


def graphql_request(token: str, query: str, variables: dict = None) -> dict:
    """Send a GraphQL request to the GitHub API."""
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        GITHUB_GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "sponsors-api-client/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def fetch_all_sponsors(token: str) -> dict:
    """Fetch all sponsors, handling pagination automatically."""
    all_nodes = []
    cursor = None
    viewer_info = {}

    while True:
        result = graphql_request(token, SPONSORS_QUERY, {"cursor": cursor})

        if "errors" in result:
            raise RuntimeError(f"GraphQL errors: {result['errors']}")

        data = result["data"]["viewer"]
        viewer_info = {"login": data["login"], "name": data["name"]}
        sponsorships = data["sponsorshipsAsMaintainer"]
        all_nodes.extend(sponsorships["nodes"])

        page_info = sponsorships["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]

    return {
        "viewer": viewer_info,
        "totalCount": len(all_nodes),
        "sponsors": all_nodes,
    }


def print_sponsors(data: dict) -> None:
    """Print sponsor information in a readable format."""
    viewer = data["viewer"]
    print(f"Sponsors for: {viewer['name']} (@{viewer['login']})")
    print(f"Total sponsors: {data['totalCount']}")
    print("-" * 50)

    if not data["sponsors"]:
        print("No sponsors found.")
        return

    # Sort by monthly amount descending
    sponsors = sorted(
        data["sponsors"],
        key=lambda s: s["tier"]["monthlyPriceInDollars"] if s["tier"] else 0,
        reverse=True,
    )

    for s in sponsors:
        entity = s.get("sponsorEntity") or {}
        login = entity.get("login", "private")
        name = entity.get("name") or login
        url = entity.get("url", "")
        tier = s.get("tier") or {}
        amount = tier.get("monthlyPriceInDollars", 0)
        tier_name = tier.get("name", "Unknown tier")
        active = "active" if s["isActive"] else "inactive"
        privacy = s["privacyLevel"].lower()
        created = s["createdAt"][:10]

        print(f"  {name} (@{login})")
        if url:
            print(f"    URL:     {url}")
        print(f"    Tier:    {tier_name} (${amount}/mo)")
        print(f"    Status:  {active} | privacy: {privacy} | since: {created}")
        print()


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        print("Create a token at https://github.com/settings/tokens", file=sys.stderr)
        print("Required scopes: read:user (and read:org for org sponsorships)", file=sys.stderr)
        sys.exit(1)

    try:
        data = fetch_all_sponsors(token)
    except urllib.error.HTTPError as exc:
        print(f"HTTP error {exc.code}: {exc.reason}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(f"API error: {exc}", file=sys.stderr)
        sys.exit(1)

    # If a second argument is "--json", output raw JSON
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        print(json.dumps(data, indent=2))
    else:
        print_sponsors(data)


if __name__ == "__main__":
    main()
