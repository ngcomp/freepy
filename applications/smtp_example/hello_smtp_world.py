# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# Thomas Quintana <quintana.thomas@gmail.com>
#
# Lyle Pratt <lylepratt@gmail.com>

from freepy.lib.application import Actor
from freepy.services.smtp import SmtpReceiveEvent

import logging
import time

class HelloSmtpWorld(Actor):
  def __init__(self, *args, **kwargs):
    super(HelloSmtpWorld, self).__init__(*args, **kwargs)
    self.__logger__ = logging.getLogger('services.smtp.SmtpDispatcher')

  def receive(self, message):
    if isinstance(message, SmtpReceiveEvent):
      self.__logger__.debug(message.received())
      self.__logger__.debug(message.headers())
      self.__logger__.debug(message.body())
