# functions for tasks

import os
import jinja2
import logging
import math
from apiclient import errors

import time, threading
from datetime import datetime, timedelta
from google.appengine.ext import deferred

import util


TIMELINE_ITEM_TEMPLATE_URL = '/templates/card.html'

#DEFAULT_REFRESH_TIME = 10.0
DEFAULT_REFRESH_TIME = 10800.0     #auto-refresh every three hrs

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))


def auto_refresh(creds, mirror_service, tasks_service, item_id, tasklist_title, tasklist_id, first_time=None):
	logging.info('auto refresh called')

	tasks_service = util.create_service('tasks', 'v1', creds)
	mirror_service = util.create_service('mirror', 'v1', creds)

	try:
	  timeline_item = mirror_service.timeline().get(id = item_id).execute()
	  tasklist_item = tasks_service.tasks().list(tasklist=tasklist_id).execute()
	  logging.info('autorefresh try done')
	  if timeline_item.get('isDeleted') or not tasklist_item:
	  	logging.info("stopped auto-refresh")
	  	return "auto-refresh halted, timeline item or calendar does not exist"

	except errors.HttpError, error:
	  logging.info("error in auto-refresh try")
	  return "auto-refresh error, breaking"

	logging.info('about to test refreshme if not first time')
	if not first_time:
		refresh_me(mirror_service, tasks_service, item_id, tasklist_title, tasklist_id)  

	logging.info('about to sleep')
	time.sleep(DEFAULT_REFRESH_TIME)
	logging.info('about to start new thread')
	deferred.defer(auto_refresh, creds, mirror_service, tasks_service, item_id, tasklist_title, tasklist_id)
	logging.info('new thread started')
	return "auto-refresh thread done"

def refresh_me(mirror_service, tasks_service, item_id, tasklist_title, tasklist_id):

	tasks_html = get_html_from_tasks(tasks_service, tasklist_id, tasklist_title)

	patched_timeline_item = {'html': tasks_html }

	logging.info('refreshme about to try')
	try:
		result = mirror_service.timeline().patch(id = item_id, body = patched_timeline_item).execute()
	except errors.HttpError, error:
		logging.info('an error has occured %s ', error)
	return "tasklist named \'" + tasklist_title + "\' has been updated."

def get_html_from_tasks(tasks_service, tasklist_id, tasklist_title):
	
    # pull new text from tasks api - currently refresh on every action
    logging.info('gethtml about to get')
    result = tasks_service.tasks().list(tasklist=tasklist_id).execute()

    tasks = []
    template_values = {}

    for task in result['items']:
        if task['status'] != 'completed':
            tasks.append(task)

    #indx = 5 if len(tasks) > 4 else len(tasks)
    #tasks = tasks[0:indx]

    if len(tasks) == 0:
        tasks.append({'title': 'No tasks!'})        

    #render html
    logging.info('gethtml about to set html')
    template = jinja_environment.get_template(TIMELINE_ITEM_TEMPLATE_URL)
    template_values['list_title'] = tasklist_title

    #paginate html for every 5 tasks
    tasks_html = ''
    number_pages = int(math.ceil(float(len(tasks)) // 5.0))
    counter = 0
    for i in range(number_pages):
    	indx = 5 if len(tasks[counter:]) > 4 else len(tasks[counter:])
    	tasks_subset = tasks[counter:counter+indx]
    	template_values['tasks'] = tasks_subset
    	tasks_html += template.render(template_values)
    	counter += indx
    
    logging.info('gethtml done')
    return tasks_html	    