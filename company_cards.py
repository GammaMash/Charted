# Company cards for the answer queue. Five fields per ticker:
#   where — casual rung 3: store | home | hidden (see WHERE_CLUE in template.html)
#   emoji — 3-emoji visual clue
#   what  — reveal card: plain-English "what they actually do" (no numbers, no jargon)
#   hint  — casual rung 5 "you might know them from" (spoiler-free: never names the company)
#   fact  — degen rung 2 / casual rung 4. RULE: it must CONSTRAIN, not identify. "Founded in a
#           Denny's" is a bad clue — you either know it and it's the answer, or you don't and it's
#           nothing. Write properties a knowledgeable player can filter on. Optional; falls back.
CO = {
 "MU":    {"where":"hidden", "emoji":"💾🧠📱", "what":"Micron makes memory chips — the storage and RAM inside phones, laptops and the data centers that run AI.", "hint":"the memory chips inside your phone and AI data centers"},
 "GME":   {"where":"store", "emoji":"🎮🕹️🚀", "what":"GameStop is the mall video-game retailer that became the most famous meme stock on earth in 2021.", "hint":"the mall video-game store that broke Wall Street in 2021"},
 "CRCL":  {"where":"hidden", "emoji":"💵🔵🪙", "what":"Circle issues USDC — a 'digital dollar' stablecoin used to move money around the crypto world.", "hint":"the company behind the USDC digital dollar", "fact":"Almost all of its money comes from the interest it earns on other people's dollars."},
 "CAT":   {"where":"hidden", "emoji":"🚜🏗️🟡", "what":"Caterpillar builds the yellow bulldozers, excavators and mining trucks you see on every construction site.", "hint":"the yellow bulldozers on every construction site"},
 "MSTR":  {"where":"hidden", "emoji":"₿💻🏦", "what":"Strategy (born MicroStrategy) is a software company that turned itself into a giant leveraged Bitcoin vault.", "hint":"the software company that turned itself into a Bitcoin vault", "fact":"For twenty years it sold business software. Then it decided its real product was its balance sheet."},
 "AAPL":  {"where":"store", "emoji":"📱💻⌚", "what":"Apple makes the iPhone, Mac and Apple Watch — and takes a cut of everything in the App Store.", "hint":"the phone that's probably in your hand right now"},
 "SNDK":  {"where":"home", "emoji":"💾📷🔌", "what":"SanDisk makes flash memory — the storage in memory cards, USB drives and SSDs.", "hint":"the memory cards in your camera and the USB stick in your drawer", "fact":"A hard-drive maker bought it in 2016, then spun it back out on its own last year."},
 "NKE":   {"where":"store", "emoji":"👟✅🏅", "what":"Nike is the world's biggest sneaker and sportswear brand — the swoosh, Air Jordans, 'Just Do It.'", "hint":"the swoosh on half the sneakers you own"},
 "PLTR":  {"where":"hidden", "emoji":"🕵️📊🔮", "what":"Palantir sells secretive data-analysis software used by governments, militaries and big companies.", "hint":"the secretive data software used by governments and militaries", "fact":"It's named after a magic seeing-stone from a fantasy novel."},
 "INTC":  {"where":"hidden", "emoji":"💻🔵⚙️", "what":"Intel is the classic PC chip maker — the processor 'inside' decades of computers, now fighting its way back.", "hint":"the classic 'inside your PC' chip maker"},
 "DIS":   {"where":"store", "emoji":"🏰🐭🎬", "what":"Disney owns Mickey Mouse, Marvel, Star Wars, Pixar, ESPN and the theme parks.", "hint":"Mickey Mouse, Marvel and the theme parks"},
 "COIN":  {"where":"home", "emoji":"🪙📱₿", "what":"Coinbase is the biggest US crypto exchange — the app most Americans use to buy Bitcoin.", "hint":"the app most Americans use to buy Bitcoin"},
 "MSFT":  {"where":"home", "emoji":"🪟📊🎮", "what":"Microsoft makes Windows, Office, Xbox and the Azure cloud — and is a major backer of OpenAI.", "hint":"Windows, Office and Xbox"},
 "AMD":   {"where":"hidden", "emoji":"🎮🖥️🔴", "what":"AMD designs the chips inside gaming PCs, consoles and servers — Nvidia's arch-rival in AI chips.", "hint":"gaming PC chips — the arch-rival of the AI chip king"},
 "NFLX":  {"where":"home", "emoji":"🍿📺🔴", "what":"Netflix is the world's biggest streaming service — the one that invented binge-watching.", "hint":"the streaming app you fall asleep to"},
 "HOOD":  {"where":"home", "emoji":"🪶📈📱", "what":"Robinhood is the commission-free trading app that brought a generation of first-timers into the stock market.", "hint":"the free stock-trading app with the feather logo"},
 "LULU":  {"where":"store", "emoji":"🧘👖🛍️", "what":"Lululemon sells premium yoga pants and athleisure — the brand that made leggings a status symbol.", "hint":"the yoga pants"},
 "DELL":  {"where":"home", "emoji":"💻🖥️⌨️", "what":"Dell builds PCs, laptops and the servers that data centers — including AI ones — run on.", "hint":"the computer brand from the old 'Dude, you're getting a…' ads"},
 "BA":    {"where":"hidden", "emoji":"✈️🛫🔧", "what":"Boeing builds the 737 and 787 — half the planes you've ever flown on.", "hint":"maker of half the planes you've flown on"},
 "TSLA":  {"where":"store", "emoji":"🚗⚡🔋", "what":"Tesla makes electric cars, the Cybertruck, home batteries — and bets big on robots and self-driving.", "hint":"the electric car with the most famous CEO on earth"},
 "GEMI":  {"where":"home", "emoji":"♊🪙👯", "what":"Gemini is the crypto exchange founded by the Winklevoss twins of Facebook-lawsuit fame.", "hint":"the Winklevoss twins' crypto exchange", "fact":"The stock exchange it trades on invested in it just before the listing."},
 "SBUX":  {"where":"store", "emoji":"☕🟢🧜‍♀️", "what":"Starbucks is the world's biggest coffee chain — the green mermaid on every corner.", "hint":"the green mermaid on your coffee cup"},
 "MRVL":  {"where":"hidden", "emoji":"📡🔌💾", "what":"Marvell designs the networking chips that move data around clouds and AI data centers.", "hint":"chips that shuttle data around AI data centers"},
 "IBM":   {"where":"hidden", "emoji":"🖥️🔵💼", "what":"IBM — 'Big Blue' — is the original computer giant, now selling cloud, consulting and mainframes.", "hint":"'Big Blue' — the original computer giant"},
 "RIVN":  {"where":"store", "emoji":"🛻⚡📦", "what":"Rivian makes electric pickups and SUVs — and the vans that deliver your Amazon packages.", "hint":"the electric vans that deliver your Amazon packages"},
 "KO":    {"where":"home", "emoji":"🥤🔴🐻", "what":"Coca-Cola sells the world's most famous drink — plus Sprite, Fanta, Smartwater and hundreds more.", "hint":"the red can"},
 "SMCI":  {"where":"hidden", "emoji":"🖥️🔩⚡", "what":"Super Micro builds the server racks that AI chips get bolted into — the pickaxe seller of the AI boom.", "hint":"the servers AI chips get bolted into", "fact":"Its founder is still the CEO, more than thirty years after starting it."},
 "AVGO":  {"where":"hidden", "emoji":"📶🔌📱", "what":"Broadcom's chips and software are in everything from iPhones to Wi-Fi routers to AI data centers.", "hint":"chips hiding in your phone, your Wi-Fi and the cloud", "fact":"The company that bought it liked the name so much it gave up its own."},
 "CVNA":  {"where":"store", "emoji":"🚗🪟🎰", "what":"Carvana sells used cars online — famous for its glass car vending-machine towers.", "hint":"the glass car vending machines", "fact":"It was spun out of its founder's father's used-car empire."},
 "NVDA":  {"where":"home", "emoji":"🎮🤖💚", "what":"Nvidia designs the AI chips every tech giant is fighting over — the most valuable company boom of the AI era.", "hint":"the AI chip everyone on earth is fighting over", "fact":"For its first twenty-five years, its customers were mostly video gamers."},
 "GOOGL": {"where":"home", "emoji":"🔍📱🎥", "what":"Alphabet is Google — search, YouTube, Android, Chrome and the Gemini AI models.", "hint":"the search bar you use a hundred times a day", "fact":"It renamed its parent company in 2015 and nobody has used the new name since."},
 "META":  {"where":"home", "emoji":"👍📘🕶️", "what":"Meta owns Facebook, Instagram, WhatsApp and the Quest headsets, and pours enormous sums into AI.", "hint":"the company behind Instagram and WhatsApp"},
 "ORCL":  {"where":"hidden", "emoji":"🗄️☁️🏢", "what":"Oracle sells the databases and cloud servers that big companies run their operations on.", "hint":"the database company that quietly runs corporate America"},
 "RBLX":  {"where":"home", "emoji":"🟥🎮🧱", "what":"Roblox is the online platform where millions of kids build and play each other’s games.", "hint":"the game platform every 10-year-old is on"},
 "HIMS":  {"where":"home", "emoji":"💊📦🪞", "what":"Hims & Hers sells prescription treatments online — hair, skin and weight — shipped to your door.", "hint":"the telehealth app advertising hair-loss pills"},
 "RIOT":  {"where":"hidden", "emoji":"⛏️🟠🔌", "what":"Riot Platforms runs warehouses full of computers that mine Bitcoin.", "hint":"the warehouse full of Bitcoin miners"},
 "QCOM":  {"where":"hidden", "emoji":"📡📱🔋", "what":"Qualcomm designs the chips and modems that connect nearly every Android phone to the network.", "hint":"the chip that keeps your phone on the network"},
 "LLY":   {"where":"home", "emoji":"💊🧬🏥", "what":"Eli Lilly makes the blockbuster weight-loss and diabetes drugs, plus cancer and Alzheimer’s treatments.", "hint":"the drugmaker behind the weight-loss shots"},
 "JPM":   {"where":"store", "emoji":"🏦💳🗽", "what":"JPMorgan Chase is the biggest bank in America — Chase branches, credit cards and Wall Street trading.", "hint":"the biggest bank in America"},
 "UBER":  {"where":"home", "emoji":"🚕📱🍔", "what":"Uber is the ride-hailing app — and Uber Eats, which delivers the food.", "hint":"the app you use when you don’t want to drive"},
}
