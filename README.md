## Description
Program pulls all scopes from the specified bug bounty program and outputs the urls.

## Configuration
Hackerone - https://docs.hackerone.com/en/articles/8410331-api-token
Bugcrowd - No API key needed
Integriti - https://www.youtube.com/watch?v=9uHOSU8W6vk&ab_channel=Intigriti
Yes We Hack - No API key needed
*Add the API keys to config.ini*

## Usage
```
python hackerone.py > h1.txt
python bugcrowd.py > bugcrowd.txt
python integriti.py > integriti.txt
python yeswehack.py > yeswehack.txt
```

## Usful Command
```bash
cat scopes/* | grep -E '^\*\.' | sed 's/\*\.//' | subfinder -o subs.txt
```

