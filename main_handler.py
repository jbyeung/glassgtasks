# Copyright (C) 2013 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Request Handler for /main endpoint."""

__author__ = 'jbyeung@gmail.com (Jeff Yeung)'


import io
import jinja2
import logging
import json
import os
import webapp2
import time, threading

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import db

from google.appengine.ext import deferred

import custom_item_fields
import httplib2
from apiclient import errors
from apiclient.http import MediaIoBaseUpload
from apiclient.http import BatchHttpRequest
from oauth2client.appengine import StorageByKeyName

from apiclient.discovery import build
from oauth2client.appengine import OAuth2Decorator


from model import Credentials
from model import TasklistStore
import util

from tasks import auto_refresh, get_html_from_tasks, TIMELINE_ITEM_TEMPLATE_URL


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

TIMELINE_ITEM_TEMPLATE_URL = '/templates/card.html'


class _BatchCallback(object):
  """Class used to track batch request responses."""

  def __init__(self):
    """Initialize a new _BatchCallbaclk object."""
    self.success = 0
    self.failure = 0

  def callback(self, request_id, response, exception):
    """Method called on each HTTP Response from a batch request.

    For more information, see
      https://developers.google.com/api-client-library/python/guide/batch
    """
    if exception is None:
      self.success += 1
    else:
      self.failure += 1
      logging.error(
          'Failed to insert item for user %s: %s', request_id, exception)


class MainHandler(webapp2.RequestHandler):
  """Request Handler for the main endpoint."""

  def _render_template(self, message=None):
    """Render the main page template."""

    userid, creds = util.load_session_credentials(self)
    tasks_service = util.create_service('tasks', 'v1', creds)

    template_values = {'userId': self.userid}

    if message:
      template_values['message'] = message
    
    # self.mirror_service is initialized in util.auth_required
    subscriptions = self.mirror_service.subscriptions().list().execute()
    for subscription in subscriptions.get('items', []):
      collection = subscription.get('collection')
      if collection == 'timeline':
        template_values['timelineSubscriptionExists'] = True
    
    # pull from tasks api, list of tasklists
    tasklists = tasks_service.tasklists().list().execute()
    template_values['tasklists'] = tasklists['items']

    #load the tasklist names and ids from db if exists
    #q = db.GqlQuery("SELECT * FROM TasklistStore " + 
    #                "WHERE owner = " + userid)
    q = TasklistStore.all()
    q.filter("owner = ",self.userid)
    TASKLIST_NAMES = []
    for p in q.run():
      TASKLIST_NAMES.append(p.my_name)
    if TASKLIST_NAMES == []:
      TASKLIST_NAMES.append("None")

    template_values['synced'] = TASKLIST_NAMES

    template = jinja_environment.get_template('templates/index.html')
    self.response.out.write(template.render(template_values))

  @util.auth_required
  def get(self):
    """Render the main page."""
    # Get the flash message and delete it.
    message = memcache.get(key=self.userid)
    memcache.delete(key=self.userid)
    self._render_template(message)

  @util.auth_required
  def post(self):
    """Execute the request and render the template."""
    operation = self.request.get('operation')
    # Dict of operations to easily map keys to methods.
    operations = {
        # 'refresh': self._refresh_list,
        'new_tasklist': self._new_tasklist,
        'select_tasklist': self._select_tasklist
    }
    if operation in operations:
      message = operations[operation]()
    else:
      message = "I don't know how to " + operation
    # Store the flash message for 5 seconds.
    memcache.set(key=self.userid, value=message, time=5)
    self.redirect('/')

  def _select_tasklist(self):
    # selects tasklist, assigns to TASKLIST_NAME
    userid, creds = util.load_session_credentials(self)
    tasks_service = util.create_service('tasks', 'v1', creds)

    tasklist_id = self.request.get('select')
    logging.info("select")
    logging.info(self.request.get('select'))

    if tasklist_id == '':
      return "Please select a tasklist before trying to add it."
    else:
      #set name/id to db
      my_tasklist = TasklistStore(owner=self.userid)
      my_tasklist.my_id = tasklist_id
      #TASKLIST_NAMES.append(tasklist_title)

      tasklists = tasks_service.tasklists().list().execute()
      for tasklist in tasklists['items']:
        if tasklist_id == tasklist['id']:
          my_tasklist.my_name = tasklist['title']
            #TASKLIST_IDS[tasklist_title] = tasklist['id']

      my_tasklist.put()

      return my_tasklist.my_name + " selected successfully"

  def _new_tasklist(self):
    userid, creds = util.load_session_credentials(self)
    tasks_service = util.create_service('tasks', 'v1', creds)
    mirror_service = util.create_service('mirror', 'v1', creds)

    logging.info('Inserting timeline items')
    # Note that icons will not show up when making counters on a
    # locally hosted web interface.
    #mirror_service = util.create_service('mirror', 'v1', creds)
    #tasks_service = util.create_service('tasks', 'v1', creds)


    ############################  TASKS API STUFF #######
    # create empty task list @glass if none selected or none exist
    #q = db.GqlQuery("SELECT * FROM TasklistStore " + 
    #                "WHERE owner = " + userid)
    q = TasklistStore.all()
    q.filter("owner = ",self.userid)
    q.run()
    #if no tasklists, insert a default one
    if q:
        logging.info('not inserting')
    else:
        logging.info('no tasklist selected, inserting @glass ')
        tasklist = {
          'title': '@glass'
        }
        result = tasks_service.tasklists().insert(body=tasklist).execute()
        my_tasklist = TasklistStore(owner = userid, my_name = tasklist_title,
                                    my_id = result['id'])
        my_tasklist.put()
        
    ## now for each selected tasklist, post tasks to timeline
    for p in q:
      tasklist_id = p.my_id
      tasklist_name = p.my_name

      # insert seed tasks
      task = {
        'title': 'Glass interface synced to this list!',
        'notes': 'Try adding a new task with the voice command!'
      }
      result = tasks_service.tasks().insert(tasklist=tasklist_id, body=task).execute()
      
      # grab all the tasks in tasklist to display
      result = tasks_service.tasks().list(tasklist=tasklist_id).execute()

      #filter out completed tasks
      tasks = []
      for i, task in enumerate(result['items']):
        if task['status'] != 'completed':
          tasks.append(task)

      #grabbing all tasks now instead of just 5
      #indx = 5 if len(tasks) > 4 else len(tasks)
      #tasks = tasks[0:indx]

      if len(tasks) == 0:
        tasks.append({'title': 'No tasks!'})
 
      #render html
      # new_fields = {
      #     'list_title': tasklist_name,
      #     'tasks': tasks
      # }
      body = {
          'notification': {'level': 'DEFAULT'},
          'title': tasklist_id,     #secret way of stashing the tasklist id in the timeline item
          'html': get_html_from_tasks(tasks_service, tasklist_id, tasklist_name),
          'menuItems': [
              {
                  'action': 'REPLY',
                  'id': 'create_task',
                  'values': [{
                      'displayName': 'New Task',
                      'iconUrl': util.get_full_url(self, '/static/images/new_task.png')}]
              },
              {
                  'action': 'CUSTOM',
                  'id': 'refresh',
                  'values': [{
                      'displayName': 'Refresh',
                      'iconUrl': util.get_full_url(self, '/static/images/refresh2.png')}]
              },
              {'action': 'TOGGLE_PINNED'},
              {'action': 'DELETE'}
          ]
      }
      # custom_item_fields.set_multiple(body, new_fields, TIMELINE_ITEM_TEMPLATE_URL)


      # self.mirror_service is initialized in util.auth_required.
      # add card to timeline
      try:
        result = self.mirror_service.timeline().insert(body=body).execute()
        if result:
          item_id = result['id']
          # logging.info('mainhandler about to defer')
          # deferred.defer(auto_refresh, creds, mirror_service, tasks_service, item_id, tasklist_name, tasklist_id, True)
          # logging.info('mainhandler deferred')

      except errors.HttpError, error:
        logging.info ('an error has occured %s ', error)


    return 'New tasklists have been inserted to the timeline.'  


MAIN_ROUTES = [
    ('/', MainHandler)
]
