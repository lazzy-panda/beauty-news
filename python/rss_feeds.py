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
    {"url": "https://i-d.co/feed/", "hashtags": "#fashion #культура #тренды"},
    {"url": "https://fashionmagazine.com/feed/", "hashtags": "#fashion #глянец #стиль"},
    {"url": "https://www.fashiondive.com/feeds/news/", "hashtags": "#fashion #индустрия #retail"},
    {"url": "https://www.licenseglobal.com/rss.xml", "hashtags": "#fashion #brands #licensing"},
    {"url": "https://www.luxurydaily.com/feed/", "hashtags": "#luxury #маркетинг #бренды"},

    # --- Beauty (мир) ---
    {"url": "https://www.allure.com/feed/rss", "hashtags": "#beauty #макияж #уход"},
    {"url": "https://www.refinery29.com/en-us/rss.xml", "hashtags": "#beauty #fashion #тренды"},
    {"url": "https://www.beautyindependent.com/feed/", "hashtags": "#beauty #бренды #инди"},
    {"url": "https://beautyinc.com/feed/", "hashtags": "#beauty #индустрия #бизнес"},
    {"url": "https://www.popsugar.com/beauty/feed", "hashtags": "#beauty #макияж #тренды"},
    {"url": "https://stylecaster.com/feed/", "hashtags": "#beauty #fashion #стиль"},
    {"url": "https://www.premiumbeautynews.com/spip.php?page=backend", "hashtags": "#beauty #индустрия #упаковка"},

    # --- Глянец (мир) ---
    {"url": "https://www.elle.com/rss/all.xml/", "hashtags": "#fashion #beauty #глянец"},
    {"url": "https://www.harpersbazaar.com/rss/all.xml/", "hashtags": "#fashion #beauty #глянец"},
    {"url": "https://www.vogue.com/feed/rss", "hashtags": "#vogue #fashion #beauty"},
    {"url": "https://www.cosmopolitan.com/rss/all.xml/", "hashtags": "#beauty #fashion #тренды"},
    {"url": "https://www.teenvogue.com/feed/rss", "hashtags": "#fashion #beauty #культура"},
    {"url": "https://www.nylon.com/rss", "hashtags": "#fashion #beauty #культура"},
    {"url": "https://www.vanityfair.com/feed/rss", "hashtags": "#fashion #культура #глянец"},
    {"url": "https://www.gq.com/feed/rss", "hashtags": "#fashion #мужскойстиль #грумминг"},
    {"url": "https://www.esquire.com/rss/all.xml/", "hashtags": "#fashion #мужскойстиль #культура"},

    # --- Маркетинг, PR, adtech ---
    {"url": "https://digiday.com/feed/", "hashtags": "#маркетинг #медиа #adtech"},
    {"url": "https://www.adweek.com/feed/", "hashtags": "#маркетинг #реклама #бренды"},
    {"url": "https://www.campaignlive.com/rss/news", "hashtags": "#маркетинг #реклама #PR"},
    {"url": "https://www.prdaily.com/feed/", "hashtags": "#PR #коммуникации"},
    {"url": "https://martech.org/feed/", "hashtags": "#martech #данные #аналитика"},
    {"url": "https://www.marketingdive.com/feeds/news/", "hashtags": "#маркетинг #бренды #тренды"},
    {"url": "https://www.marketingbrew.com/feed.xml", "hashtags": "#маркетинг #бренды #тренды"},
    {"url": "https://www.marketingweek.com/feed/", "hashtags": "#маркетинг #бренды #стратегия"},
    {"url": "https://www.brandingmag.com/feed/", "hashtags": "#branding #маркетинг #стратегия"},
    {"url": "https://www.adexchanger.com/feed/", "hashtags": "#adtech #данные #реклама"},
    {"url": "https://www.chiefmarketer.com/feed/", "hashtags": "#маркетинг #CMO #стратегия"},
    {"url": "https://www.fastcompany.com/rss", "hashtags": "#бизнес #инновации #бренды"},

    # --- Influencer marketing / SMM ---
    {"url": "https://influencermarketinghub.com/feed/", "hashtags": "#инфлюенсеры #маркетинг #кейсы"},
    {"url": "https://blog.hootsuite.com/feed/", "hashtags": "#SMM #контент #стратегия"},
    {"url": "https://sproutsocial.com/insights/feed/", "hashtags": "#SMM #бренды #данные"},
    {"url": "https://www.socialmediatoday.com/feeds/news/", "hashtags": "#SMM #соцсети #тренды"},
    {"url": "https://grin.co/blog/feed/", "hashtags": "#инфлюенсеры #маркетинг #DTC"},
    {"url": "https://trendhero.io/blog/feed/", "hashtags": "#инфлюенсеры #Instagram #данные"},
    {"url": "https://buffer.com/resources/rss/", "hashtags": "#SMM #контент #соцсети"},
    {"url": "https://www.convinceandconvert.com/feed/", "hashtags": "#маркетинг #контент #SMM"},
    {"url": "https://sparktoro.com/blog/feed/", "hashtags": "#маркетинг #аудитория #SMM"},

    # --- Креаторы и creator economy ---
    {"url": "https://www.passionfru.it/feed", "hashtags": "#креаторы #creatoreconomy"},
    {"url": "https://www.thetilt.com/feed", "hashtags": "#креаторы #контент #бизнес"},
    {"url": "https://creatoreconomy.so/feed", "hashtags": "#креаторы #creatoreconomy"},
    {"url": "https://www.tubefilter.com/feed/", "hashtags": "#креаторы #YouTube #видео"},
    {"url": "https://www.workweek.com/feed", "hashtags": "#креаторы #медиа #бизнес"},
    {"url": "https://2pml.com/feed/", "hashtags": "#DTC #маркетинг #бренды"},

    # --- Retail / e-commerce beauty & fashion ---
    {"url": "https://www.retaildive.com/feeds/news/", "hashtags": "#retail #ecommerce #бренды"},
    {"url": "https://www.modernretail.co/feed/", "hashtags": "#retail #ecommerce #DTC"},
    {"url": "https://www.retailtouchpoints.com/feed", "hashtags": "#retail #ecommerce #технологии"},
]
