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
# WITHOUT WARRANTIES OR CsecreONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Request Handler for /notify endpoint."""

# need to configure the methods to handle menu actions from oauth for tasks
# leave at marking complete only, no uncompleting
# also voice command to make new task


__author__ = 'jbyeung@gmail.com (Jeff Yeung)'


import io
import json
import logging
import webapp2
import custom_item_fields

from apiclient.http import MediaIoBaseUpload
from apiclient import errors
from oauth2client.appengine import StorageByKeyName
from main_handler import TIMELINE_ITEM_TEMPLATE_URL

from model import Credentials
from model import TasklistStore
import util


class NotifyHandler(webapp2.RequestHandler):
  """Request Handler for notification pings."""

  def post(self):
    """Handles notification pings."""
    logging.info('Got a notification with payload %s', self.request.body)
    data = json.loads(self.request.body)
    userid = data['userToken']
    # TODO: Check that the userToken is a valid userToken.
    self.mirror_service = util.create_service(
        'mirror', 'v1',
        StorageByKeyName(Credentials, userid, 'credentials').get())
    self.tasks_service = util.create_service(
        'tasks', 'v1', 
        StorageByKeyName(Credentials, userid, 'credentials').get())
    if data.get('collection') == 'timeline':
      self._handle_timeline_notification(data)


  def _handle_timeline_notification(self, data):
    """Handle timeline notification."""
    #userid, creds = util.load_session_credentials(self)
    item_id = data.get('itemId')
    userid = data.get('userToken')

    #process actions
    logging.info(userid)
    #for user_action in data.get('userActions', []):
    user_action = data.get('userActions', [])[0]
    logging.info(user_action)
    payload = user_action.get('payload')

    if user_action.get('type') == 'REPLY':
        # handle adding a new task via voice input
        # create local vars for selected tasklist
        
        transcription_item = self.mirror_service.timeline().get(id=item_id).execute()
        transcription = transcription_item.get('text')

        timeline_item_id = transcription_item.get('inReplyTo')
        item = self.mirror_service.timeline().get(id=timeline_item_id).execute()
        tasklist_id = item.get('title')     #this is actually the tasklist id stashed in _new_tasklist from main_handler
        logging.info(tasklist_id)
        logging.info("tasklist id above")
        
        q = TasklistStore.all()
        q.filter("owner = ",userid)
        q.filter("my_id = ",tasklist_id)
        q.run()
        for p in q:
            tasklist_name = p.my_name
        

        if transcription:   #don't do anything if its empty
            task = {
                'title':transcription
            }
            logging.info('transcribed this text: ')
            logging.info(transcription)
            
            try:
                self.mirror_service.timeline().delete(id=item_id).execute()
                logging.info('deleted the voice item')
            except errors.HttpError, e:
                logging.info('An error occurred: %s' % error)

            try:
                result = self.tasks_service.tasks().insert(tasklist=tasklist_id, body=task).execute()
                logging.info('new task is inserted now')
            except errors.HttpError, error:
                logging.info('An error occured: %s' % error)

        item_id = timeline_item_id
    ############# CODE FOR REFRESH
    # refresh the card on the timeline on refresh command or after any custom action

    if user_action.get('type') == 'REPLY' or (user_action.get('type') == 'CUSTOM' and payload == 'refresh'):
        # create local vars for selected tasklist
        item = self.mirror_service.timeline().get(id=item_id).execute()
        tasklist_id = item.get('title')     #this is actually the tasklist id stashed in _new_tasklist from main_handler
        is_pinned = item.get('isPinned')
        logging.info(tasklist_id)
        logging.info("tasklist_id above")
        
        q = TasklistStore.all()
        q.filter("owner = ",userid)
        q.filter("my_id = ",tasklist_id)
        q.run()
        for p in q:
            tasklist_name = p.my_name
        
        # pull new text from tasks api - currently refresh on every action
        logging.info('refreshing')
        result = self.tasks_service.tasks().list(tasklist=tasklist_id).execute()

        tasks = []
        for task in result['items']:
            if task['status'] != 'completed':
                tasks.append(task)

        indx = 5 if len(tasks) > 4 else len(tasks)
        tasks = tasks[0:indx]

        if len(tasks) == 0:
            tasks.append({'title': 'No tasks!'})        

        #render html
        new_fields = {
            'list_title': tasklist_name,
            'tasks': tasks    
        }
        
        body = {
            'notification': {'level': 'DEFAULT'},
            'title': tasklist_id,
            'isPinned': is_pinned,
            # 'html': timeline_html,
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
                {'action': 'SHARE'},
                {'action': 'TOGGLE_PINNED'},
                {'action': 'DELETE'}
            ]
        }

        custom_item_fields.set_multiple(body, new_fields, TIMELINE_ITEM_TEMPLATE_URL)

        try:
            # First retrieve the timeline item from the API.
            # Update the timeline item's metadata.
            #patched_timeline_item = {'text': newtext }
            result = self.mirror_service.timeline().update(id=item_id, body=body).execute()
            #result = self.mirror_service.timeline().update(id=item_id, body=timeline_item).execute()
            logging.info('inserted updated tasklist to timeline')
        except errors.HttpError, error:
            logging.info('An error occured: %s ', error)

NOTIFY_ROUTES = [
    ('/notify', NotifyHandler)
]

