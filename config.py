# update intervals
from datetime import timedelta
d_send_reminders = timedelta(seconds=15)
d_update_events = timedelta(hours=6)
event_cache_size = 256
event_ttl = round(timedelta(hours=1).total_seconds())