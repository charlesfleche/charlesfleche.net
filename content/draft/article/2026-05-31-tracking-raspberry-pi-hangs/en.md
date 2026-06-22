Title: Tracking Raspberry PI hangs
Description: How to avoid buying new hardware and optimize what I already have
Tags:

https://claude.ai/share/f2cb8063-0eba-4dd6-b4e4-509422926ac3


```bash
# /usr/local/bin/syslog_snapshot.sh
#!/bin/bash
LOG=/var/log/health_snapshot.log
echo "=== $(date) ===" >> $LOG
echo "-- uptime/load --" >> $LOG
uptime >> $LOG
echo "-- memory --" >> $LOG
free -h >> $LOG
echo "-- swap activity --" >> $LOG
vmstat 1 3 >> $LOG
echo "-- top processes by memory --" >> $LOG
ps aux --sort=-%mem | head -15 >> $LOG
echo "-- dmesg (last 20 lines) --" >> $LOG
dmesg | tail -20 >> $LOG
echo "" >> $LOG
```

```
chmod +x /usr/local/bin/syslog_snapshot.sh
# Add to crontab:
*/5 * * * * /usr/local/bin/syslog_snapshot.sh
```
