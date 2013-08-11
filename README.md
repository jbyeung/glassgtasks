Project to test out Mirror API and get a Google Tasks interface working for Google Glass

setup: change the tasklists in tasklists.json to your liking, these are all the ones that will be added/synced

can do:
- retrieve tasklists as cards, showing top 5 incomplete tasks
- can refresh to update the card, which can be pinned
- voice-command to create new task in this list

Google App engine url: glassgtasks.appspot.com


Auto-refresh currently doesn't work, so is disabled at the moment.



to do:
debug auto-refresh, queues fail to execute

features to add later:
- change to bundle, with first card as main actions and 5 item list (or expandable), others for descriptions of specific tasks and completion option
- website configuration tools