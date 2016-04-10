var casper = require("casper").create({
  //verbose: true,
  //logLevel: "debug",
});

var filename = casper.cli.raw.get('filename');
var url = casper.cli.raw.get('url');

casper.start();
casper.userAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.102 Safari/537.36');
casper.open(url);
casper.then(function () { this.wait(10000); });
casper.then(function () { this.thenClick('div[data-size="LARGE"]'); });
casper.then(function () { this.wait(10000); });
casper.then(function () { this.thenClick('div[data-color="BK0001"]'); });
casper.then(function () { this.wait(10000); });
casper.then(function () { this.captureSelector(filename, 'div[class=price-wrapper]'); });

casper.run();
