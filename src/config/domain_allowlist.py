DOMAIN_PRIORITY: dict[str, int] = {
    "ncert.nic.in": 5,
    "cbse.gov.in": 5,
    "diksha.gov.in": 4,
    "ncertbooks.prashanthellina.com": 4,
    "epathshala.nic.in": 4,
    "learncbse.in": 3,
    "byjus.com": 2,
    "vedantu.com": 2,
    "tiwariacademy.com": 2,
    "extramarks.com": 1,
    "teachoo.com": 1,
    "jagranjosh.com": 1,
}

DEFAULT_PRIORITY = 0
MIN_PRIORITY_THRESHOLD = 1


def get_domain_priority(url: str) -> int:
    from urllib.parse import urlparse

    hostname = urlparse(url).hostname or ""
    for domain, priority in DOMAIN_PRIORITY.items():
        if domain in hostname:
            return priority
    return DEFAULT_PRIORITY


def is_domain_allowed(url: str) -> bool:
    return get_domain_priority(url) >= MIN_PRIORITY_THRESHOLD
