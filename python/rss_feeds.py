"""
RSS feed definitions by category.
Each entry: url + hashtags for Telegram post.
Тематика: beauty & fashion индустрия, маркетинг, PR, influencer marketing, креаторы, стратегия.
Только англоязычные источники, прошедшие liveness-проверку feedparser.
"""

RSS_FEEDS = [
    # --- Beauty & Fashion индустрия (мир) ---
    {"url": "https://www.businessoffashion.com/feed/", "hashtags": "#fashion #индустрия #бизнес"},
    {"url": "https://wwd.com/feed/", "hashtags": "#fashion #beauty #индустрия"},
    {"url": "https://www.glossy.co/feed/", "hashtags": "#beauty #fashion #retail"},
    {"url": "https://www.dazeddigital.com/rss", "hashtags": "#fashion #beauty #тренды"},
    {"url": "https://hypebeast.com/feed", "hashtags": "#fashion #streetwear #коллаборации"},
    {"url": "https://www.highsnobiety.com/feed/", "hashtags": "#fashion #streetwear #бренды"},

    # --- Beauty (мир) ---
    {"url": "https://www.allure.com/feed/rss", "hashtags": "#beauty #макияж #уход"},
    {"url": "https://www.refinery29.com/en-us/rss.xml", "hashtags": "#beauty #fashion #тренды"},
    {"url": "https://www.beautyindependent.com/feed/", "hashtags": "#beauty #бренды #инди"},

    # --- Глянец (мир) ---
    {"url": "https://www.elle.com/rss/all.xml/", "hashtags": "#fashion #beauty #глянец"},
    {"url": "https://www.harpersbazaar.com/rss/all.xml/", "hashtags": "#fashion #beauty #глянец"},
    {"url": "https://www.vogue.com/feed/rss", "hashtags": "#vogue #fashion #beauty"},
    {"url": "https://www.cosmopolitan.com/rss/all.xml/", "hashtags": "#beauty #fashion #тренды"},

    # --- Маркетинг, PR, adtech ---
    {"url": "https://digiday.com/feed/", "hashtags": "#маркетинг #медиа #adtech"},
    {"url": "https://www.adweek.com/feed/", "hashtags": "#маркетинг #реклама #бренды"},
    {"url": "https://www.campaignlive.com/rss/news", "hashtags": "#маркетинг #реклама #PR"},
    {"url": "https://www.prdaily.com/feed/", "hashtags": "#PR #коммуникации"},
    {"url": "https://martech.org/feed/", "hashtags": "#martech #данные #аналитика"},
    {"url": "https://www.marketingdive.com/feeds/news/", "hashtags": "#маркетинг #бренды #тренды"},

    # --- Influencer marketing / SMM ---
    {"url": "https://influencermarketinghub.com/feed/", "hashtags": "#инфлюенсеры #маркетинг #кейсы"},
    {"url": "https://blog.hootsuite.com/feed/", "hashtags": "#SMM #контент #стратегия"},
    {"url": "https://sproutsocial.com/insights/feed/", "hashtags": "#SMM #бренды #данные"},
    {"url": "https://www.socialmediatoday.com/feeds/news/", "hashtags": "#SMM #соцсети #тренды"},

    # --- Креаторы и creator economy ---
    {"url": "https://www.passionfru.it/feed", "hashtags": "#креаторы #creatoreconomy"},
    {"url": "https://www.thetilt.com/feed", "hashtags": "#креаторы #контент #бизнес"},
    {"url": "https://creatoreconomy.so/feed", "hashtags": "#креаторы #creatoreconomy"},

    # --- Retail / e-commerce beauty & fashion ---
    {"url": "https://www.retaildive.com/feeds/news/", "hashtags": "#retail #ecommerce #бренды"},
    {"url": "https://www.modernretail.co/feed/", "hashtags": "#retail #ecommerce #DTC"},
]
