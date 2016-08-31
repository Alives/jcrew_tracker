# jcrew_tracker
A python script that uses selenium and phamtomjs to alert on J.Crew product
changes.

I wrote this to be alerted on the changes of specific product offerings.
Changes being any product addtions, price changes, or product removals.

It requires that phantomjs and selenium are installed.  Pushbullet notifications
require the pushbullet.py pip module.

The script is intended to be run by cron.

##Sample Email
![alt text](http://i.imgur.com/xzQz06C.png?1 "Email HTML")

##How to run it
###Default mode (Large Polos):
```bash
python jcrew_tracker.py \
  -f jcrew_tracker@your_domain.com \
  -t your_email@your_domain.com
```
  
###For non-polo or non-jcrew products:
```bash
python jcrew_tracker.py \
  --logfile /tmp/madewell_tracker.log \
  --pushbullet_api_keyfile pushbullet.api_key \
  --size the_size_you_want \
  --state_file madewell.state \
  --url https://www.madewell.com/madewell_category/DENIMBAR/highriserskinny/PRDOVR~E0257/E0257.jsp \
  -f madewell_tracker@your_domain.com
  -s 'Madewell Jeans Changes'
  -t 'your_email@your_domain.com, another_email@another_domain.com'
```
