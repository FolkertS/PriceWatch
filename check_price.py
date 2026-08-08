#!/bin/sh
# backmarket_premium_check.sh
#
# Fetches the Back Market "iPhone 15 Pro" page and logs the price of the
# "Premium" condition option. Designed to run with nothing but tools that
# already ship in DSM (curl, grep) -- no Docker, no Python, no packages
# to install. Built for a DS216j but will run on any Synology.
#
# SET THESE TWO PATHS before using:
LOGDIR="/volume1/homes/YOUR_USERNAME/backmarket"
LOGFILE="$LOGDIR/premium_price_log.csv"
COOKIEJAR="$LOGDIR/cookies.txt"

# Product page. Using the Dutch storefront: Back Market blocks/redirects
# the US site (/en-us/) for non-US IPs, which is why the US URL returned
# "Sorry, this page is not available." when run from a Dutch connection.
# Swap this if you want to track a different model/listing/country.
HOMEPAGE="https://www.backmarket.nl/nl-nl"
URL="https://www.backmarket.nl/nl-nl/p/iphone-15-pro"

# A normal browser User-Agent avoids basic bot-blocking. Update this
# occasionally to a current Chrome UA string if fetches start failing.
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

mkdir -p "$LOGDIR"

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Back Market sits behind Cloudflare, which hands out session/bot-check
# cookies (__cf_bm, _cfuvid, visitor_id, session_id) on first contact.
# A real browser picks these up on the homepage and carries them to the
# product page automatically; a single stateless request straight to the
# product page arrives with none of them and gets a generic
# "Sorry, this page is not available." response instead of real content.
# So: hit the homepage first to fill a cookie jar, then reuse it below.
curl -s -c "$COOKIEJAR" -A "$UA" --max-time 30 "$HOMEPAGE" -o /dev/null

# Flatten to one line: grep only matches within a single line, and the
# icon markup and price text could be separated by a newline in the
# source HTML, so a plain multi-line fetch could cause false misses.
HTML=$(curl -s -b "$COOKIEJAR" -L -A "$UA" \
    -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" \
    -H "Accept-Language: nl-NL,nl;q=0.9,en;q=0.8" \
    -H "Referer: $HOMEPAGE" \
    --max-time 30 "$URL" | tr '\n' ' ')

if [ -z "$HTML" ]; then
    echo "$TIMESTAMP,ERROR: empty response (network/block issue)" >> "$LOGFILE"
    exit 1
fi

# The "Premium" condition option is the only one marked with a small
# diamond icon (outline-diamond.gif) right before its price. Anchoring on
# that icon filename -- rather than just the word "Premium" -- avoids
# accidentally matching the "Premium" text that also appears elsewhere on
# the page (e.g. the customer-review condition filter).
#
# [^€]* matches everything up to (but not including) the first '€', so
# this can only ever land on the price immediately following that icon.
# Euro formatting here is "€ 629,00" -- symbol first, comma decimal.
PRICE=$(printf '%s' "$HTML" | grep -oE 'outline-diamond[^€]*€[^0-9]*[0-9][0-9.,]*' | grep -oE '€[^0-9]*[0-9][0-9.,]*' | head -1)

if [ -z "$PRICE" ]; then
    echo "$TIMESTAMP,ERROR: Premium price not found (page layout may have changed)" >> "$LOGFILE"
    exit 1
fi

echo "$TIMESTAMP,$PRICE" >> "$LOGFILE"

# --- Optional: pop a DSM desktop notification when the price changes ---
# Uncomment to enable. Replace YOUR_USERNAME with your DSM login.
#
# PREV=$(tail -n 2 "$LOGFILE" | head -n 1 | cut -d',' -f2)
# if [ -n "$PREV" ] && [ "$PREV" != "$PRICE" ]; then
#     /usr/syno/bin/synodsmnotify YOUR_USERNAME "Back Market Premium price changed" \
#         "iPhone 15 Pro Premium: $PREV -> $PRICE"
# fi

exit 0
