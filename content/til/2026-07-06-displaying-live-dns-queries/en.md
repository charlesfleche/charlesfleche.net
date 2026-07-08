Title: Displaying live DNS queries
Description: Monitoring system wide name resolution queries
Tags: [linux, dns, systemd, resolved]

`resolved monitor` shows the live DNS queries. It needs to run as root.

```bash
$ resolvectl monitor

==== AUTHENTICATING FOR org.freedesktop.resolve1.subscribe-query-results ====
Authentication is required to subscribe query results.
Authenticating as: root
Password: 
==== AUTHENTICATION COMPLETE ====

→ Q: ssl.gstatic.com IN A
→ Q: ssl.gstatic.com IN AAAA
← S: success
← A: ssl.gstatic.com IN AAAA 2607:f8b0:4020:c07::5e
← A: ssl.gstatic.com IN A 142.250.69.67

→ Q: merino.services.mozilla.com IN A
→ Q: merino.services.mozilla.com IN AAAA
← S: success
← A: merino.services.mozilla.com IN CNAME mozilla.map.fastly.net
← A: mozilla.map.fastly.net IN AAAA 2a04:4e42:400::347
← A: mozilla.map.fastly.net IN AAAA 2a04:4e42::347
← A: mozilla.map.fastly.net IN AAAA 2a04:4e42:600::347
← A: mozilla.map.fastly.net IN AAAA 2a04:4e42:200::347
← A: mozilla.map.fastly.net IN A 151.101.1.91
← A: mozilla.map.fastly.net IN A 151.101.193.91
← A: mozilla.map.fastly.net IN A 151.101.65.91
← A: mozilla.map.fastly.net IN A 151.101.129.91

→ Q: incoming.telemetry.mozilla.org IN A
→ Q: incoming.telemetry.mozilla.org IN AAAA
← S: success
← A: incoming.telemetry.mozilla.org IN CNAME telemetry-incoming.r53-2.services.mozilla.com
← A: telemetry-incoming.r53-2.services.mozilla.com IN A 34.120.208.123
← A: r53-2.services.mozilla.com IN SOA ns-1507.awsdns-60.org awsdns-hostmaster.amazon.com 1 7200 900 1209600 86400

→ Q: telemetry-incoming.r53-2.services.mozilla.com IN A
→ Q: telemetry-incoming.r53-2.services.mozilla.com IN AAAA
→ C: incoming.telemetry.mozilla.org IN A
→ C: incoming.telemetry.mozilla.org IN AAAA
← S: success
← A: telemetry-incoming.r53-2.services.mozilla.com IN A 34.120.208.123
← A: r53-2.services.mozilla.com IN SOA ns-1507.awsdns-60.org awsdns-hostmaster.amazon.com 1 7200 900 1209600 86400

→ Q: 1.debian.pool.ntp.org IN AAAA
← S: success
← A: pool.ntp.org IN SOA d.ntpns.org hostmaster.pool.ntp.org 1783342806 5400 5400 1209600 3600

→ Q: 1.debian.pool.ntp.org IN A
← S: success
← A: 1.debian.pool.ntp.org IN A 162.159.200.1
← A: 1.debian.pool.ntp.org IN A 170.39.49.50
← A: 1.debian.pool.ntp.org IN A 216.232.132.95
← A: 1.debian.pool.ntp.org IN A 147.189.136.126

# ...
```

