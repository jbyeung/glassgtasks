Project to test out Mirror API and get a Google Tasks interface working for Google Glass

setup: change the tasklists in tasklists.json to your liking, these are all the ones that will be added/synced

can do:
- retrieve tasklists as cards, showing top 5 incomplete tasks
- can refresh to update the card, which can be pinned
- voice-command to create new task in this list

Google App engine url: glassgtasks.appspot.com




debug:
clean up code - refresh/adding tasklist should be compacted

features to add:

adding db - prevent adding duplicate
set up auto refresh - http://stackoverflow.com/questions/8600161/executing-periodic-actions-in-python


In regard to the UI for marking tasks as complete: What about bundles? If you presented a task list as a "bundle" where the first card was the 5-entry list, and then the remaining cards were each individual task (including beyond those five) the first card (showing the 5 tasks) could present the existing options of adding a task and refreshing, while the remaining cards could allow one to mark off, remove, or edit tasks. While this would increase the number of taps by one for adding a task (since entering the bundle would take that one extra tap) beyond that it shouldn't impact the existing use cases with the app as it stands now, but would allow the functionality to be expanded pretty significantly in what would be a fairly user-logical way, I think. This would also keep it within the sort-of minimalist "what you need now" perspective of Google's ideal for Glassware in terms of the presentation on the timeline, while still allowing the exposure of more in-depth Task features (including the key ability of mostly/fully managing your tasks within a specific list, without having to fiddle about on your phone).



Thanks for the input, I hadn't thought about adding the main actions into the top bundle-child card.. that might work.  Completing and removing tasks I can see.  Editing - voice input would have to replace the text, basically delete+add (and a sort-by-edit-date to move it to top).  The only other thing I could see is adding a note to the task maybe?  I'll probably add these changes after I figure out an easy way to do auto-refresh, then do it all at once.


I think checkboxes on the website to configure things would be a good idea. Configuration is something that shouldn't really be necessary on Glass itself, and wouldn't fit well with Google's idea of keeping the presentation on Glass relatively simple. But there's no question people are going to have different expectations and wants and this would expose it to them well. Since most configuration options should basically be "set once, then leave alone" it's a good way to handle it.