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
```python jcrew_tracker.py -t your_email@your_domain.com -f jcrew_tracker@your_domain.com```
  
###For non-polo or non-jcrew products:
```python jcrew_tracker.py --size the_size_you_want --state_file madewell.state --url https://www.madewell.com/madewell_category/DENIMBAR/highriserskinny/PRDOVR~E0257/E0257.jsp --pushbullet_api_keyfile pushbullet.api_key -t 'your_email@your_domain.com, another_email@another_domain.com' -f madewell_tracker@your_domain.com   --logfile /tmp/madewell_tracker.log -s 'Madewell Jeans Changes'```
