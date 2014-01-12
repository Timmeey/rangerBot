rangerBot
=========

The _ranger Bot for goxtool forked from pira/_ranger.py

I wanted to have a trading bot for my mtgox account. But as the Value of BTC increased i did not have enough FIAT/BTC to use the balancer bot anymore. SO i searched for alternatives and found this _ranger bot by "pira". Since it uses the same strategy as the balancer, but had the ability to set a trade corridor it worked for me, even with the small amount of FIAT/BTC.

So this repository is about an improved verison of piras rangerBot. Because pira just provided the bot as a gist, which made it impossible to make pull requests and so on, i took it and made it into a real repo.


How it works:
You set a trading range e.g. 500 to 1200 and a step width of 5 %. Now the bot devides the range into 5% steps(levels), at each level the bot will sell/buy steadily btc so that when we hit the upper limit all btc will be sold, and hitting the lower limit all FIAT would be spend for BTC.

At the start it will set 6 orders (every step_width(5%)) around the current price.

My changes so far are:

1. Order fillment status check. If a order is filled besides 0.00000001BTC, the bot will take it as fully filled. This helps against a weird habbit of mtGox to sometimes leave 0.00000001 BTC of an order. So the bot will not wait until these micro orders are filled.

2. Added the ability to set cold BTC/FIAT storage wich will not be touched by the bot. So if you set BTC_COLD to 0.5, the bot will allways leave 0.5 BTC in your account. Same goes for FIAT_COLD. So you can let the bot run without you full protfolio value.
